import { lstat, open, readdir, realpath } from "@toonflow/file";
import { Router } from "express";
import { zip } from "fflate";
import { basename, join } from "node:path";
import { z } from "zod";
import u from "@/utils";
import { validateFields } from "@/lib/middleware";

const router = Router();
// ACT: 当前在内存中打包，与桌面和移动端保存入口统一限制为 1 GB；更大项目需改为流式打包和保存。
const maxBytes = 1024 * 1024 * 1024;

export default router.get("/", validateFields({ directory: z.string().min(1).max(4096) }, "query"), async (req, res) => {
  const directory = await u.workspace.resolveWorkspace(req, req.query.directory as string);
  const files: Record<string, Uint8Array> = Object.create(null);
  let entries = 0;
  let totalBytes = 0;

  async function collectFiles(path: string, prefix = "") {
    for (const child of await readdir(path, { withFileTypes: true })) {
      if (res.destroyed) throw new Error("项目导出已取消");
      if (++entries > 10000) throw Object.assign(new Error("项目导出最多包含 10000 个文件和目录"), { status: 413 });
      if (/[\\:]/.test(child.name)) throw Object.assign(new Error("项目包含无法安全导出为 ZIP 的文件名"), { status: 400 });
      const filePath = join(path, child.name);
      const archivePath = prefix ? `${prefix}/${child.name}` : child.name;
      const info = await lstat(filePath);
      if (info.isSymbolicLink() || (!info.isFile() && !info.isDirectory())) {
        throw Object.assign(new Error("项目不能包含符号链接或特殊文件"), { status: 400 });
      }
      const actualPath = await realpath(filePath);
      if (!u.workspaceFile.isWithin(directory, actualPath)) throw Object.assign(new Error("项目文件超出工作区范围"), { status: 403 });
      if (info.isDirectory()) {
        files[`${archivePath}/`] = new Uint8Array();
        await collectFiles(actualPath, archivePath);
        continue;
      }
      if (totalBytes + info.size > maxBytes) throw Object.assign(new Error("项目文件总大小不能超过 1 GB"), { status: 413 });
      const file = await open(actualPath, "r");
      try {
        const current = await file.stat();
        if (!current.isFile() || current.dev !== info.dev || current.ino !== info.ino) {
          throw Object.assign(new Error("项目文件在导出期间发生变化，请重试"), { status: 409 });
        }
        const chunks: Buffer[] = [];
        for await (const chunk of file.createReadStream({ autoClose: false, highWaterMark: 64 * 1024 })) {
          if (res.destroyed) throw new Error("项目导出已取消");
          totalBytes += chunk.length;
          if (totalBytes > maxBytes) throw Object.assign(new Error("项目文件总大小不能超过 1 GB"), { status: 413 });
          chunks.push(chunk);
        }
        files[archivePath] = Buffer.concat(chunks);
      } finally { await file.close(); }
    }
  }

  await collectFiles(directory);
  if (res.destroyed) return;
  const bytes = await new Promise<Uint8Array>((resolve, reject) => {
    let cancel: (() => void) | undefined;
    function handleClose() {
      cancel?.();
      reject(new Error("项目导出已取消"));
    }
    res.once("close", handleClose);
    cancel = zip(files, { level: 1 }, (error, data) => {
      res.off("close", handleClose);
      if (error) reject(error);
      else resolve(data);
    });
  });
  if (bytes.byteLength > maxBytes) throw Object.assign(new Error("项目 ZIP 文件不能超过 1 GB"), { status: 413 });
  res.set("Cache-Control", "no-store").attachment(`${basename(directory) || "项目"}.zip`).send(Buffer.from(bytes));
});
