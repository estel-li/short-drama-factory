import { cp, mkdir, readdir, realpath, rm } from "@toonflow/file";
import { dirname, resolve } from "node:path";

export default async function copySandboxPackages(nodeModulesDirectory: string) {
  async function copyPackage(packageName: string, fromDirectory: string, paths: string[]) {
    const directory = dirname(await realpath(Bun.resolveSync(`${packageName}/package.json`, fromDirectory)));
    const destination = resolve(nodeModulesDirectory, packageName);
    const notices = (await readdir(directory)).filter((name) => /^(license|copying|notice|third_party_notices)(\.|$)/i.test(name));
    await rm(destination, { recursive: true, force: true });
    for (const path of ["package.json", ...notices, ...paths]) {
      const target = resolve(destination, path);
      await mkdir(dirname(target), { recursive: true });
      await cp(resolve(directory, path), target, {
        recursive: true,
        dereference: true,
        filter: (source) => !/\.(?:map|d\.[cm]?ts)$/.test(source),
      });
    }
    return directory;
  }

  // ACT: 清单对应 just-bash 3.6.0 的 ESM 外部依赖；升级时同步其入口及 Worker 相对目录。
  const sandboxDirectory = resolve(import.meta.dir, "../../../packages/tools/sandbox");
  const bashDirectory = await copyPackage("just-bash", sandboxDirectory, [
    "dist/bundle/index.js",
    "dist/bundle/chunks",
    "vendor/cpython-emscripten",
  ]);
  await copyPackage("run", bashDirectory, ["dist"]);
  await copyPackage("sql.js", bashDirectory, ["dist/sql-wasm.js", "dist/sql-wasm.wasm"]);
  await copyPackage("diff", bashDirectory, ["libesm"]);
  await copyPackage("sprintf-js", bashDirectory, ["src/sprintf.js"]);
  await copyPackage("seek-bzip", bashDirectory, ["lib"]);
  const markdownDirectory = await copyPackage("turndown", bashDirectory, ["lib/turndown.cjs.js", "lib/turndown.es.js"]);
  await copyPackage("@mixmark-io/domino", markdownDirectory, ["lib"]);
  const fetchDirectory = await copyPackage("guarded-fetch", bashDirectory, ["dist/index.mjs"]);
  await copyPackage("undici", fetchDirectory, ["index.js", "index-fetch.js", "lib"]);
  await copyPackage("ipaddr.js", fetchDirectory, ["lib"]);
  // ACT: 不携带可选的 xz/zstd 原生编译链；这些压缩格式沿用上游的缺少依赖错误。
}
