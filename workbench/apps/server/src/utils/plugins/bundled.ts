import { cp, lstat, mkdir, readdir, readFile, writeAtomic } from "@toonflow/file";
import { resolve } from "node:path";

export default async function installBundledPlugins(dataDirectory: string, sourceDirectory: string) {
  const names: Record<string, Set<string>> = {};
  for (const [type, folder] of Object.entries({ node: "nodes", tool: "tools", ext: "ext", skill: "skills" })) {
    names[type] = new Set();
    const source = resolve(sourceDirectory, folder);
    const target = resolve(dataDirectory, folder);
    const entries = await readdir(source, { withFileTypes: true }).catch((error: NodeJS.ErrnoException) => {
      if (error.code === "ENOENT") return [];
      throw error;
    });
    await mkdir(target, { recursive: true });
    if (!(await lstat(target)).isDirectory() || (await lstat(target)).isSymbolicLink()) throw new Error("插件目录无效");
    for (const entry of entries) {
      if (type === "skill" ? !entry.isDirectory() : !entry.isFile()) continue;
      const name = type === "skill" ? entry.name : entry.name.replace(/\.(?:tool|umd)\.js$/, "");
      names[type]!.add(name);
      const path = resolve(target, entry.name);
      // 补齐新内置包，保留已经安装的版本与用户编辑。
      const existing = await lstat(path).catch((error: NodeJS.ErrnoException) => { if (error.code !== "ENOENT") throw error; });
      if (existing) continue;
      if (entry.isDirectory()) await cp(resolve(source, entry.name), path, { recursive: true, force: false, errorOnExist: true });
      else await writeAtomic(path, await readFile(resolve(source, entry.name)), { exclusive: true });
    }
  }
  return names;
}
