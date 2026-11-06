import { z } from "zod";
import { comfyAddress } from "@/utils/localModels";

type Graph = Record<string, { class_type: string; inputs: Record<string, unknown> }>;
type Field = { key: string; label: string; node: string; input: string; match: RegExp };
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
const presets: Preset[] = [
  { id: "sd", label: "SD / SDXL · 文生图", mediaType: "image", description: "标准 Checkpoint 文生图，20 步、CFG 7、Euler。SDXL 建议 1024 像素；SD 1.5 建议 512 像素。不适用 Turbo / Lightning 权重。", source: "https://comfyanonymous.github.io/ComfyUI_examples/sdxl/", fields: [checkpoint] },
  { id: "fluxSchnell", label: "FLUX.1 Schnell FP8 · 文生图", mediaType: "image", description: "包含文本编码器与 VAE 的 Schnell FP8 Checkpoint；4 步、CFG 1、Euler / simple。分体模型和 FLUX Dev 不适用。", source: "https://comfyanonymous.github.io/ComfyUI_examples/flux/", fields: [{ ...checkpoint, match: /flux1[-_]schnell[-_]fp8\.safetensors$/i }] },
  { id: "sdEdit", label: "SD / SDXL · 图生图", mediaType: "image", description: "单张原图重绘，20 步、CFG 7。按节点尺寸和比例缩放、居中裁切；重绘强度默认 0.55，可在画布图片生成设置中调整，越低越接近原图。适合标准 SD / SDXL Checkpoint。", source: "https://comfyanonymous.github.io/ComfyUI_examples/img2img/", fields: [checkpoint] },
  { id: "fluxSchnellEdit", label: "FLUX.1 Schnell FP8 · 图生图", mediaType: "image", description: "使用现有 Schnell FP8 Checkpoint 对一张图片重绘，4 步、CFG 1。按节点尺寸和比例缩放、居中裁切；重绘强度默认 0.55，可在画布图片生成设置中调整。这是基于原图的重绘，精确指令编辑可使用 Qwen 编辑方案。", source: "https://comfyanonymous.github.io/ComfyUI_examples/img2img/", fields: [{ ...checkpoint, match: /flux1[-_]schnell[-_]fp8\.safetensors$/i }] },
  ...[false, true].map(edit => ({ id: edit ? "qwenTurboEdit" : "qwenTurbo", label: `Qwen Image 2.1 Turbo · ${edit ? "图生图（单图编辑）" : "文生图"}`, mediaType: "image" as const, description: `Turbo 完整权重，官方 8 步 sigma 序列、Euler、CFG 1。${edit ? "请上传一张参考图，使用原图比例，编码分辨率 1024。" : "使用画布提示词与图片尺寸。"} 需要 TextEncodeQwenImage21 节点。`, source: `https://docs.comfy.org/tutorials/image/qwen/qwen-image-2-1#qwen-image-2-1-turbo-${edit ? "image-edit" : "text-to-image"}`, fields: [diffusion, encoder, vae] })),
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
function choices(info: Record<string, any>, field: Field) {
  const spec = info[field.node]?.input?.required?.[field.input];
  const values = Array.isArray(spec?.[0]) ? spec[0] : spec?.[1]?.options;
  if (!Array.isArray(values)) return [];
  const priority = (name: string) => /nvfp4_awq/i.test(name) ? 0 : /int8_convrot|w4a8/i.test(name) ? 1 : 2;
  return values.filter((value): value is string => typeof value === "string" && field.match.test(value))
    .sort((a, b) => priority(a) - priority(b) || a.length - b.length || a.localeCompare(b));
}
function graphFor(id: string, models: Record<string, string>): Graph {
  const graph: Graph = {};
  const node = (id: string, type: string, inputs: Record<string, unknown>) => { graph[id] = { class_type: type, inputs }; };
  if (id.startsWith("h3")) {
    const turbo = id.includes("Turbo");
    node("1", "UNETLoader", { unet_name: models.diffusion, weight_dtype: "default" });
    node("2", "CLIPLoader", { clip_name: models.encoder, type: "minimax", device: "default" });
    node("3", "VAELoader", { vae_name: models.vae });
    node("4", "VAELoader", { vae_name: models.audioVae });
    node("5", "ComfyMathExpression", { expression: "max(5, round(a * 24)) + (5 - (max(5, round(a * 24)) % 17)) % 17", "values.a": "{{duration}}" });
    node("6", "ComfyMathExpression", { expression: "round(sqrt(400000 * a / b) / 32) * 32", "values.a": "{{width}}", "values.b": "{{height}}" });
    node("7", "ComfyMathExpression", { expression: "round(sqrt(400000 * b / a) / 32) * 32", "values.a": "{{width}}", "values.b": "{{height}}" });
    node("8", "MiniMaxH3ImageToVideo", { clip: ["2", 0], vae: ["3", 0], prompt: "{{prompt}}", width: ["6", 1], height: ["7", 1], length: ["5", 1] });
    if (id.endsWith("Image")) { node("20", "LoadImage", { image: "{{firstFrame}}" }); graph["8"]!.inputs.first_frame = ["20", 0]; }
    if (turbo) node("21", "LoraLoaderModelOnly", { model: ["1", 0], lora_name: models.lora, strength_model: 1 });
    const model = [turbo ? "21" : "1", 0];
    node("9", "RandomNoise", { noise_seed: "{{seed}}" });
    node("10", "BasicGuider", { model, conditioning: ["8", 0] });
    node("11", "KSamplerSelect", { sampler_name: "res_multistep" });
    node("12", "BasicScheduler", { model, scheduler: "simple", steps: turbo ? 4 : 20, denoise: 1 });
    node("13", "SamplerCustomAdvanced", { noise: ["9", 0], guider: ["10", 0], sampler: ["11", 0], sigmas: ["12", 0], latent_image: ["8", 1] });
    node("14", "VAEDecodeTiled", { samples: ["13", 0], vae: ["3", 0], tile_size: 512, overlap: 64, temporal_size: 64, temporal_overlap: 8 });
    node("15", "VAEDecodeAudio", { samples: ["13", 0], vae: ["4", 0] });
    node("16", "CreateVideo", { images: ["14", 0], audio: ["15", 0], fps: 24 });
    node("output", "SaveVideo", { video: ["16", 0], filename_prefix: "shortDramaFactory/h3", format: "auto", codec: "auto" });
  } else if (id.startsWith("qwen")) {
    node("1", "UNETLoader", { unet_name: models.diffusion, weight_dtype: "default" });
    node("2", "CLIPLoader", { clip_name: models.encoder, type: "qwen_image", device: "default" });
    node("3", "TextEncodeQwenImage21", { clip: ["2", 0], prompt: "{{prompt}}", negative_prompt: "", resolution: 1024 });
    node("4", "VAELoader", { vae_name: models.vae });
    if (id === "qwenTurboEdit") {
      node("5", "LoadImage", { image: "{{image0}}" });
      Object.assign(graph["3"]!.inputs, { vae: ["4", 0], "images.image_1": ["5", 0] });
    } else node("5", "EmptyLatentImage", { width: "{{width}}", height: "{{height}}", batch_size: 1 });
    node("6", "ManualSigmas", { sigmas: "1.0, 0.978453, 0.95418, 0.926626, 0.89508, 0.845148, 0.704534, 0.414568, 0" });
    node("7", "KSamplerSelect", { sampler_name: "euler" });
    node("8", "RandomNoise", { noise_seed: "{{seed}}" });
    node("9", "BasicGuider", { model: ["1", 0], conditioning: ["3", 0] });
    node("10", "SamplerCustomAdvanced", { noise: ["8", 0], guider: ["9", 0], sampler: ["7", 0], sigmas: ["6", 0], latent_image: id === "qwenTurboEdit" ? ["3", 2] : ["5", 0] });
    node("11", "VAEDecode", { samples: ["10", 0], vae: ["4", 0] });
    node("output", "SaveImage", { images: ["11", 0], filename_prefix: "shortDramaFactory/qwen" });
  } else {
    const flux = id.startsWith("fluxSchnell");
    const edit = id.endsWith("Edit");
    node("1", "CheckpointLoaderSimple", { ckpt_name: models.checkpoint });
    node("2", "CLIPTextEncode", { clip: ["1", 1], text: "{{prompt}}" });
    node("3", "CLIPTextEncode", { clip: ["1", 1], text: "" });
    if (edit) {
      node("7", "LoadImage", { image: "{{image0}}" });
      node("8", "ImageScale", { image: ["7", 0], upscale_method: "lanczos", width: "{{width}}", height: "{{height}}", crop: "center" });
      node("4", "VAEEncode", { pixels: ["8", 0], vae: ["1", 2] });
    } else node("4", flux ? "EmptySD3LatentImage" : "EmptyLatentImage", { width: "{{width}}", height: "{{height}}", batch_size: 1 });
    node("5", "KSampler", { model: ["1", 0], positive: ["2", 0], negative: ["3", 0], latent_image: ["4", 0], seed: "{{seed}}", steps: flux ? 4 : 20, cfg: flux ? 1 : 7, sampler_name: "euler", scheduler: flux ? "simple" : "normal", denoise: edit ? "{{denoise}}" : 1 });
    node("6", "VAEDecode", { samples: ["5", 0], vae: ["1", 2] });
    node("output", "SaveImage", { images: ["6", 0], filename_prefix: `shortDramaFactory/${id}` });
  }
  return graph;
}

function presetModelId(preset: Preset) {
  return preset.mediaType === "video" ? "comfyVideo" : `comfy${preset.id[0]!.toUpperCase()}${preset.id.slice(1)}`;
}

export async function catalog(url: string, mediaType: "image" | "video") {
  const info = await objectInfo(url);
  return presets.filter(preset => preset.mediaType === mediaType).map(preset => ({
    ...preset, modelId: presetModelId(preset), inputMode: preset.id.endsWith("Edit") || preset.id.endsWith("Image") ? "image" : "text",
    fields: preset.fields.map(field => ({ key: field.key, label: field.label, node: field.node, input: field.input, options: choices(info, field) })),
    missingNodes: [...new Set(Object.values(graphFor(preset.id, {})).map(node => node.class_type))].filter(name => !info[name]),
  }));
}

export async function build(body: z.infer<typeof buildSchema>) {
  const preset = presets.find(item => item.id === body.preset && item.mediaType === body.mediaType);
  if (!preset) throw Object.assign(new Error("请选择对应类型的内置工作流"), { status: 400 });
  const info = await objectInfo(body.url);
  const workflow = graphFor(preset.id, body.models);
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
    : { id: presetModelId(preset), label: preset.label, type: "image", mode: imageEdit ? ["singleImage"] : ["text"], imageSizes: preset.id.startsWith("sd") ? ["512x512", "768x768", "1024x1024"] : ["1024x1024"], imageRatios: ["1:1", "16:9", "9:16", "4:3", "3:4"],
      ...(["sdEdit", "fluxSchnellEdit"].includes(preset.id) ? { rules: [{ type: "inputNumber", field: "denoise", title: "重绘强度（越高变化越大）", value: 0.55, props: { min: 0.05, max: 1, step: 0.05, precision: 2 } }] } : {}) };
  return { workflow, outputNode: "output", model, label: preset.label, independent, inputMode: imageEdit || preset.id.endsWith("Image") ? "image" : "text" };
}
