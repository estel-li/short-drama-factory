import type { Request } from "express";
import { z } from "zod";
import { isLocalWorkspaceRequest } from "@/utils/workspace";
import { connection, requestJson, verifyInstance } from "@/utils/h3Factory";

const path = z.string().trim().min(1).max(4096);
const comfyUrl = z.url().refine(value => {
  const url = new URL(value);
  return url.protocol === "http:" && ["localhost", "127.0.0.1"].includes(url.hostname)
    && !url.username && !url.password && !url.search && !url.hash && url.pathname === "/";
}, "本地启动请使用 http://127.0.0.1:端口");
export const pathsSchema = z.object({ comfy_dir: path, python: z.string().trim().max(4096).default("") }).strict();
export const configSchema = pathsSchema.extend({ python: path, comfy_url: comfyUrl });
export const installSchema = z.object({
  mode: z.literal("fresh"), manifest: z.string().regex(/^[a-zA-Z0-9_-]+$/).max(100),
  install_dir: path, models_dir: path, comfy_url: comfyUrl,
  model_search_dirs: z.array(path).max(20).default([]),
}).strict();

export function authorize(req: Request) {
  if (!isLocalWorkspaceRequest(req) || req.get("forwarded") || req.get("x-forwarded-for")) {
    throw Object.assign(new Error("仅允许本机工作台管理 ComfyUI 环境"), { status: 403 });
  }
}

export async function request(req: Request, path: string, method = "GET", body?: unknown) {
  authorize(req);
  const config = connection();
  await verifyInstance(config);
  return requestJson(config, path, method, body);
}
