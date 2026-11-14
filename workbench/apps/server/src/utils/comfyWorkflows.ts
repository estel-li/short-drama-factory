import { z } from "zod";
import { comfyAddress } from "@/utils/localModels";
import sd from "@comfyPresets/sd.json";
import fluxSchnell from "@comfyPresets/fluxSchnell.json";
import sdEdit from "@comfyPresets/sdEdit.json";
import fluxSchnellEdit from "@comfyPresets/fluxSchnellEdit.json";
import qwenTurbo from "@comfyPresets/qwenTurbo.json";
import qwenTurboEdit from "@comfyPresets/qwenTurboEdit.json";
import miniMaxH3Image from "@comfyPresets/miniMaxH3Image.json";
import h3StandardText from "@comfyPresets/h3StandardText.json";
import h3StandardImage from "@comfyPresets/h3StandardImage.json";
import h3TurboText from "@comfyPresets/h3TurboText.json";
import h3TurboImage from "@comfyPresets/h3TurboImage.json";

type Graph = Record<string, { class_type: string; inputs: Record<string, unknown> }>;
type Loader = { node: string; match: RegExp };
type Field = Loader & { key: string; label: string; input: string; gguf?: Loader };
type Preset = { id: string; label: string; mediaType: "image" | "video"; description: string; source: string; fields: Field[] };
const checkpoint: Field = { key: "checkpoint", label: "Checkpoint", node: "CheckpointLoaderSimple", input: "ckpt_name", match: /^(?!.*(?:flux|qwen|turbo|lightning)).+/i };
const diffusion: Field = { key: "diffusion", label: "扩散模型", node: "UNETLoader", input: "unet_name", match: /qwen_image_2\.1_turbo.*\.safetensors$/i };
const encoder: Field = { key: "encoder", label: "文本编码器", node: "CLIPLoader", input: "clip_name", match: /qwen3vl_8b.*\.safetensors$/i };
const vae: Field = { key: "vae", label: "VAE", node: "VAELoader", input: "vae_name", match: /qwen_image_2\.1_vae.*\.safetensors$/i };
const h3Fields: Field[] = [
  { ...diffusion, match: /minimax_h3_fl2va_(?:pruned_)?(?:int8_convrot|bf16|fp8_scaled|w[468]a8)\.safetensors$/i },
  { ...encoder, match: /qwen3vl_32b_minimax_h3.*\.safetensors$/i },
  { ...vae, label: "视频 VAE", match: /minimax_h3_video_vae.*\.safetensors$/i },
  { ...vae, key: "audioVae", label: "音频 VAE", match: /minimax_h3_audio_vae.*\.safetensors$/i },
];
const h3Source = "https://github.com/Comfy-Org/workflow_templates/blob/main/templates/video_minimax_h3_";
const h3ImagePreset = "miniMaxH3Image";
const h3ImageDiffusionMatch = /^minimax[-_]h3[-_]image[-_].*\.(?:safetensors|gguf)$/i;
const h3ImageFields: Field[] = [
  { ...diffusion, match: h3ImageDiffusionMatch, gguf: { node: "UnetLoaderGGUF", match: h3ImageDiffusionMatch } },
  { ...encoder, match: /^qwen3vl_32b_minimax_h3.*\.safetensors$/i,
    gguf: { node: "CLIPLoaderGGUF", match: /^qwen3vl_32b_(?:minimax_)?h3[-_].*\.gguf$/i } },
  { ...vae, label: "图片 VAE", match: /^minimax_h3_image_vae_fp16\.safetensors$/i },
];
const modelScope = "https://www.modelscope.cn/models";
const h3ImageGgufRepo = `${modelScope}/Abiray/MiniMax-H3-Image-GGUF`;
const presets: Preset[] = [
  { id: "sd", label: "SD / SDXL · 文生图", mediaType: "image", description: "标准 Checkpoint 文生图，20 步、CFG 7、Euler。SDXL 建议 1024 像素；SD 1.5 建议 512 像素。不适用 Turbo / Lightning 权重。", source: "https://comfyanonymous.github.io/ComfyUI_examples/sdxl/", fields: [checkpoint] },
  { id: "fluxSchnell", label: "FLUX.1 Schnell FP8 · 文生图", mediaType: "image", description: "包含文本编码器与 VAE 的 Schnell FP8 Checkpoint；4 步、CFG 1、Euler / simple。分体模型和 FLUX Dev 不适用。", source: "https://comfyanonymous.github.io/ComfyUI_examples/flux/", fields: [{ ...checkpoint, match: /flux1[-_]schnell[-_]fp8\.safetensors$/i }] },
  { id: "sdEdit", label: "SD / SDXL · 图生图", mediaType: "image", description: "单张原图重绘，20 步、CFG 7。按节点尺寸和比例缩放、居中裁切；重绘强度默认 0.55，可在画布图片生成设置中调整，越低越接近原图。适合标准 SD / SDXL Checkpoint。", source: "https://comfyanonymous.github.io/ComfyUI_examples/img2img/", fields: [checkpoint] },
  { id: "fluxSchnellEdit", label: "FLUX.1 Schnell FP8 · 图生图", mediaType: "image", description: "使用现有 Schnell FP8 Checkpoint 对一张图片重绘，4 步、CFG 1。按节点尺寸和比例缩放、居中裁切；重绘强度默认 0.55，可在画布图片生成设置中调整。这是基于原图的重绘，精确指令编辑可使用 Qwen 编辑方案。", source: "https://comfyanonymous.github.io/ComfyUI_examples/img2img/", fields: [{ ...checkpoint, match: /flux1[-_]schnell[-_]fp8\.safetensors$/i }] },
  ...[false, true].map(edit => ({ id: edit ? "qwenTurboEdit" : "qwenTurbo", label: `Qwen Image 2.1 Turbo · ${edit ? "图生图（单图编辑）" : "文生图"}`, mediaType: "image" as const, description: `Turbo 完整权重，官方 8 步 sigma 序列、Euler、CFG 1。${edit ? "请上传一张参考图，使用原图比例，编码分辨率 1024。" : "使用画布提示词与图片尺寸。"} 需要 TextEncodeQwenImage21 节点。`, source: `https://docs.comfy.org/tutorials/image/qwen/qwen-image-2-1#qwen-image-2-1-turbo-${edit ? "image-edit" : "text-to-image"}`, fields: [diffusion, encoder, vae] })),
  { id: h3ImagePreset, label: "MiniMax H3 Image · 文生图", mediaType: "image", description: "基于 ComfyUI 官方文生图模板，使用 6 步、Euler / simple、CFG 1。直接使用画布提示词和尺寸，关闭可选提示词增强。支持官方 Safetensors 和 GGUF 量化权重。", source: "https://github.com/Comfy-Org/workflow_templates/blob/c8e48bdcfc7241d7af588d20d4f924caf9d9d953/templates/image_minimax_h3_image_t2i.json", fields: h3ImageFields },
  ...[false, true].flatMap(turbo => [false, true].map(image => ({
    id: `h3${turbo ? "Turbo" : "Standard"}${image ? "Image" : "Text"}`, label: `MiniMax H3 · ${image ? "首帧图生视频" : "文生视频"} · ${turbo ? "4 步快速" : "20 步标准"}`,
    mediaType: "video" as const, description: `原生音画、24 fps，时长按 17k+5 帧对齐，可能稍长于输入时长。固定约 0.4MP，比例随画布；VAE 分块解码适配较低显存。${turbo ? "需要 FL2V 的 4 步 LightX2V LoRA，不能选 Ref2VA 或 8 步 LoRA。" : "不加载加速 LoRA。"}${image ? "需在首帧栏上传一张图片。" : "仅接受文本提示词。"}`,
    source: `${h3Source}${image ? "i2v" : "t2v"}.json`, fields: turbo ? [...h3Fields, { key: "lora", label: "4 步加速 LoRA", node: "LoraLoaderModelOnly", input: "lora_name", match: /minimax_h3_fl2v.*(?:4step|4_step).*\.safetensors$/i }] : h3Fields,
  }))),
];
export const catalogSchema = z.object({ url: comfyAddress, mediaType: z.enum(["image", "video"]) }).strict();
export const buildSchema = catalogSchema.extend({ preset: z.string().max(80), models: z.record(z.string().max(80), z.string().max(2048)) });

async function objectInfo(url: string) {
  const response = await fetch(new URL("/object_info", url), { redirect: "error", signal: AbortSignal.timeout(20000) });
  if (!response.ok) throw Object.assign(new Error(`读取 ComfyUI 节点失败（${response.status}）`), { status: 502 });
  const info = await response.json() as Record<string, any>;
  if (!info || typeof info !== "object" || Array.isArray(info) || !Object.values(info).some(node => node && typeof node === "object" && node.input)) {
    throw Object.assign(new Error("不是有效的 ComfyUI 节点目录"), { status: 502 });
  }
  return info;
}
function inputOptions(info: Record<string, any>, node: string, input: string) {
  const spec = info[node]?.input?.required?.[input];
  const values = Array.isArray(spec?.[0]) ? spec[0] : spec?.[1]?.options;
  return Array.isArray(values) ? values.filter((value): value is string => typeof value === "string") : [];
}
function choices(info: Record<string, any>, field: Field) {
  const priority = (name: string) => /nvfp4_awq/i.test(name) ? 0 : /int8_convrot|w4a8/i.test(name) ? 1 : 2;
  const gguf = field.gguf;
  const native = inputOptions(info, field.node, field.input).filter(value => !gguf || !/\.gguf$/i.test(value));
  const quantized = gguf && (field.key !== "encoder" || inputOptions(info, gguf.node, "type").includes("minimax"))
    ? inputOptions(info, gguf.node, field.input).filter(value => /\.gguf$/i.test(value) && gguf.match.test(value)) : [];
  return [...new Set([...native.filter(value => field.match.test(value)), ...quantized])]
    .sort((a, b) => priority(a) - priority(b) || a.length - b.length || a.localeCompare(b));
}

async function imageGpu(url: string) {
  try {
    const response = await fetch(new URL("/system_stats", url), { redirect: "error", signal: AbortSignal.timeout(3500) });
    if (!response.ok) return;
    const stats = await response.json() as { devices?: { name?: string; type?: string; vram_total?: number }[] };
    // ComfyUI lists its primary device first. Report that device's VRAM, even on a multi-GPU host.
    const device = stats.devices?.[0];
    if (device?.type && device.type !== "cpu" && device.type !== "mps" && typeof device.name === "string"
      && Number.isFinite(device.vram_total) && device.vram_total! > 0) {
      return { name: device.name, vramGiB: Math.round(device.vram_total! / 1024 ** 3) };
    }
  } catch { /* The preset remains available if hardware details cannot be read. */ }
}

function h3ImageDownloads(gpu: Awaited<ReturnType<typeof imageGpu>>, info: Record<string, any>, fields: { key: string; options: string[] }[]) {
  const vram = gpu?.vramGiB ?? 0;
  const quant = vram >= 24 ? "Q5_K_M" : vram >= 16 ? "Q4_K_M" : vram >= 12 ? "Q3_K_M" : vram >= 8 ? "Q2_K" : "";
  const diffusionFile = quant ? `MiniMax-H3-Image-Pruned-${quant}.gguf` : "";
  // The quantizer's example uses the Q3 encoder. Reuse either a compatible native or GGUF encoder when present.
  const encoderPath = vram >= 24 ? "Abiray/MiniMax-H3-GGUF/resolve/master/text_encoders/qwen3vl_32b_minimax_h3-Q4_K_M.gguf"
    : "Abiray/Qwen3-VL-32B-Instruct-GGUF/resolve/master/Qwen3vl_32b_h3-Q3_K_M.gguf";
  const downloads = [
    { key: "diffusion", file: diffusionFile, directory: "models/diffusion_models", url: `${h3ImageGgufRepo}/resolve/master/${diffusionFile}` },
    { key: "encoder", file: encoderPath.split("/").at(-1)!, directory: "models/text_encoders", url: `${modelScope}/${encoderPath}` },
    { key: "vae", file: "minimax_h3_image_vae_fp16.safetensors", directory: "models/vae", url: `${modelScope}/Comfy-Org/MiniMax-H3-Image/resolve/master/vae/minimax_h3_image_vae_fp16.safetensors` },
  ].filter(file => !fields.find(field => field.key === file.key)?.options.length);
  const ggufNodes: string[] = [];
  if (!info.UnetLoaderGGUF && downloads.some(file => file.key === "diffusion")) ggufNodes.push("UnetLoaderGGUF");
  if (!inputOptions(info, "CLIPLoaderGGUF", "type").includes("minimax") && downloads.some(file => file.key === "encoder")) ggufNodes.push("CLIPLoaderGGUF（minimax）");
  return { gpu, repo: h3ImageGgufRepo, files: downloads.filter(file => file.file), needsManualChoice: downloads.some(file => !file.file),
    ggufNodes };
}
const workflowTemplates: Record<string, Graph> = {
  sd, fluxSchnell, sdEdit, fluxSchnellEdit, qwenTurbo, qwenTurboEdit, miniMaxH3Image,
  h3StandardText, h3StandardImage, h3TurboText, h3TurboImage,
};

function graphFor(preset: Preset, models: Record<string, string | undefined>): Graph {
  const graph = structuredClone(workflowTemplates[preset.id]!);
  const fields = new Map(preset.fields.map(field => [`{{${field.key}}}`, field]));
  for (const node of Object.values(graph)) {
    for (const [input, value] of Object.entries(node.inputs)) {
      const field = typeof value === "string" ? fields.get(value) : undefined;
      if (!field || node.class_type !== field.node || input !== field.input) continue;
      const file = models[field.key];
      node.inputs[input] = file;
      if (!field.gguf || !/\.gguf$/i.test(file ?? "")) continue;
      node.class_type = field.gguf.node;
      if (field.key === "diffusion") delete node.inputs.weight_dtype;
      if (field.key === "encoder") delete node.inputs.device;
    }
  }
  return graph;
}

function presetModelId(preset: Preset) {
  return preset.mediaType === "video" ? "comfyVideo" : `comfy${preset.id[0]!.toUpperCase()}${preset.id.slice(1)}`;
}

export async function catalog(url: string, mediaType: "image" | "video") {
  const [info, gpu] = await Promise.all([objectInfo(url), mediaType === "image" ? imageGpu(url) : undefined]);
  return presets.filter(preset => preset.mediaType === mediaType).map(preset => {
    const fields = preset.fields.map(field => ({ key: field.key, label: field.label, node: field.node, ggufNode: field.gguf?.node, input: field.input, options: choices(info, field) }));
    const models = preset.id === h3ImagePreset ? Object.fromEntries(fields.map(field => [field.key, field.options[0] ?? ""])) : {};
    return { ...preset, modelId: presetModelId(preset), inputMode: preset.id.endsWith("Edit") || (mediaType === "video" && preset.id.endsWith("Image")) ? "image" : "text",
      fields, missingNodes: [...new Set(Object.values(graphFor(preset, models)).map(node => node.class_type))].filter(name => !info[name]),
      ...(preset.id === h3ImagePreset ? { downloads: h3ImageDownloads(gpu, info, fields) } : {}),
    };
  });
}

export async function build(body: z.infer<typeof buildSchema>) {
  const preset = presets.find(item => item.id === body.preset && item.mediaType === body.mediaType);
  if (!preset) throw Object.assign(new Error("请选择对应类型的内置工作流"), { status: 400 });
  const info = await objectInfo(body.url);
  const workflow = graphFor(preset, body.models);
  const missing = [...new Set(Object.values(workflow).map(node => node.class_type))].filter(name => !info[name]);
  if (missing.length) throw Object.assign(new Error(`当前 ComfyUI 缺少节点：${missing.join("、")}。请更新对应 ComfyUI 或切换到兼容环境后重新读取。`), { status: 409 });
  for (const field of preset.fields) {
    if (!choices(info, field).includes(body.models[field.key] ?? "")) throw Object.assign(new Error(`${field.label} 不存在或不匹配此工作流，请重新读取模型`), { status: 400 });
  }
  const video = preset.mediaType === "video";
  const imageEdit = !video && preset.id.endsWith("Edit");
  const independent = !video;
  const model = video
    ? { id: "comfyVideo", label: preset.label, type: "video", mode: preset.id.endsWith("Image") ? ["singleImage"] : ["text"], audio: true, durationResolutionMap: [{ duration: [4, 5, 6, 8, 10, 12, 15], resolution: ["480p"] }] }
    : { id: presetModelId(preset), label: preset.label, type: "image", mode: imageEdit ? ["singleImage"] : ["text"], imageSizes: preset.id === h3ImagePreset ? ["2048x2048", "1024x1024", "4096x4096"] : preset.id.startsWith("sd") ? ["512x512", "768x768", "1024x1024"] : ["1024x1024"], imageRatios: ["1:1", "16:9", "9:16", "4:3", "3:4"],
      ...(["sdEdit", "fluxSchnellEdit"].includes(preset.id) ? { rules: [{ type: "inputNumber", field: "denoise", title: "重绘强度（越高变化越大）", value: 0.55, props: { min: 0.05, max: 1, step: 0.05, precision: 2 } }] } : {}) };
  return { workflow, outputNode: "output", model, label: preset.label, independent, inputMode: imageEdit || (video && preset.id.endsWith("Image")) ? "image" : "text" };
}
