import type { Request, Response } from "express";
import { Readable } from "node:stream";
import { pipeline } from "node:stream/promises";
import { localModelsConfig } from "@/utils/localModels";
import { assertAppRequest, getAppOrigin } from "@/utils/mcp/control";
import { isLocalHostRequest } from "@/utils/workspace";

export async function proxyComfy(req: Request, res: Response) {
  if (!isLocalHostRequest(req)) throw Object.assign(new Error("ComfyUI 连接仅供本机工作台使用"), { status: 403 });
  const parts = req.params.path;
  const path = Array.isArray(parts) ? parts.join("/") : String(parts ?? "");
  const readAllowed = /^(?:system_stats|queue|object_info(?:\/[^/]+)?|history\/[a-zA-Z0-9-]+|view)$/;
  const writeAllowed = /^(?:prompt|upload\/image|interrupt)$/;
  if (!(req.method === "GET" ? readAllowed : writeAllowed).test(path)) throw Object.assign(new Error("不支持的 ComfyUI 操作"), { status: 404 });
  if (path !== "view") assertAppRequest(req);
  else if (req.get("origin") || req.get("referer")) getAppOrigin(req);
  else if (req.get("sec-fetch-site")) throw Object.assign(new Error("媒体访问来源无效"), { status: 403 });
  const config = localModelsConfig();
  const url = new URL(`/${path}`, config.comfyUrl);
  if (path === "view") {
    for (const key of ["filename", "subfolder", "type", "format", "preview", "channel"]) {
      const value = req.query[key];
      if (typeof value === "string") url.searchParams.set(key, value);
    }
  }
  const controller = new AbortController();
  const close = () => { if (!res.writableEnded) controller.abort(); };
  res.on("close", close);
  try {
    if (path === "interrupt") {
      const queue = await fetch(new URL("/queue", config.comfyUrl), { signal: AbortSignal.timeout(5000), redirect: "error" });
      if (!queue.ok) throw new Error("无法核对正在运行的任务，未中断");
      const state = await queue.json() as { queue_running?: unknown[][] };
      if (!req.body?.prompt_id || !state.queue_running?.some(item => item[1] === req.body.prompt_id)) {
        throw Object.assign(new Error("当前运行的不是此节点任务，未中断其他任务"), { status: 409 });
      }
    }
    const headers: Record<string, string> = {};
    if (req.method === "POST") headers["Content-Type"] = req.get("content-type") || "application/json";
    if (req.get("range")) headers.Range = req.get("range")!;
    const response = await fetch(url, { method: req.method, headers, redirect: "error",
      signal: AbortSignal.any([controller.signal, AbortSignal.timeout(120_000)]),
      body: req.method === "GET" ? undefined : Buffer.isBuffer(req.body) ? new Uint8Array(req.body).buffer : JSON.stringify(req.body ?? {}),
    });
    res.status(response.status).set("Cache-Control", "no-store");
    for (const key of ["content-type", "content-length", "content-range", "accept-ranges"]) {
      const value = response.headers.get(key);
      if (value) res.set(key, value);
    }
    if (response.body) await pipeline(Readable.fromWeb(response.body as Parameters<typeof Readable.fromWeb>[0]), res);
    else res.end();
  } finally { res.off("close", close); }
}
