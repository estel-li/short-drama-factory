import { randomUUID, createHash } from "node:crypto";
import { basename, dirname, extname, isAbsolute, join, relative, sep } from "node:path";
import { lstat, mkdir, opendir, realpath, stat, symlink } from "@toonflow/file";
import { z } from "zod";

export const categories = ["checkpoints", "diffusion_models", "text_encoders", "vae", "loras", "controlnet", "clip_vision", "upscale_models", "embeddings", "model_patches", "latent_upscale_models"] as const;
export const startSchema = z.object({ directories: z.array(z.string().trim().min(1).max(4096)).min(1).max(20) }).strict();
export const attachSchema = z.object({ searchId: z.uuid(), items: z.array(z.object({ id: z.string().min(1), category: z.enum(categories) }).strict()).min(1).max(500) }).strict();
type Candidate = { id: string; name: string; path: string; size: number; modified: number; category: string };
type Search = { id: string; status: "running" | "done" | "stopped" | "limited" | "error"; directories: string[]; scanned: number; skipped: number; current: string; message: string; items: Candidate[] };
let current: Search | undefined;
const extensions = new Set([".safetensors", ".ckpt", ".gguf", ".pt", ".pth", ".bin"]);
const skippedDirectories = new Set(["$recycle.bin", "system volume information", "windows", "node_modules", ".git", ".venv", "__pycache__"]);

function within(root: string, path: string) {
  const offset = relative(root, path);
  return !isAbsolute(offset) && offset !== ".." && !offset.startsWith(`..${sep}`);
}

function categoryFor(path: string) {
  const parts = path.toLowerCase().split(/[\\/]/);
  for (const part of parts.slice(0, -1).reverse()) {
    if (categories.includes(part as typeof categories[number])) return part;
    if (part === "unet") return "diffusion_models";
    if (part === "clip") return "text_encoders";
  }
  const name = basename(path).toLowerCase();
  if (/lora/.test(name)) return "loras";
  if (/vae|^ae\./.test(name)) return "vae";
  if (/qwen3vl|t5xxl|^clip_[lg]\./.test(name)) return "text_encoders";
  if (/minimax[_-]?h3|qwen[_-]?image|z[_-]?image/.test(name)) return "diffusion_models";
  return "unknown";
}

export function get(id?: string) {
  if (id && current?.id !== id) throw Object.assign(new Error("搜索记录已过期，请重新搜索"), { status: 404 });
  return current ?? null;
}

export async function start(directories: string[]) {
  if (current?.status === "running") throw Object.assign(new Error("已有搜索正在进行，请先停止"), { status: 409 });
  const roots: string[] = [];
  for (let value of directories) {
    if (/^[a-z]:$/i.test(value)) value += "\\";
    if (!isAbsolute(value) || /^[/\\]{2}/.test(value)) throw Object.assign(new Error("请填写本机目录的绝对路径或盘符，例如 E:\\"), { status: 400 });
    const actual = await realpath(value).catch(() => { throw Object.assign(new Error(`目录不存在或不可读取：${value}`), { status: 400 }); });
    // Bun 在 Windows 对盘符根目录的 realpath 可能返回 E:，必须保留根分隔符，不能退化为盘符相对路径。
    const path = /^[a-z]:$/i.test(actual) ? `${actual}\\` : actual;
    if (!(await stat(path)).isDirectory()) throw Object.assign(new Error(`不是文件夹：${value}`), { status: 400 });
    if (!roots.some(root => within(root, path))) roots.push(path);
  }
  // 路径校验有 await，提交前再次检查，避免并发搜索互相替换。
  if (get()?.status === "running") throw Object.assign(new Error("已有搜索正在进行"), { status: 409 });
  const state: Search = { id: randomUUID(), status: "running", directories: roots, scanned: 0, skipped: 0, current: "", message: "", items: [] };
  current = state;
  void scan(state).catch(error => { state.status = "error"; state.message = error instanceof Error ? error.message : "搜索失败"; });
  return state;
}

async function scan(state: Search) {
  const pending = [...state.directories];
  const visited = new Set<string>();
  const started = Date.now();
  let entries = 0;
  while (pending.length && state.status === "running") {
    // ACT: 单次本机扫描上限 5 分钟、100 万条目、1 万候选；达到上限保留结果并提示缩小目录。
    if (Date.now() - started > 300000 || entries >= 1000000 || state.items.length >= 10000) {
      state.status = "limited"; state.message = "已达到扫描上限，以下为部分结果；请缩小目录继续搜索。"; break;
    }
    const path = pending.pop()!;
    const key = process.platform === "win32" ? path.toLowerCase() : path;
    if (visited.has(key)) continue;
    visited.add(key);
    state.current = path;
    state.scanned++;
    try {
      if ((await lstat(path)).isSymbolicLink()) { state.skipped++; continue; }
      const directory = await opendir(path);
      for await (const entry of directory) {
        if (state.status !== "running") break;
        if (entries++ >= 1000000 || state.items.length >= 10000 || Date.now() - started > 300000) {
          state.status = "limited"; state.message = "已达到扫描上限，以下为部分结果；请缩小目录继续搜索。"; break;
        }
        if (entry.isSymbolicLink()) { state.skipped++; continue; }
        const child = join(path, entry.name);
        if (entry.isDirectory()) {
          if (skippedDirectories.has(entry.name.toLowerCase())) state.skipped++;
          else pending.push(child);
        } else if (entry.isFile() && extensions.has(extname(entry.name).toLowerCase())) {
          try {
            const info = await stat(child);
            if (!info.size) continue;
            state.items.push({ id: String(state.items.length), name: entry.name, path: child, size: info.size, modified: info.mtimeMs, category: categoryFor(child) });
          } catch { state.skipped++; }
        }
      }
    } catch { state.skipped++; }
  }
  if (state.status === "running") state.status = "done";
  state.current = "";
}

export function stop(id: string) {
  const state = get(id)!;
  if (state.status === "running") { state.status = "stopped"; state.message = "搜索已停止，已找到的结果保留。"; }
  return state;
}

export async function attach(body: z.infer<typeof attachSchema>, comfyDirectory: string) {
  const state = get(body.searchId)!;
  const comfyRoot = await realpath(comfyDirectory);
  if (!(await stat(join(comfyRoot, "main.py"))).isFile()) throw new Error("保存的 ComfyUI 目录无效");
  const results: { path: string; category: string; status: string; target?: string; message?: string }[] = [];
  for (const selected of body.items) {
    const item = state.items.find(item => item.id === selected.id);
    if (!item) throw Object.assign(new Error("模型不在本次搜索结果中"), { status: 400 });
    try {
      const info = await lstat(item.path);
      if (!info.isFile() || info.isSymbolicLink() || info.size !== item.size || info.mtimeMs !== item.modified) throw new Error("文件已变化，请重新搜索");
      const source = await realpath(dirname(item.path));
      if (!state.directories.some(root => within(root, source))) throw new Error("模型已离开搜索目录");
      const modelRoot = join(comfyRoot, "models", selected.category);
      await mkdir(modelRoot, { recursive: true });
      const actualRoot = await realpath(modelRoot);
      if (within(actualRoot, item.path)) {
        results.push({ path: item.path, category: selected.category, status: "existing", target: relative(actualRoot, item.path) }); continue;
      }
      const folder = join(actualRoot, "importedModels");
      await mkdir(folder, { recursive: true });
      if ((await lstat(folder)).isSymbolicLink()) throw new Error("接入目录被替换为链接，已停止写入");
      const target = join(folder, createHash("sha256").update(process.platform === "win32" ? source.toLowerCase() : source).digest("hex").slice(0, 16));
      if (within(source, target)) throw new Error("来源目录包含 ComfyUI 模型目录，会形成循环；请把模型放入独立文件夹");
      try { await symlink(source, target, process.platform === "win32" ? "junction" : "dir"); }
      catch (error) {
        if ((error as NodeJS.ErrnoException).code !== "EEXIST" || await realpath(target) !== source) throw error;
      }
      results.push({ path: item.path, category: selected.category, status: "linked", target: relative(actualRoot, join(target, item.name)) });
    } catch (error) {
      results.push({ path: item.path, category: selected.category, status: "error", message: error instanceof Error ? error.message : "接入失败" });
    }
  }
  return { results, message: "已通过目录链接复用模型。链接目录中的同类文件也可见；原文件需保持原位。请在图片／视频模型设置中重新读取模型。" };
}
