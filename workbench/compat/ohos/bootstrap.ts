import { Readable } from "node:stream";
import { format } from "node:util";
import { pathToFileURL } from "node:url";

// ACT: Node 24.2 的这些懒加载全局会提前编译 WASM；先移除访问器，再复用已安装 Undici 的 Web API。
const webGlobals = ["fetch", "Headers", "Response", "Request", "FormData", "WebSocket", "CloseEvent", "MessageEvent", "EventSource", "ErrorEvent"] as const;
for (const name of webGlobals) Reflect.deleteProperty(globalThis, name);
const webApi = require("toonflow:webApi") as typeof globalThis;
for (const name of webGlobals) if (name !== "fetch") Reflect.set(globalThis, name, webApi[name]);
// Node 24.2 为 HTTP 的 ESM 命名导出读取全部属性，连带触发这三个旧 Undici 访问器。
const http = require("node:http");
for (const name of ["WebSocket", "CloseEvent", "MessageEvent"] as const) {
  Object.defineProperty(http, name, { value: webApi[name], configurable: true, enumerable: true, writable: true });
}
const { getRequestState } = require("toonflow:webRequest") as {
  getRequestState(request: Request): { body: { source: unknown } | null };
};
const { getResponseState } = require("toonflow:webResponse") as {
  getResponseState(response: Response): { urlList: URL[]; type: string };
};

const native = (process as NodeJS.Process & {
  _linkedBinding(name: string): { log(message: string): void };
})._linkedBinding("toonflowNative");
const nodeFetch = (require("toonflow:nodeFetch") as {
  default(url: string, options: { method: string; headers: Record<string, string>; body?: Readable | Blob; signal: AbortSignal; redirect: Request["redirect"] }):
    Promise<{ body: Readable; status: number; statusText: string; headers: { raw(): Record<string, string[]> }; url: string; redirected: boolean }>;
}).default;

// ACT: V8 jitless 不提供 WASM；Node 内置 fetch 的 HTTP 解析器依赖 WASM。
// 复用已安装的 node-fetch 传输，响应保持原生 Web Stream / Response 语义。
Object.assign(globalThis, { fetch: async (input: string | URL | Request, options?: RequestInit) => {
  const init = {
    ...options,
    ...(options?.body instanceof ReadableStream ? { duplex: "half" as const } : {}),
  };
  const request = input instanceof Request ? new Request(input, init) : new Request(String(input), init);
  // 保留可重放请求体，307/308 不能把字符串、Blob 和表单误判为一次性流。
  const body = !request.body ? undefined : getRequestState(request).body?.source != null ? await request.blob()
    : Readable.fromWeb(request.body as import("node:stream/web").ReadableStream);
  const result = await nodeFetch(request.url, {
    method: request.method,
    headers: Object.fromEntries(request.headers),
    body,
    signal: request.signal,
    redirect: request.redirect,
  });
  const response = new Response([101, 204, 205, 304].includes(result.status) || request.method === "HEAD" ? null
    : Readable.toWeb(result.body as unknown as Readable) as ReadableStream, {
    status: result.status,
    statusText: result.statusText,
    headers: Object.entries(result.headers.raw()).flatMap(([name, values]) => values.map(value => [name, value])),
  });
  // 使用同一 Undici 版本的状态接口，使 clone() 也保留 URL 和重定向信息。
  const state = getResponseState(response);
  state.urlList = result.url ? [...(result.redirected ? [new URL(request.url)] : []), new URL(result.url)] : [];
  state.type = "basic";
  return response;
} });

for (const name of ["log", "info", "warn", "error", "debug"] as const) {
  console[name] = (...values: unknown[]) => native.log(format(...values));
}

import(pathToFileURL(process.argv[2]!).href).catch(error => {
  console.error(error);
  process.exit(1);
});
