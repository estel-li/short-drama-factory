import { createHash } from "node:crypto";
import { mkdir, realpath, stat } from "@toonflow/file";
import { lockWorkspaceFiles, resolveWorkspacePath, writeWorkspaceFile } from "@/utils/workspace/files";
import { downloadPublicFile, remoteAddress } from "@/utils/workspace/download";

const maxImageSize = 20 * 1024 * 1024;
const imageFormats = { "image/png": "png", "image/jpeg": "jpg", "image/webp": "webp", "image/gif": "gif", "image/avif": "avif", "image/bmp": "bmp" };
const inflight = new Map<string, Promise<{ path: string; mimeType: string }>>();
function invalid(message: string, status = 400): never {
  throw Object.assign(new Error(message), { status });
}

function imageMimeType(bytes: Buffer): keyof typeof imageFormats {
  if (bytes.length >= 24 && bytes.subarray(0, 8).equals(Buffer.from([137, 80, 78, 71, 13, 10, 26, 10])) && bytes.toString("ascii", 12, 16) === "IHDR") return "image/png";
  if (bytes.length >= 4 && bytes[0] === 255 && bytes[1] === 216 && bytes[2] === 255) return "image/jpeg";
  if (bytes.length >= 13 && /^GIF8[79]a/.test(bytes.toString("ascii", 0, 6))) return "image/gif";
  if (bytes.length >= 16 && bytes.toString("ascii", 0, 4) === "RIFF" && bytes.toString("ascii", 8, 12) === "WEBP" && /^VP8[ LX]$/.test(bytes.toString("ascii", 12, 16))) return "image/webp";
  if (bytes.length >= 26 && bytes.toString("ascii", 0, 2) === "BM") return "image/bmp";
  if (bytes.length >= 16 && bytes.toString("ascii", 4, 8) === "ftyp") {
    const end = bytes.readUInt32BE(0);
    if (end >= 16 && end <= bytes.length) {
      for (let offset = 8; offset + 4 <= end; offset += 4) if (["avif", "avis"].includes(bytes.toString("ascii", offset, offset + 4))) return "image/avif";
    }
  }
  if (/<svg(?:\s|>)/i.test(bytes.toString("utf8", 0, 512))) invalid("暂不支持网络 SVG 图片，请使用 PNG、JPEG、WebP、GIF、AVIF 或 BMP");
  return invalid("下载内容不是支持的图片，可能返回了网页或登录页面");
}

export async function importImage(cwd: string, value: string) {
  const directory = await realpath(cwd);
  const url = remoteAddress(value);
  const key = JSON.stringify([directory, url.href]);
  const existing = inflight.get(key);
  if (existing) return existing;
  const pending = (async () => {
    const hash = createHash("sha256").update(url.href).digest("hex");
    const outputDirectory = "assets/chatImages";
    for (const [mimeType, extension] of Object.entries(imageFormats)) {
      const path = `${outputDirectory}/${hash}.${extension}`;
      const cached = await resolveWorkspacePath(directory, path, true);
      const info = await stat(cached.path).catch((error: NodeJS.ErrnoException) => { if (error.code === "ENOENT") return null; throw error; });
      if (info?.isFile() && info.size > 0 && info.size <= maxImageSize) return { path, mimeType };
    }
    const signal = AbortSignal.timeout(30000);
    const bytes = await downloadPublicFile(url.href, {
      signal, maxBytes: maxImageSize, label: "聊天图片", accept: "image/avif,image/webp,image/png,image/jpeg,image/gif,image/bmp",
    }).catch(error => {
      if (signal.aborted) invalid("图片下载超时（30 秒），请检查网络后重试", 504);
      if (error instanceof Error && "status" in error) throw error;
      throw Object.assign(new Error("图片下载连接失败，请检查图片地址、网络或 HTTPS 证书", { cause: error }), { status: 502 });
    });
    const mimeType = imageMimeType(bytes);
    const path = `${outputDirectory}/${hash}.${imageFormats[mimeType]}`;
    const output = await resolveWorkspacePath(directory, outputDirectory, true);
    const candidate = await resolveWorkspacePath(directory, path, true);
    const release = lockWorkspaceFiles([candidate.path]);
    try {
      await mkdir(output.path, { recursive: true });
      const target = await resolveWorkspacePath(directory, path);
      await writeWorkspaceFile(target.path, bytes, true);
    } finally { release(); }
    return { path, mimeType };
  })();
  inflight.set(key, pending);
  try { return await pending; }
  finally { if (inflight.get(key) === pending) inflight.delete(key); }
}
