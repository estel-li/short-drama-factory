import { copyFile, cp, existsSync, mkdir, readFile, readdir, realpath, rm, writeAtomic } from "@toonflow/file";
import { dirname, isAbsolute, join, relative, resolve } from "node:path";
import config from "../../electrobun.config";
import nodeBuildPlugin from "./nodeBuildPlugin";
import { installBrowserCompatibility } from "./browserCompatibility";

const projectRoot = resolve(import.meta.dir, "../..");
const buildRoot = join(projectRoot, "build/ohos");
const staging = join(buildRoot, "project");
const deveco = process.env.DEVECO_HOME || "C:/Program Files/Huawei/DevEco Studio";
const sdkRoot = process.env.DEVECO_SDK_HOME || join(deveco, "sdk");
const sdk = join(sdkRoot, "default/openharmony");
const node = join(deveco, "tools/node/node.exe");
const hvigor = join(deveco, "tools/hvigor/bin/hvigorw.js");
const ohpm = join(deveco, "tools/ohpm/bin/pm-cli.js");
const setup = process.argv[2] === "setup";
const runtimePath = resolve(process.env.ohosNodePath || join(buildRoot, "runtime/libnode.so"));
const nodeHeaders = resolve(process.env.ohosNodeHeaders || join(buildRoot, "nodeHeaders/node-v24.2.0/include/node"));
const abi = process.env.ohosArch || "arm64-v8a";
const version = config.app.version;
if (process.argv.length > (setup ? 3 : 2)) throw new Error("用法：bun compat/ohos/build.ts [setup]");
if (process.platform !== "win32") throw new Error("当前 OHOS 打包使用 Windows DevEco Studio SDK。");
if (!["arm64-v8a", "x86_64"].includes(abi)) throw new Error("ohosArch 必须为 arm64-v8a 或 x86_64。");
if (!/^\d+\.\d+\.\d+$/.test(version)) throw new Error("OHOS 版本号必须为 X.Y.Z。");
const [major, minor, patch] = version.split(".").map(Number);
const versionCode = major * 1000000 + minor * 1000 + patch;
if (![major, minor, patch].every(Number.isSafeInteger) || minor > 999 || patch > 999 || versionCode <= 0 || versionCode > 2147483647) {
  throw new Error("OHOS 版本号超出 versionCode 范围，minor 和 patch 必须为 0–999。");
}
for (const path of [node, hvigor, ohpm, join(sdk, "toolchains/lib/hap-sign-tool.jar"), runtimePath, join(nodeHeaders, "node.h"), join(buildRoot, "runtime/nodeLicense.txt")]) {
  if (!existsSync(path)) throw new Error(`找不到 ${path}。请安装 DevEco Studio，并显式执行 bun run --cwd compat/ohos setup。`);
}
const runtime = await readFile(runtimePath);
const machine = runtime.length >= 20 ? runtime.readUInt16LE(18) : 0;
if (runtime.subarray(0, 4).toString("hex") !== "7f454c46" || runtime[4] !== 2 || runtime[5] !== 1 || runtime.readUInt16LE(16) !== 3 || machine !== (abi === "arm64-v8a" ? 183 : 62)) {
  throw new Error(`Node 共享库与 ${abi} 不匹配；x86_64 需要单独提供兼容 OHOS 的 ohosNodePath 和同版本头文件。`);
}
const env = { ...process.env, JAVA_HOME: join(deveco, "jbr"), DEVECO_SDK_HOME: sdkRoot };
async function run(command: string[], cwd = staging) {
  const child = Bun.spawn(command, { cwd, env, stdout: "inherit", stderr: "inherit" });
  if (await child.exited !== 0) throw new Error(`命令执行失败：${command[0]}`);
}
async function write(path: string, content: string | object) {
  const target = join(staging, path);
  await mkdir(dirname(target), { recursive: true });
  await writeAtomic(target, typeof content === "string" ? content : JSON.stringify(content, null, 2) + "\n");
}

await mkdir(buildRoot, { recursive: true });
// ACT: SDK 强制使用的文件名只生成到 build，compat 内自有源码保持小驼峰。
await write("oh-package.json5", { modelVersion: "6.0.0", name: "toonflowOhos", version, dependencies: {} });
await write("hvigor/hvigor-config.json5", { modelVersion: "6.0.0", dependencies: {}, execution: { daemon: false } });
await write("hvigorfile.ts", 'import { appTasks } from "@ohos/hvigor-ohos-plugin";\nexport default { system: appTasks };\n');
const signingConfig = process.env.ohosSigningConfig ? JSON.parse(await readFile(resolve(process.env.ohosSigningConfig), "utf8")) : undefined;
if (signingConfig && (typeof signingConfig.name !== "string" || !signingConfig.material || signingConfig.type !== "HarmonyOS")) {
  throw new Error("ohosSigningConfig 必须指向 DevEco signingConfigs 中一个完整配置对象的 JSON 文件。");
}
await write("build-profile.json5", {
  app: { signingConfigs: signingConfig ? [signingConfig] : [], products: [{ name: "default", ...(signingConfig ? { signingConfig: signingConfig.name } : {}), compatibleSdkVersion: "5.0.0(12)", targetSdkVersion: "26.0.0", runtimeOS: "HarmonyOS" }], buildModeSet: [{ name: "debug" }, { name: "release" }] },
  modules: [{ name: "entry", srcPath: "./entry", targets: [{ name: "default", applyToProducts: ["default"] }] }],
});
await write("AppScope/app.json5", { app: { bundleName: "com.toonflow.mobile", vendor: "Toonflow", versionCode, versionName: version, icon: "$media:logo", label: "$string:appName" } });
await write("AppScope/resources/base/element/string.json", { string: [{ name: "appName", value: "Toonflow" }] });
await mkdir(join(staging, "AppScope/resources/base/media"), { recursive: true });
await copyFile(join(projectRoot, "packages/assets/logo.iconset/icon_512x512.png"), join(staging, "AppScope/resources/base/media/logo.png"));
await write("entry/hvigorfile.ts", 'import { hapTasks } from "@ohos/hvigor-ohos-plugin";\nexport default { system: hapTasks };\n');
await write("entry/oh-package.json5", { name: "entry", version, dependencies: { "libtoonflowRuntime.so": "file:./src/main/cpp/types/libtoonflowRuntime" } });
await write("entry/src/main/cpp/types/libtoonflowRuntime/oh-package.json5", { name: "libtoonflowRuntime.so", version: "1.0.0", types: "./index.d.ts" });
await copyFile(join(import.meta.dir, "native/ets/runtime.d.ts"), join(staging, "entry/src/main/cpp/types/libtoonflowRuntime/index.d.ts"));
await write("entry/build-profile.json5", { apiType: "stageMode", buildOption: { externalNativeOptions: { path: "./src/main/cpp/CMakeLists.txt", arguments: "", cppFlags: "", abiFilters: [abi] } }, targets: [{ name: "default" }] });
await write("entry/src/main/module.json5", { module: {
  name: "entry", type: "entry", mainElement: "entryAbility", deviceTypes: ["phone", "tablet"], deliveryWithInstall: true, installationFree: false,
  pages: "$profile:mainPages", requestPermissions: [{ name: "ohos.permission.INTERNET" }],
  abilities: [{ name: "entryAbility", srcEntry: "./ets/entryAbility.ets", label: "$string:appName", icon: "$media:logo", startWindowIcon: "$media:logo", startWindowBackground: "$color:startBackground", exported: true,
    skills: [{ entities: ["entity.system.home"], actions: ["ohos.want.action.home"] }] }],
} });
await write("entry/src/main/resources/base/profile/mainPages.json", { src: ["pages/index"] });
await write("entry/src/main/resources/base/element/color.json", { color: [{ name: "startBackground", value: "#18181b" }] });
await write("entry/src/main/cpp/CMakeLists.txt", `cmake_minimum_required(VERSION 3.5.0)
project(toonflowRuntime)
add_library(nodeRuntime SHARED IMPORTED)
set_target_properties(nodeRuntime PROPERTIES IMPORTED_LOCATION "\${CMAKE_CURRENT_SOURCE_DIR}/../../../libs/${abi}/libnode.so")
add_library(toonflowNodeHost SHARED nodeHost.cpp imageNative.cpp)
target_compile_features(toonflowNodeHost PRIVATE cxx_std_20)
target_compile_options(toonflowNodeHost PRIVATE -fvisibility=hidden)
set_source_files_properties(nodeHost.cpp PROPERTIES INCLUDE_DIRECTORIES "${nodeHeaders.replaceAll("\\", "/")}")
target_link_libraries(toonflowNodeHost PRIVATE nodeRuntime image_source image_packer pixelmap)
target_link_options(toonflowNodeHost PRIVATE -Wl,-z,defs)
set_target_properties(toonflowNodeHost PROPERTIES BUILD_RPATH "$ORIGIN" INSTALL_RPATH "$ORIGIN")
add_library(toonflowRuntime SHARED runtime.cpp)
target_compile_features(toonflowRuntime PRIVATE cxx_std_17)
target_compile_options(toonflowRuntime PRIVATE -fvisibility=hidden)
target_link_libraries(toonflowRuntime PUBLIC libace_napi.z.so libhilog_ndk.z.so)
target_link_options(toonflowRuntime PRIVATE -Wl,-z,defs)
`);
await copyFile(join(import.meta.dir, "native/runtime.cpp"), join(staging, "entry/src/main/cpp/runtime.cpp"));
await copyFile(join(import.meta.dir, "native/nodeHost.cpp"), join(staging, "entry/src/main/cpp/nodeHost.cpp"));
for (const name of ["imageNative.cpp", "imageNative.h"]) {
  await copyFile(join(import.meta.dir, "native", name), join(staging, "entry/src/main/cpp", name));
}
await cp(join(import.meta.dir, "native/ets"), join(staging, "entry/src/main/ets"), { recursive: true });
await write("entry/src/main/ets/browserCompatibility.ets", `export default ${JSON.stringify(`(${installBrowserCompatibility.toString()})();`)};\n`);
const nativeDirectory = join(staging, "entry/libs", abi);
await mkdir(nativeDirectory, { recursive: true });
await rm(join(nativeDirectory, "libbun.so"), { force: true });
// ACT: 发布库 SONAME 带 ABI 后缀；HAP 原生库使用 .so 文件名，只调整链接名，执行代码不变。
const packagedRuntime = Buffer.from(runtime);
const programHeaders = Number(runtime.readBigUInt64LE(32));
const programHeaderSize = runtime.readUInt16LE(54);
const programHeaderCount = runtime.readUInt16LE(56);
const segments: { offset: number; address: number; size: number }[] = [];
let dynamicOffset = 0;
let dynamicSize = 0;
for (let index = 0; index < programHeaderCount; index++) {
  const offset = programHeaders + index * programHeaderSize;
  const type = runtime.readUInt32LE(offset);
  if (type === 3) throw new Error("OHOS Node 必须是真正共享库，不能使用 PIE 可执行文件");
  if (type === 1) segments.push({ offset: Number(runtime.readBigUInt64LE(offset + 8)), address: Number(runtime.readBigUInt64LE(offset + 16)), size: Number(runtime.readBigUInt64LE(offset + 32)) });
  if (type === 2) { dynamicOffset = Number(runtime.readBigUInt64LE(offset + 8)); dynamicSize = Number(runtime.readBigUInt64LE(offset + 32)); }
}
let stringsAddress = 0;
let nameOffset = -1;
for (let offset = dynamicOffset; offset < dynamicOffset + dynamicSize; offset += 16) {
  const type = Number(runtime.readBigInt64LE(offset));
  if (type === 0) break;
  if (type === 5) stringsAddress = Number(runtime.readBigUInt64LE(offset + 8));
  if (type === 14) nameOffset = Number(runtime.readBigUInt64LE(offset + 8));
}
const stringsSegment = segments.find(segment => stringsAddress >= segment.address && stringsAddress < segment.address + segment.size);
if (!stringsSegment || nameOffset < 0) throw new Error("Node 共享库缺少动态链接名");
const nameStart = stringsSegment.offset + stringsAddress - stringsSegment.address + nameOffset;
const nameEnd = runtime.indexOf(0, nameStart);
if (nameStart < 0 || nameEnd < nameStart || nameEnd - nameStart > 255) throw new Error("Node 动态链接名越界或无效");
const originalName = runtime.subarray(nameStart, nameEnd).toString();
if (!/^libnode\.so(?:\.\d+)?$/.test(originalName)) throw new Error(`不支持的 Node 动态链接名：${originalName}`);
packagedRuntime.write("libnode.so\0", nameStart);
await writeAtomic(join(nativeDirectory, "libnode.so"), packagedRuntime);
if (setup) {
  await run([node, ohpm, "install", "--all"]);
  console.log(`已准备鸿蒙工程与本地 NAPI 类型：${staging}`);
  process.exit(0);
}
if (!existsSync(join(staging, "entry/oh_modules/libtoonflowRuntime.so"))) throw new Error("请先显式执行 bun run --cwd compat/ohos setup 准备 NAPI 类型。");
await run([process.execPath, "run", "build:server"], projectRoot);

const payload = join(buildRoot, "payload");
if (existsSync(payload)) {
  const path = relative(await realpath(buildRoot), await realpath(payload));
  if (!path || path.startsWith("..") || isAbsolute(path)) throw new Error("拒绝清理 OHOS 构建目录之外的 payload");
  await rm(payload, { recursive: true });
}
await mkdir(payload, { recursive: true });
const result = await Bun.build({
  entrypoints: [join(projectRoot, "apps/mobile/src/server.ts"), join(projectRoot, "packages/mcp/src/stdio.ts"), join(projectRoot, "packages/ffmpeg/src/ffmpegWorker.ts")],
  target: "node", format: "esm", splitting: true, outdir: payload, naming: "[name].js", minify: true,
  plugins: [nodeBuildPlugin],
  external: ["@silvia-odwyer/photon-node", "@firecrawl/anydoc", "@firecrawl/anydoc-wasm", "just-bash"], define: { "process.env.appVersion": JSON.stringify(version) },
});
if (!result.success) throw new AggregateError(result.logs, "构建 OHOS 移动端服务失败");
const aiDirectory = dirname(Bun.resolveSync("@earendil-works/pi-ai", join(projectRoot, "apps/server")));
const googleDirectory = dirname(Bun.resolveSync("@google/genai", aiDirectory));
const fetchPath = Bun.resolveSync("node-fetch/src/index.js", googleDirectory);
const codingAgentDirectory = dirname(Bun.resolveSync("@earendil-works/pi-coding-agent", join(projectRoot, "apps/server")));
const webApiPath = Bun.resolveSync("undici/index.js", codingAgentDirectory);
const bootstrap = await Bun.build({
  entrypoints: [join(import.meta.dir, "bootstrap.ts")], target: "node", format: "cjs", outdir: payload,
  naming: "bootstrap.cjs", minify: true,
  plugins: [{ name: "ohosFetch", setup(build) {
    build.onResolve({ filter: /^toonflow:nodeFetch$/ }, () => ({ path: fetchPath }));
    build.onResolve({ filter: /^toonflow:webApi$/ }, () => ({ path: webApiPath }));
    build.onResolve({ filter: /^toonflow:webRequest$/ }, () => ({ path: join(dirname(webApiPath), "lib/web/fetch/request.js") }));
    build.onResolve({ filter: /^toonflow:webResponse$/ }, () => ({ path: join(dirname(webApiPath), "lib/web/fetch/response.js") }));
  } }],
});
if (!bootstrap.success) throw new AggregateError(bootstrap.logs, "构建 OHOS 服务引导失败");
for (const directory of ["web", "nodes", "tools", "ext", "providers", "skills"]) {
  await cp(join(projectRoot, "build", directory), join(payload, directory), { recursive: true });
}
await cp(join(projectRoot, "build/server/node_modules"), join(payload, "node_modules"), { recursive: true });
const revision = new Bun.CryptoHasher("sha256").update(runtime);
async function hashPayload(directory: string) {
  const entries = await readdir(directory, { withFileTypes: true });
  for (const entry of entries.sort((left, right) => left.name.localeCompare(right.name))) {
    const path = join(directory, entry.name);
    if (entry.isDirectory()) await hashPayload(path);
    else revision.update(relative(payload, path).replaceAll("\\", "/")).update("\0").update(await readFile(path)).update("\0");
  }
}
await hashPayload(payload);
const payloadRevision = revision.digest("hex");
await writeAtomic(join(payload, "revision.txt"), payloadRevision);
const raw = join(staging, "entry/src/main/resources/rawfile");
await mkdir(raw, { recursive: true });
await rm(join(raw, "payload.zip"), { force: true });
await rm(join(raw, "bun"), { force: true });
await rm(join(raw, "bunLicense.md"), { force: true });
await copyFile(join(buildRoot, "runtime/nodeLicense.txt"), join(raw, "nodeLicense.txt"));
await copyFile(join(import.meta.dir, "readme.md"), join(raw, "readme.md"));
await writeAtomic(join(raw, "revision.txt"), payloadRevision);
await run(["tar.exe", "--format=zip", "-cf", join(raw, "payload.zip"), "-C", payload, "."]);
await run([node, hvigor, "--mode", "module", "-p", "product=default", "-p", "module=entry@default", "-p", "buildMode=debug", "assembleHap", "--no-daemon"]);
const signed = signingConfig ? "signed" : "unsigned";
const output = join(buildRoot, `toonflow-${version}-ohos-${abi}-${signed}.hap`);
await copyFile(join(staging, `entry/build/default/outputs/default/entry-default-${signed}.hap`), output);
console.log(`OHOS HAP 已生成${signingConfig ? "" : "（未签名，安装前需配置 ohosSigningConfig）"}：${output}`);
