const rules = [
  { type: "input", field: "apiUrl", title: "API 地址", value: "https://ark.cn-beijing.volces.com/api/v3" },
  { type: "input", field: "apiKey", title: "API Key", value: "", props: { type: "password", showPassword: true, autocomplete: "off" } },
] as const;

type Context = ProviderContext<ProviderConfig<typeof rules>>;

function baseUrl(context: Context) {
  const url = new URL(context.config.apiUrl.trim());
  if (!/^https?:$/.test(url.protocol) || url.username || url.password || url.search || url.hash) throw new Error("API 地址须为不含凭据或查询参数的 HTTP(S) 地址");
  if (!context.config.apiKey.trim()) throw new Error("请先保存火山方舟 API Key");
  return url.href.replace(/\/$/, "");
}

async function requestJson(context: Context, path: string, body?: unknown) {
  const response = await context.tool.fetch(`${baseUrl(context)}${path}`, {
    method: body === undefined ? "GET" : "POST", redirect: "error",
    headers: { Authorization: `Bearer ${context.config.apiKey.trim()}`, "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
    signal: AbortSignal.timeout(body === undefined ? 30_000 : 300_000),
  });
  const data = await response.json() as Record<string, any>;
  if (!response.ok || data.error) throw new Error(context.tool.errorMessage(data) || `火山方舟请求失败（HTTP ${response.status}）`);
  return data;
}

function mediaUrl(input: MediaInput) {
  if (input.type === "url") return input.url;
  const value = input.type === "binary" ? Buffer.from(input.data).toString("base64") : input.data;
  return value.startsWith("data:") ? value : `data:${input.mimeType};base64,${value}`;
}

async function wait(signal?: AbortSignal) {
  signal?.throwIfAborted();
  await new Promise<void>((resolve, reject) => {
    const abort = () => { clearTimeout(timer); reject(signal?.reason); };
    const timer = setTimeout(() => { signal?.removeEventListener("abort", abort); resolve(); }, 3000);
    signal?.addEventListener("abort", abort, { once: true });
  });
}

async function poll(context: Context, data: ProviderTaskData): Promise<MediaAsset[]> {
  if (data.baseUrl !== baseUrl(context) || typeof data.taskId !== "string" || !/^[\w-]+$/.test(data.taskId)) throw new Error("任务连接已改变，不能在另一服务查询原任务");
  const deadline = Date.now() + 60 * 60 * 1000;
  while (Date.now() < deadline) {
    context.signal?.throwIfAborted();
    const result = await requestJson(context, `/contents/generations/tasks/${encodeURIComponent(data.taskId)}`);
    if (result.status === "succeeded") {
      if (typeof result.content?.video_url !== "string") throw new Error("任务成功但未返回视频地址");
      return [{ type: "url", mediaType: "video", url: result.content.video_url }];
    }
    if (["failed", "expired", "cancelled", "canceled"].includes(result.status)) {
      throw Object.assign(new Error(context.tool.errorMessage(result) || `视频任务${result.status}`), { code: "MEDIA_TASK_FAILED" });
    }
    await wait(context.signal);
  }
  throw new Error("等待视频任务超时；已保留原任务 ID，可继续查询，不会自动重复提交");
}

export default {
  icon: "",
  id: "volcengine",
  label: "字节跳动 · 火山方舟",
  version: "1.0.0",
  readme: "直接使用火山方舟 API Key。视频支持 Seedance 文生、首尾帧与图片参考；图片支持 Seedream 文生图与参考图编辑。模型 ID 可改为你已开通的模型或接入点 ID。在线生成按供应商规则计费。其他兼容服务可更改 API 地址，须遵循相同协议。",
  rules,
  models: [
    { id: "doubao-seedance-2-5-260628", label: "Seedance 2.5", type: "video", mode: ["text", "startFrameOptional", "endFrameOptional", ["imageReference:30", "audioReference:10"]], audio: "optional", durationResolutionMap: [{ duration: [4, 5, 6, 8, 10, 12, 15, 20, 25, 30], resolution: ["480p", "720p", "1080p"] }] },
    { id: "doubao-seedream-5-0-pro-260628", label: "Seedream 5.0 Pro", type: "image", mode: ["text", "singleImage", "multiReference"], imageSizes: ["1K", "1.5K", "2K"], imageRatios: ["1:1", "16:9", "9:16", "4:3", "3:4"] },
  ],
  async generateImage(request) {
    // 图片接口使用像素尺寸表达比例，避免节点的比例选择被静默丢弃。
    let size = request.size || "2K";
    if (request.ratio && !/^\d+x\d+$/.test(size)) {
      const [width, height] = request.ratio.split(":").map(Number);
      const pixels = ({ "1K": 1024, "1.5K": 1536, "2K": 2048, "3K": 3072, "4K": 4096 } as Record<string, number>)[size];
      if (!pixels || !width || !height) throw new Error("图片尺寸或比例无效");
      size = `${Math.round(Math.sqrt(pixels * pixels * width / height) / 8) * 8}x${Math.round(Math.sqrt(pixels * pixels * height / width) / 8) * 8}`;
    }
    const data = await requestJson(this, "/images/generations", {
      model: request.model, prompt: request.prompt, size, response_format: "url",
      ...(request.images?.length ? { image: request.images.map(mediaUrl) } : {}),
    });
    if (!Array.isArray(data.data) || !data.data.length) throw new Error("未返回生成图片");
    return data.data.map((item: Record<string, unknown>): MediaAsset => {
      if (typeof item.url === "string") return { type: "url", mediaType: "image", url: item.url };
      if (typeof item.b64_json === "string") return { type: "base64", mediaType: "image", data: item.b64_json, mimeType: "image/png" };
      throw new Error(this.tool.errorMessage(item) || "图片响应格式错误");
    });
  },
  async generateVideo(request) {
    if (request.videos?.length) throw new Error("此直连接口的参考视频需要公网素材 URL；请使用支持上传的 API 适配器或 ComfyUI 工作流");
    const isFrames = ["singleImage", "startFrameOptional", "endFrameOptional", "startEndRequired"].includes(String(request.mode)) || !!request.firstFrame || !!request.lastFrame;
    if (isFrames && request.audios?.length) throw new Error("首尾帧模式与音频参考不能混用");
    const images = request.images ?? [];
    if (isFrames && (request.firstFrame || request.lastFrame) && images.length) throw new Error("首尾帧和参考图片不能混用");
    if (isFrames && images.length > 2) throw new Error("首尾帧模式最多两张图片");
    const firstFrame = request.firstFrame ?? (isFrames ? images[0] : undefined);
    const lastFrame = request.lastFrame ?? (isFrames ? images[1] : undefined);
    if (lastFrame && !firstFrame) throw new Error("尾帧需要同时提供首帧");
    const ordered = (request as VideoRequest & { referenceOrder?: ({ type: string; index?: number })[] }).referenceOrder;
    const prompt = request.prompt.replace(/\{\{ref (\d+)\}\}/g, (_, number: string) => {
      const ref = ordered?.[Number(number) - 1];
      if (!ref) throw new Error("引用标记缺少素材映射");
      if (ref.type === "firstFrame") return "首帧";
      if (ref.type === "lastFrame") return "尾帧";
      if (ref.type === "text") return `参考 ${number}`;
      if (isFrames && ref.type === "image") return ref.index === 0 ? "首帧" : "尾帧";
      return `${ref.type === "image" ? "@图片" : "@音频"}${(ref.index ?? 0) + 1}`;
    });
    const content: Record<string, unknown>[] = [{ type: "text", text: prompt }];
    const add = (input: MediaInput, type: string, role: string) => content.push({ type, [type]: { url: mediaUrl(input) }, role });
    if (firstFrame) add(firstFrame, "image_url", "first_frame");
    if (lastFrame) add(lastFrame, "image_url", "last_frame");
    if (!isFrames) for (const image of images) add(image, "image_url", "reference_image");
    for (const audio of request.audios ?? []) add(audio, "audio_url", "reference_audio");
    const body = { model: request.model, content, duration: request.duration, ratio: request.ratio, resolution: request.resolution, generate_audio: request.generateAudio };
    const data = await requestJson(this, "/contents/generations/tasks", body);
    if (typeof data.id !== "string") throw new Error("接口未返回任务 ID，请先核对供应商任务记录，勿重复提交");
    const task = { taskId: data.id, baseUrl: baseUrl(this) };
    await this.saveTaskData?.(task);
    return poll(this, task);
  },
  async resumeTask(data) { return poll(this, data); },
} satisfies ProviderDefinition<typeof rules>;
