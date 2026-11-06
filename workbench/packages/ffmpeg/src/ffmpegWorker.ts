import { parentPort } from "node:worker_threads";
import { msg } from "@toonflow/i18n";
import { messageError } from "@toonflow/i18n/errors";
import { createFfmpeg } from "./runtime";
import { executeRemoteFfmpeg, serializeError } from "./remote";
import type { FfmpegWorkerRequest, FfmpegWorkerResponse } from "./workerClient";

if (!parentPort) throw new Error("FFmpeg 必须在工作线程中运行");
const port = parentPort;
const active = new Map<string, AbortController>();
port.on("close", () => {
  for (const controller of active.values()) controller.abort();
});

async function run(message: Exclude<FfmpegWorkerRequest, { type: "cancel" }>, signal: AbortSignal) {
  const send = (response: FfmpegWorkerResponse) => port.postMessage(response);
  if (message.type === "version") {
    const child = Bun.spawn([message.path, "-version"], {
      stdin: "ignore", stdout: "pipe", stderr: "ignore", windowsHide: true, timeout: 15000, signal,
      env: Object.fromEntries(Object.entries(process.env).filter(([key]) => key.toUpperCase() !== "FFREPORT")),
    });
    // 取消可能先关闭输出流；仍等子进程退出后，调用方才能替换或清理可执行文件。
    const [output, code] = await Promise.all([child.stdout.text(), child.exited]).finally(() => child.exited);
    signal.throwIfAborted();
    const version = output.split(/\r?\n/, 1)[0];
    if (code !== 0 || !version?.startsWith(`${message.name} version `)) {
      throw messageError(msg`${message.name} 无法运行，请检查平台兼容性或重新下载`);
    }
    send({ id: message.id, type: "done", version });
    return;
  }
  const factory = createFfmpeg(message.cwd);
  factory.setFfmpegPath(message.paths.ffmpeg);
  factory.setFfprobePath(message.paths.ffprobe);
  await executeRemoteFfmpeg(factory, message.request, event => send({ id: message.id, type: "event", event }), signal);
  send({ id: message.id, type: "done" });
}

port.on("message", (message: FfmpegWorkerRequest) => {
  if (message.type === "cancel") {
    active.get(message.id)?.abort(Object.assign(new Error(message.reason.message), message.reason));
    return;
  }
  const controller = new AbortController();
  active.set(message.id, controller);
  void run(message, controller.signal).catch(error => {
    port.postMessage({ id: message.id, type: "error", error: serializeError(error) } satisfies FfmpegWorkerResponse);
  }).finally(() => active.delete(message.id));
});
