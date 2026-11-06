import { readFile } from "@toonflow/file";
import { createRequire } from "node:module";
import { dirname, relative, resolve } from "node:path";
import type { BunPlugin } from "bun";

const root = resolve(import.meta.dirname, "../..");
const runtimePath = resolve(import.meta.dirname, "runtime.ts").replaceAll("\\", "/");
const serverRequire = createRequire(resolve(root, "apps/server/package.json"));
const dependencyRequire = createRequire(serverRequire.resolve("@babel/parser"));
const scaffoldRequire = createRequire(resolve(root, "packages/extScaffold/package.json"));
const dependencies = new Map(["@babel/parser", "@babel/traverse", "@babel/types", "semver", "mime-types", "which"]
  .map(name => [name, dependencyRequire.resolve(name).replaceAll("\\", "/")]));
dependencies.set("typescript", scaffoldRequire.resolve("typescript").replaceAll("\\", "/"));

const memberReplacements: Record<string, Record<string, string>> = {
  "apps/server/src/remoteConnection.ts": { "Bun.escapeHTML": "escapeHtml" },
  "apps/server/src/utils/desktop/index.ts": { "Bun.semver.order": "semverOrder", "Bun.sleep": "sleep" },
  "apps/server/src/routes/desktop/clipboard/write.ts": { "Bun.Image": "runtimeImage" },
  "apps/server/src/utils/media/provider.ts": { "new Bun.Transpiler": "createTranspiler", "Bun.Image": "runtimeImage", "Bun.hash": "hash" },
  "apps/server/src/utils/media/priceReference.ts": { "Bun.Image": "runtimeImage", "Bun.spawn": "spawnProcess" },
  "apps/server/src/utils/plugins/install.ts": { "new Bun.Transpiler": "createTranspiler", "Bun.semver.order": "semverOrder" },
  "apps/server/src/utils/plugins/tools.ts": { "new Bun.Transpiler": "createTranspiler" },
  "apps/server/src/utils/plugins/ext.ts": { "Bun.hash": "hash" },
  "apps/server/src/utils/plugins/initializeExt.ts": { "Bun.hash": "hash" },
  "apps/server/src/utils/teams/files.ts": { "new Bun.Transpiler": "createTranspiler" },
  "packages/ffmpeg/src/index.ts": { "Bun.which": "which" },
  "packages/ffmpeg/src/ffmpegWorker.ts": { "Bun.spawn": "spawnProcess" },
};
const specialFiles = new Set(["apps/mobile/src/server.ts", "apps/server/src/utils/mcp/resources.ts", "packages/file/src/index.ts"]);

function replaceOnce(source: string, before: string, after: string, file: string) {
  if (source.indexOf(before) < 0 || source.indexOf(before) !== source.lastIndexOf(before)) {
    throw new Error("OHOS 构建转换未唯一匹配 " + file + ": " + before.slice(0, 100));
  }
  return source.replace(before, after);
}

const nodeBuildPlugin: BunPlugin = {
  name: "toonflowOhosNode",
  setup(build) {
    build.onResolve({ filter: /^toonflow:ohos-runtime$/ }, () => ({ path: runtimePath }));
    build.onResolve({ filter: /^(?:@babel\/(?:parser|traverse|types)|semver|mime-types|which|typescript)$/ }, args => {
      const importer = resolve(args.importer).replaceAll("\\", "/");
      // ACT: Bun 1.3 Windows 在 require.resolve 缓存的反斜杠路径上崩溃；保持各调用方原来的依赖版本。
      return { path: importer === runtimePath ? dependencies.get(args.path)! : createRequire(importer).resolve(args.path).replaceAll("\\", "/") };
    });
    build.onResolve({ filter: /renameExclusive\.ts$/ }, args => {
      if (resolve(dirname(args.importer), args.path) === resolve(root, "packages/file/src/renameExclusive.ts")) return { path: runtimePath };
    });
    build.onLoad({ filter: /\.ts$/ }, async args => {
      const file = relative(root, args.path).replaceAll("\\", "/");
      if (!memberReplacements[file] && !specialFiles.has(file)) return;
      let source = (await readFile(args.path, "utf8")).replaceAll("\r\n", "\n");
      const imports = new Set<string>();
      const change = (before: string, after: string) => { source = replaceOnce(source, before, after, file); };
      for (const [before, after] of Object.entries(memberReplacements[file] ?? {})) {
        if (!source.includes(before)) throw new Error("OHOS 构建转换缺少 " + file + ": " + before);
        source = source.replaceAll(before, after);
        imports.add(after);
      }
      if (file === "apps/mobile/src/server.ts") {
        change("import.meta.path", "import.meta.filename");
        change("bun: Bun.version", 'runtime: "node", node: process.versions.node');
        change("console.log(", "ready(");
        change("TOONFLOW_MOBILE_URL=", "");
        change('process.on("SIGTERM", () => { connection.stop(); server.close(() => process.exit(0)); });', "");
        imports.add("ready");
      }
      if (file === "packages/file/src/index.ts") {
        change('process.platform === "android" ||', '(process.platform as string) === "openharmony" || process.platform === "android" ||');
      }
      if (file === "apps/server/src/utils/plugins/tools.ts") {
        change('Bun.plugin({\n  name: "toolHost",\n  setup(build) {\n    build.module("toonflow:tool-zod", () => ({ exports: zod, loader: "object" }));\n  },\n});', "registerToolZod(zod);");
        change("const { path, metadata } = await readTool(name, directory);", "const { path, metadata, revision } = await readTool(name, directory);");
        change("import(pathToFileURL(path).href)", 'import(pathToFileURL(path).href + "?revision=" + revision)');
        change("安装成功后由安装器清除模块缓存。", "Node 按源码 revision 区分模块缓存，更新后重新加载。");
        imports.add("registerToolZod");
      }
      if (file === "apps/server/src/utils/plugins/install.ts") {
        change("const entries = new Map<string, { size: number; directory: boolean }>();", "const entries = new Map<string, { size: number; directory: boolean }>();\n  const files = new Map<string, File>();");
        change("entries.set(path.toLowerCase(), { size, directory });", "entries.set(path.toLowerCase(), { size, directory });\n    if (!directory) files.set(original, new File([tar.slice(offset + 512, offset + 512 + size)], original));");
        change('  let files: Map<string, File>;\n  try { files = await new Bun.Archive(tar).files(); }\n  catch { return invalid("技能压缩包无法读取"); }\n', "");
      }
      if (file === "apps/server/src/utils/desktop/index.ts") {
        change('import { file } from "@toonflow/file/bun";', 'import { stat, readFile } from "@toonflow/file";');
        change("const providerFile = file(selected.path);", 'const providerFile = await stat(selected.path).catch((error: NodeJS.ErrnoException) => { if (error.code !== "ENOENT" && error.code !== "ENOTDIR") throw error; });');
        change("if (!(await providerFile.exists()))", "if (!providerFile)");
        change("source: await providerFile.text(), lastModified: providerFile.lastModified", 'source: await readFile(selected.path, "utf8"), lastModified: providerFile.mtimeMs');
      }
      if (file === "packages/ffmpeg/src/index.ts") {
        change('import { file } from "@toonflow/file/bun";', 'import { existsSync } from "@toonflow/file";');
        change("await file(downloaded).exists()", "existsSync(downloaded)");
      }
      if (file === "apps/server/src/utils/mcp/resources.ts") {
        change('import { file } from "@toonflow/file/bun";', "");
        change('file(main ? skill.filePath : resolve(skill.baseDir, path)).type || "application/octet-stream"', "fileMime(main ? skill.filePath : resolve(skill.baseDir, path))");
        change('file(target).type || "application/octet-stream"', "fileMime(target)");
        imports.add("fileMime");
      }
      if (imports.size) source = 'import { ' + [...imports].join(", ") + ' } from "toonflow:ohos-runtime";\n' + source;
      return { contents: source, loader: "ts" };
    });
  },
};

export default nodeBuildPlugin;
