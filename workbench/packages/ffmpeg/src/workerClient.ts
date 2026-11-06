import { AsyncResource } from "node:async_hooks";
import { Worker } from "node:worker_threads";
import { serializeError } from "./remote";
import type { BrowserFfmpegRequest, FfmpegRemoteEvent } from "./browserTypes";

type WorkerError = ReturnType<typeof serializeError>;
type WorkerOperation = { type: "version"; path: string; name: string }
  | { type: "execute"; cwd: string; paths: { ffmpeg: string; ffprobe: string }; request: BrowserFfmpegRequest };
export type FfmpegWorkerRequest = { id: string } & (WorkerOperation | { type: "cancel"; reason: WorkerError });
export type FfmpegWorkerResponse = { id: string } & (
  { type: "event"; event: FfmpegRemoteEvent } | { type: "done"; version?: string } | { type: "error"; error: WorkerError }
);
type PendingRequest = {
  emit: (event: FfmpegRemoteEvent) => void;
  finish: (error?: unknown, version?: string) => void;
};

let worker: Worker | undefined;
const pending = new Map<string, PendingRequest>();

function getWorker() {
  if (worker) return worker;
  // ACT: 源码直接运行 TS；server 和桌面构建将独立 JS 入口放在主 bundle 同目录。
  const path = new URL(import.meta.url.endsWith(".ts") ? "./ffmpegWorker.ts" : "./ffmpegWorker.js", import.meta.url);
  const current = worker = new Worker(path);
  current.on("message", (message: FfmpegWorkerResponse) => {
    const task = pending.get(message.id);
    if (!task) return;
    if (message.type === "event") task.emit(message.event);
    else if (message.type === "error") task.finish(Object.assign(new Error(message.error.message), message.error));
    else task.finish(undefined, message.version);
  });
  const fail = (error: Error) => {
    if (worker !== current) return;
    worker = undefined;
    for (const task of [...pending.values()]) task.finish(error);
  };
  current.on("error", fail);
  current.on("exit", code => fail(new Error(`FFmpeg 工作线程已退出（${code}）`)));
  current.unref();
  return current;
}

function send(operation: WorkerOperation, emit: (event: FfmpegRemoteEvent) => void, signal?: AbortSignal) {
  signal?.throwIfAborted();
  const current = getWorker();
  const id = crypto.randomUUID();
  const onEvent = AsyncResource.bind(emit, "ffmpegRequest");
  return new Promise<string | undefined>((resolve, reject) => {
    let callbackError: Error | undefined;
    const cancel = (reason: unknown) => current.postMessage({ id, type: "cancel", reason: serializeError(reason) } satisfies FfmpegWorkerRequest);
    const abort = () => cancel(signal?.reason);
    const finish = (error?: unknown, version?: string) => {
      if (!pending.delete(id)) return;
      signal?.removeEventListener("abort", abort);
      if (!pending.size) current.unref();
      if (error !== undefined || callbackError !== undefined) reject(error ?? callbackError);
      else resolve(version);
    };
    pending.set(id, {
      finish,
      emit: event => {
        if (callbackError !== undefined) return;
        try { onEvent(event); }
        catch (error) {
          callbackError = error instanceof Error ? error : new Error(String(error));
          cancel(error);
        }
      },
    });
    signal?.addEventListener("abort", abort, { once: true });
    current.ref();
    try { current.postMessage({ ...operation, id } satisfies FfmpegWorkerRequest); }
    catch (error) { finish(error); }
  });
}

export async function readVersionInWorker(path: string, name: string, signal?: AbortSignal): Promise<string> {
  const version = await send({ type: "version", path, name }, () => {}, signal);
  signal?.throwIfAborted();
  return version!;
}

export async function executeFfmpegInWorker(
  cwd: string,
  paths: { ffmpeg: string; ffprobe: string },
  request: BrowserFfmpegRequest,
  emit: (event: FfmpegRemoteEvent) => void,
  signal: AbortSignal,
): Promise<void> {
  await send({ type: "execute", cwd, paths, request }, emit, signal);
}
