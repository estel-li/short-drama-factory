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
}).strict();
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
