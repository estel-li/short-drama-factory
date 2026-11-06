import { Router } from "express";
import u from "@/utils";
import { validateFields } from "@/lib/middleware";
import { success } from "@/lib/responseFormat";
import { comfyAddress } from "@/utils/localModels";
import { z } from "zod";

// ComfyUI 的目录描述加载方式，不提供统一的图片／视频用途字段。
// 仅识别明确的模型家族；其余分体模型保留为待确认，不当作图片候选。
function modelUsage(category: string, name: string) {
  const fileName = name.replaceAll("\\", "/").split("/").at(-1)!;
  if (/minimax[_-]?h3|^taeh3\./i.test(fileName)) return "video";
  if (/^(?:flux|qwen[_-]?image|z[_-]?image|sdxl|stable[_-]?diffusion)(?:[._\s-]|\d)/i.test(fileName)) return "image";
  return category === "checkpoints" ? "image" : "unknown";
}

export default Router().post("/", validateFields({ url: comfyAddress, mediaType: z.enum(["image", "video"]).optional() }), async (req, res) => {
  u.mcpControl.assertAppRequest(req);
  const base = comfyAddress.parse(req.body.url);
  const read = async (path: string) => {
    const response = await fetch(new URL(path, base), { signal: AbortSignal.timeout(8000), redirect: "error" });
    if (!response.ok) throw Object.assign(new Error(`ComfyUI 连接失败（HTTP ${response.status}）`), { status: 502 });
    return response.json() as Promise<Record<string, any>>;
  };
  const state = await read("/system_stats");
  if (!state.system || !Array.isArray(state.devices)) throw Object.assign(new Error("不是有效的 ComfyUI 服务"), { status: 502 });
  // 读取各加载器实际可选的模型；H3、Flux、Qwen 等分体权重不属于 Checkpoint。
  const loaders = [
    { id: "checkpoints", node: "CheckpointLoaderSimple", field: "ckpt_name" },
    { id: "diffusionModels", node: "UNETLoader", field: "unet_name" },
    { id: "textEncoders", node: "CLIPLoader", field: "clip_name" },
    { id: "vae", node: "VAELoader", field: "vae_name" },
    { id: "loras", node: "LoraLoaderModelOnly", field: "lora_name" },
  ];
  const allGroups = await Promise.all(loaders.map(async ({ id, node, field }) => {
    const info = await read(`/object_info/${node}`);
    const values = info[node]?.input?.required?.[field]?.[0];
    const files = Array.isArray(values) ? [...new Set(values.filter((name: unknown): name is string => typeof name === "string"))] : [];
    return { id, files };
  }));
  const mediaType = req.body.mediaType as "image" | "video" | undefined;
  const modelGroups = mediaType ? allGroups.map(group => ({ ...group, files: group.files.filter(name => modelUsage(group.id, name) === mediaType) })) : allGroups;
  const unclassifiedGroups = mediaType ? allGroups.map(group => ({ ...group, files: group.files.filter(name => modelUsage(group.id, name) === "unknown") })).filter(group => group.files.length) : [];
  const excludedModelCount = mediaType ? allGroups.filter(group => ["checkpoints", "diffusionModels"].includes(group.id))
    .reduce((count, group) => count + group.files.filter(name => modelUsage(group.id, name) === (mediaType === "image" ? "video" : "image")).length, 0) : 0;
  const checkpoints = modelGroups.find(group => group.id === "checkpoints")!.files;
  res.json(success({ connected: true, checkpoints, modelGroups, unclassifiedGroups, excludedModelCount }));
});
