import { z } from "zod";
import conf from "@/utils/conf";

const localAddress = z.url().refine(value => {
  const url = new URL(value);
  return ["http:", "https:"].includes(url.protocol) && ["127.0.0.1", "localhost", "[::1]"].includes(url.hostname)
    && !url.username && !url.password && !url.search && !url.hash && url.pathname === "/";
}, "请使用本机回环 HTTP(S) 地址；远程主机通过 SSH 隧道连接");
export const comfyAddress = z.url().refine(value => {
  const url = new URL(value);
  const host = url.hostname.toLowerCase();
  const parts = host.split(".").map(Number);
  const privateV4 = parts.length === 4 && parts.every(part => Number.isInteger(part) && part >= 0 && part <= 255)
    && (parts[0] === 10 || parts[0] === 127 || (parts[0] === 192 && parts[1] === 168) || (parts[0] === 172 && parts[1]! >= 16 && parts[1]! <= 31));
  return ["http:", "https:"].includes(url.protocol)
    && (privateV4 || host === "localhost" || host === "[::1]" || /^\[f[cd][0-9a-f]{2}:/.test(host) || host.endsWith(".local"))
    && !url.username && !url.password && !url.search && !url.hash && url.pathname === "/";
}, "ComfyUI 请使用本机或局域网 HTTP(S) 地址，例如 http://192.168.1.4:8188");

const workflow = z.string().max(2 * 1024 * 1024).refine(value => {
  if (!value.trim()) return true;
  try {
    const data = JSON.parse(value);
    return data && typeof data === "object" && !Array.isArray(data) && Object.keys(data).length > 0
      && Object.values(data).every((node: any) => node && typeof node.class_type === "string" && node.inputs && typeof node.inputs === "object" && !Array.isArray(node.inputs));
  } catch { return false; }
}, "请提供 ComfyUI API 格式的工作流 JSON");
export const comfyConfigSchema = z.object({
  imageUrl: comfyAddress.optional(), videoUrl: comfyAddress.optional(), checkpoint: z.string().max(2048).optional(),
  imageWorkflow: workflow.optional(), videoWorkflow: workflow.optional(),
  imageOutputNode: z.string().max(256).optional(), videoOutputNode: z.string().max(256).optional(),
  workflowModels: z.record(z.string().min(1).max(200), z.object({
    mediaType: z.literal("image"), workflow: workflow.refine(value => !!value.trim(), "独立工作流不能为空"), outputNode: z.string().max(256),
    inputMode: z.enum(["image", "text"]).optional(),
  }).strict()).refine(value => Object.keys(value).length <= 50, "独立工作流最多 50 个").optional(),
}).strict();

function workflowTokens(raw: string) {
  const graph = JSON.parse(raw);
  if (!graph || typeof graph !== "object" || Array.isArray(graph) || !Object.keys(graph).length) throw new Error("请提供 ComfyUI API 格式工作流");
  const tokens = new Set<string>();
  const visit = (value: unknown) => {
    if (typeof value === "string") for (const match of value.matchAll(/\{\{(\w+)\}\}/g)) tokens.add(match[1]!);
    else if (value && typeof value === "object") Object.values(value).forEach(visit);
  };
  for (const node of Object.values(graph) as { class_type?: string; inputs?: Record<string, unknown> }[]) {
    if (!node || typeof node.class_type !== "string" || !node.inputs || typeof node.inputs !== "object" || Array.isArray(node.inputs)) throw new Error("请提供 ComfyUI API 格式工作流");
    visit(node.inputs);
  }
  return tokens;
}

export function comfyVideoModes(config: Record<string, unknown>): VideoMode[] | undefined {
  if (typeof config.videoWorkflow !== "string" || !config.videoWorkflow.trim()) return;
  try {
    const refs = [...workflowTokens(config.videoWorkflow)].filter(token => /^(?:image\d+|firstFrame|lastFrame|video\d+|audio\d+)$/.test(token));
    if (!refs.length) return ["text"];
    // 单图模式在画布中只允许一张图片；旧版 H3 的 startFrameOptional 会错误地把它当作尾帧。
    if (refs.length === 1 && ["firstFrame", "image0"].includes(refs[0]!)) return ["singleImage"];
    if (refs.length === 2 && refs.includes("firstFrame") && refs.includes("lastFrame")) return ["startEndRequired"];
  } catch { /* 无效工作流由生成前校验给出具体错误。 */ }
}

function videoWorkflowConfig(config: Record<string, unknown>, request: VideoRequest) {
  let raw = typeof config.videoWorkflow === "string" ? config.videoWorkflow.trim() : "";
  if (!raw) throw new Error("请先在视频模型设置中应用并保存内置工作流");
  let tokens = workflowTokens(raw);
  // 兼容已保存的首帧工作流与单图模式；显式传入的尾帧绝不改作首帧。
  if (tokens.has("firstFrame") && !tokens.has("image0") && request.images?.length === 1 && !request.firstFrame && !request.lastFrame) {
    raw = raw.replaceAll("{{firstFrame}}", "{{image0}}");
    tokens = workflowTokens(raw);
  }
  const refs = new Set((request.images ?? []).map((_, index) => `image${index}`));
  if (request.firstFrame) refs.add("firstFrame");
  if (request.lastFrame) refs.add("lastFrame");
  if (request.videos?.length || request.audios?.length) throw new Error("当前 ComfyUI 视频接口不支持视频或音频参考");
  for (const token of refs) {
    if (tokens.has(token)) continue;
    if (token === "lastFrame") throw new Error("当前工作流不支持尾帧。首帧图生视频请使用单图参考模式；刷新模型列表后重新选择，不会忽略这张图片。");
    throw new Error("当前工作流没有对应的参考图输入，请选择首帧图生视频工作流并保存，不能忽略已传入的参考图");
  }
  for (const token of tokens) {
    if (/^(?:image\d+|firstFrame|lastFrame)$/.test(token) && !refs.has(token)) throw new Error(`当前工作流缺少 ${token === "firstFrame" ? "首帧图片" : token === "lastFrame" ? "尾帧图片" : "参考图"}，请连接或上传对应图片`);
  }
  return { ...config, videoWorkflow: raw };
}

export function comfyWorkflowConfig(config: Record<string, unknown>, request: ImageRequest | VideoRequest, mediaType: "image" | "video") {
  if (mediaType === "video") return videoWorkflowConfig(config, request as VideoRequest);
  const profiles = comfyConfigSchema.shape.workflowModels.parse(config.workflowModels);
  const profile = profiles && Object.hasOwn(profiles, request.model) ? profiles[request.model] : undefined;
  if (!profile) {
    if (["comfySd", "comfyFluxSchnell", "comfySdEdit", "comfyFluxSchnellEdit", "comfyQwenTurboEdit", "comfyQwenTurbo"].includes(request.model)) {
      throw new Error("此图片工作流尚未保存，请在图片模型设置中重新应用并保存对应预设");
    }
    return config;
  }
  if (mediaType !== profile.mediaType) throw new Error("工作流与媒体类型不匹配");
  if (profile.inputMode === "text") {
    if (request.images?.length) throw new Error("此文生图工作流不接受参考图，请选择对应的单图编辑或图生图方案");
  } else if (request.images?.length !== 1) throw new Error("此图生图工作流需要且只支持一张原图，请连接图片节点或上传一张参考图");
  if ((request as ImageRequest).mask) throw new Error("此工作流用于整图重绘，不支持蒙版局部编辑");
  let graph = profile.workflow;
  if (graph.includes('"{{denoise}}"')) {
    const strength = request.other?.denoise ?? 0.55;
    if (typeof strength !== "number" || !Number.isFinite(strength) || strength < 0.05 || strength > 1) throw new Error("重绘强度须为 0.05 到 1 之间的数字");
    graph = graph.replaceAll('"{{denoise}}"', String(strength));
  }
  return { ...config, imageWorkflow: graph, imageOutputNode: profile.outputNode };
}
export const localModelsSchema = z.object({
  comfyUrl: comfyAddress,
  factoryUrl: localAddress,
  applicationRoot: z.string().trim().max(4096),
}).strict();

export function localModelsConfig() {
  return localModelsSchema.parse({ comfyUrl: process.env.SDF_COMFY_URL || "http://127.0.0.1:8188",
    factoryUrl: process.env.SDF_BASE_URL || "http://127.0.0.1:8765", applicationRoot: process.env.SDF_APPLICATION_ROOT || "",
    ...(conf.get("settings", {}).localModels as Record<string, unknown> | undefined),
  });
}
