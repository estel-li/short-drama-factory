const rules = [
  { type: "input", field: "imageUrl", title: "图片 ComfyUI 地址", value: "http://127.0.0.1:8188", mediaType: "image" },
  { type: "input", field: "checkpoint", title: "图片大模型（Checkpoint 文件名）", value: "", mediaType: "image", props: { placeholder: "留空工作流时必填；从服务器读取后选择" } },
  { type: "input", field: "imageWorkflow", title: "图片工作流（API 格式 JSON，可选）", value: "", mediaType: "image", props: { type: "textarea", rows: 8 } },
  { type: "input", field: "imageOutputNode", title: "图片输出节点 ID（可选）", value: "", mediaType: "image" },
  { type: "input", field: "videoUrl", title: "视频 ComfyUI 地址", value: "http://127.0.0.1:8188", mediaType: "video" },
  { type: "input", field: "videoWorkflow", title: "视频工作流（API 格式 JSON，必填）", value: "", mediaType: "video", props: { type: "textarea", rows: 8 } },
  { type: "input", field: "videoOutputNode", title: "视频输出节点 ID（可选）", value: "", mediaType: "video" },
] as const;

type Context = ProviderContext<ProviderConfig<typeof rules>>;
type Workflow = Record<string, { class_type: string; inputs: Record<string, unknown>; _meta?: unknown }>;

function baseUrl(value: string) {
  const url = new URL(value.trim());
  const host = url.hostname.toLowerCase();
  const parts = host.split(".").map(Number);
  const privateV4 = parts.length === 4 && parts.every(value => Number.isInteger(value) && value >= 0 && value <= 255)
    && (parts[0] === 10 || parts[0] === 127 || (parts[0] === 192 && parts[1] === 168) || (parts[0] === 172 && parts[1]! >= 16 && parts[1]! <= 31));
  const local = privateV4 || host === "localhost" || host === "[::1]" || /^\[f[cd][0-9a-f]{2}:/.test(host) || host.endsWith(".local");
  if (!/^https?:$/.test(url.protocol) || !local || url.username || url.password || url.search || url.hash || url.pathname !== "/") throw new Error("ComfyUI 请填写本机或局域网 HTTP(S) 地址，如 http://192.168.1.4:8188");
  return url.origin;
}

async function json(context: Context, base: string, path: string, body?: unknown) {
  const response = await context.tool.fetch(`${base}${path}`, {
    method: body === undefined ? "GET" : "POST", redirect: "error", signal: AbortSignal.timeout(60_000),
    headers: body instanceof FormData ? undefined : { "Content-Type": "application/json" },
    body: body === undefined ? undefined : body instanceof FormData ? body : JSON.stringify(body),
  });
  const value = await response.json() as Record<string, any>;
  if (!response.ok || value.error || (value.node_errors && Object.keys(value.node_errors).length)) {
    throw new Error(context.tool.errorMessage(value) || `ComfyUI 请求失败（HTTP ${response.status}）`);
  }
  return value;
}

async function delay(signal?: AbortSignal) {
  signal?.throwIfAborted();
  await new Promise<void>((resolve, reject) => {
    const abort = () => { clearTimeout(timer); reject(signal?.reason); };
    const timer = setTimeout(() => { signal?.removeEventListener("abort", abort); resolve(); }, 1500);
    signal?.addEventListener("abort", abort, { once: true });
  });
}

async function poll(context: Context, task: ProviderTaskData): Promise<MediaAsset[]> {
  if (task.mediaType !== "image" && task.mediaType !== "video") throw new Error("ComfyUI 任务类型无效");
  const mediaType = task.mediaType;
  const base = baseUrl(context.config[mediaType === "image" ? "imageUrl" : "videoUrl"]);
  if (base !== task.baseUrl || typeof task.promptId !== "string" || !/^[\w-]+$/.test(task.promptId)) throw new Error("ComfyUI 地址已改变，请恢复原地址后查询原任务");
  const deadline = Date.now() + 2 * 60 * 60 * 1000;
  while (Date.now() < deadline) {
    context.signal?.throwIfAborted();
    const entry = (await json(context, base, `/history/${encodeURIComponent(task.promptId)}`))[task.promptId];
    if (entry?.status?.status_str === "error") {
      const detail = entry.status.messages?.find((item: unknown[]) => item[0] === "execution_error")?.[1];
      throw Object.assign(new Error(context.tool.errorMessage(detail) || String(detail?.exception_message || "ComfyUI 工作流执行失败")), { code: "MEDIA_TASK_FAILED" });
    }
    if (entry?.status?.completed) {
      const assets: MediaAsset[] = [];
      const seen = new Set<string>();
      for (const [id, output] of Object.entries(entry.outputs ?? {})) {
        if (task.outputNode && id !== task.outputNode) continue;
        for (const items of Object.values(output as Record<string, unknown>)) {
          if (!Array.isArray(items)) continue;
          for (const file of items) {
            if (!file || typeof file.filename !== "string" || file.type === "temp" || file.type === "input") continue;
            const matches = mediaType === "image" ? /\.(png|jpe?g|webp|avif)$/i : /\.(mp4|webm|mov)$/i;
            if (!matches.test(file.filename)) continue;
            const query = new URLSearchParams({ filename: file.filename, subfolder: String(file.subfolder ?? ""), type: String(file.type ?? "output") });
            const url = `${base}/view?${query}`;
            if (!seen.has(url)) assets.push({ type: "url", mediaType, url });
            seen.add(url);
          }
        }
      }
      if (!assets.length) throw new Error(`工作流已完成，但没有${mediaType === "image" ? "图片" : "视频"}输出；请检查保存节点与输出节点 ID`);
      return assets;
    }
    await delay(context.signal);
  }
  throw new Error("等待 ComfyUI 超时；原任务 ID 已保留，可继续查询，不会自动重新提交");
}

function parseWorkflow(value: string): Workflow {
  const workflow = JSON.parse(value);
  if (!workflow || typeof workflow !== "object" || Array.isArray(workflow) || !Object.keys(workflow).length
    || Object.values(workflow).some((node: any) => !node || typeof node.class_type !== "string" || !node.inputs || typeof node.inputs !== "object" || Array.isArray(node.inputs))) {
    throw new Error("请导入 ComfyUI 的 API 格式工作流，不是普通画布 JSON");
  }
  return workflow;
}

async function generate(context: Context, mediaType: "image" | "video", request: ImageRequest | VideoRequest): Promise<MediaAsset[]> {
  const base = baseUrl(context.config[mediaType === "image" ? "imageUrl" : "videoUrl"]);
  const raw = context.config[mediaType === "image" ? "imageWorkflow" : "videoWorkflow"].trim();
  const seed = Math.floor(Math.random() * 2 ** 48);
  const [rw, rh] = (request.ratio || "1:1").split(":").map(Number);
  const size = (request as ImageRequest).size || "1024x1024";
  const match = /^(\d+)x(\d+)$/.exec(size);
  const pixels = match ? Number(match[1]) * Number(match[2]) : ({ "1K": 1024 ** 2, "2K": 2048 ** 2, "4K": 4096 ** 2 } as Record<string, number>)[size] ?? 1024 ** 2;
  const width = Math.round(Math.sqrt(pixels * rw! / rh!) / 8) * 8;
  const height = Math.round(Math.sqrt(pixels * rh! / rw!) / 8) * 8;
  let workflow: Workflow;
  if (raw) workflow = parseWorkflow(raw);
  else {
    if (mediaType === "video") throw new Error("请先在视频模型设置中导入适合本机模型的 ComfyUI API 工作流");
    if (request.images?.length) throw new Error("默认文生图工作流不接受参考图，请导入含 {{image0}} 等绑定的图生图工作流");
    if (!context.config.checkpoint.trim()) throw new Error("请先在图片模型设置中读取并选择 ComfyUI Checkpoint，或导入自定义工作流");
    workflow = {
      "3": { class_type: "KSampler", inputs: { seed, steps: 20, cfg: 7, sampler_name: "euler", scheduler: "normal", denoise: 1, model: ["4", 0], positive: ["6", 0], negative: ["7", 0], latent_image: ["5", 0] } },
      "4": { class_type: "CheckpointLoaderSimple", inputs: { ckpt_name: context.config.checkpoint.trim() } },
      "5": { class_type: "EmptyLatentImage", inputs: { width, height, batch_size: 1 } },
      "6": { class_type: "CLIPTextEncode", inputs: { text: "{{prompt}}", clip: ["4", 1] } },
      "7": { class_type: "CLIPTextEncode", inputs: { text: "", clip: ["4", 1] } },
      "8": { class_type: "VAEDecode", inputs: { samples: ["3", 0], vae: ["4", 2] } },
      "9": { class_type: "SaveImage", inputs: { filename_prefix: "shortDramaFactory", images: ["8", 0] } },
    };
  }
  const serialized = JSON.stringify(workflow);
  if (!serialized.includes("{{prompt}}")) throw new Error("工作流提示词输入需包含 {{prompt}}，才能接收画布节点提示词");
  const tokens: Record<string, unknown> = { prompt: request.prompt, seed, width, height, model: context.config.checkpoint.trim() || request.model,
    duration: (request as VideoRequest).duration, resolution: (request as VideoRequest).resolution, ratio: request.ratio, generateAudio: (request as VideoRequest).generateAudio };
  const refs: [string, MediaInput][] = (request.images ?? []).map((input, index) => [`image${index}`, input]);
  const video = request as VideoRequest;
  if (video.firstFrame) refs.push(["firstFrame", video.firstFrame]);
  if (video.lastFrame) refs.push(["lastFrame", video.lastFrame]);
  if (video.videos?.length || video.audios?.length) throw new Error("此通用 ComfyUI 接口支持文本与图片输入；视频／音频参考请使用完整工作流节点");
  for (const [token] of refs) if (!serialized.includes(`{{${token}}}`)) throw new Error(`工作流没有 {{${token}}} 绑定，不能忽略已传入的参考图`);
  for (const [token, input] of refs) {
    if (input.type === "url") throw new Error("参考图需要先导入工作区");
    const bytes = input.type === "binary" ? input.data : Buffer.from(input.data.replace(/^data:[^,]*,/, ""), "base64");
    const extension = /jpeg/i.test(input.mimeType) ? "jpg" : /webp/i.test(input.mimeType) ? "webp" : "png";
    const form = new FormData();
    form.append("image", new Blob([new Uint8Array(bytes).buffer], { type: input.mimeType }), `sdf${seed}${token}.${extension}`);
    form.append("overwrite", "false");
    const uploaded = await json(context, base, "/upload/image", form);
    if (typeof uploaded.name !== "string") throw new Error("ComfyUI 未返回上传文件名");
    tokens[token] = uploaded.subfolder ? `${uploaded.subfolder}/${uploaded.name}` : uploaded.name;
  }
  const replace = (value: unknown): unknown => {
    if (typeof value === "string") {
      const full = /^\{\{(\w+)\}\}$/.exec(value);
      const tokenValue = (key: string) => {
        if (!Object.hasOwn(tokens, key) || tokens[key] === undefined) throw new Error(`工作流变量 {{${key}}} 没有对应输入`);
        return tokens[key];
      };
      return full ? tokenValue(full[1]!) : value.replace(/\{\{(\w+)\}\}/g, (_, key: string) => String(tokenValue(key)));
    }
    if (Array.isArray(value)) return value.map(replace);
    if (value && typeof value === "object") return Object.fromEntries(Object.entries(value).map(([key, item]) => [key, replace(item)]));
    return value;
  };
  workflow = replace(workflow) as Workflow;
  const outputNode = context.config[mediaType === "image" ? "imageOutputNode" : "videoOutputNode"].trim();
  if (outputNode && !workflow[outputNode]) throw new Error("配置的输出节点 ID 不在工作流中");
  const result = await json(context, base, "/prompt", { prompt: workflow });
  if (typeof result.prompt_id !== "string") throw new Error("ComfyUI 未返回任务 ID，请核对队列后再操作");
  const task = { promptId: result.prompt_id, baseUrl: base, mediaType, outputNode };
  await context.saveTaskData?.(task);
  return poll(context, task);
}

export default {
  icon: "",
  id: "comfyUi", label: "ComfyUI · 本机 / 局域网", version: "1.0.0",
  readme: "地址由工作台服务端访问，支持本机或局域网。图片可直接选择 SD / SDXL 兼容 Checkpoint；Flux、Qwen、MiniMax H3 等使用匹配的 API 工作流。工作流提示词绑定 {{prompt}}；参考图绑定 {{image0}}、{{image1}}；首尾帧绑定 {{firstFrame}}、{{lastFrame}}；可选 {{seed}}、{{width}}、{{height}}、{{duration}}、{{model}}。变量必须写在输入值中，单独的数字变量用字符串占位，执行时恢复为数字。停止等待不清空 ComfyUI 队列；可按原任务续查。",
  rules,
  models: [
    { id: "comfyImage", label: "ComfyUI 图片工作流", type: "image", mode: ["text", "singleImage", "multiReference"], imageSizes: ["512x512", "768x768", "1024x1024"], imageRatios: ["1:1", "16:9", "9:16", "4:3", "3:4"] },
    { id: "comfyVideo", label: "ComfyUI 视频工作流 · H3 等", type: "video", mode: ["text", "startFrameOptional", "endFrameOptional", ["imageReference:16"]], audio: "optional", durationResolutionMap: [{ duration: [4, 5, 6, 8, 10, 12, 15, 20, 30], resolution: ["480p", "720p", "1080p"] }] },
  ],
  async getPrice() { return { price: "自有 ComfyUI", tips: "由你连接的 ComfyUI 与指定工作流执行" }; },
  async generateImage(request) { return generate(this, "image", request); },
  async generateVideo(request) { return generate(this, "video", request); },
  async resumeTask(data) { return poll(this, data); },
} satisfies ProviderDefinition<typeof rules>;
