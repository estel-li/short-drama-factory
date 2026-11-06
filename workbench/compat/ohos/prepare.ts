import { existsSync, mkdir, writeAtomic } from "@toonflow/file";
import { file } from "@toonflow/file/bun";
import { resolve } from "node:path";

const runtimeRoot = resolve(import.meta.dir, "../../build/ohos/runtime");
const runtimePath = resolve(runtimeRoot, "libnode.so");
const runtimeHash = "3019bf5f9a279d98a87606fc13c53b0e797b6a50cf174f8a1243d880c71151a1";
await mkdir(runtimeRoot, { recursive: true });
if (!existsSync(runtimePath)) {
  const url = "https://github.com/electerm/ohos-node-shared/releases/download/ohos-node-shared-v24.2.0/libnode-arm64.so";
  console.log("下载 Node 24.2.0 OHOS ARM64 共享运行时");
  const response = await fetch(url);
  if (!response.ok) throw new Error(`下载 OHOS Node 失败：HTTP ${response.status}`);
  const bytes = new Uint8Array(await response.arrayBuffer());
  if (new Bun.CryptoHasher("sha256").update(bytes).digest("hex") !== runtimeHash) throw new Error("OHOS Node 下载校验失败");
  await writeAtomic(runtimePath, bytes);
}
if (new Bun.CryptoHasher("sha256").update(await file(runtimePath).arrayBuffer()).digest("hex") !== runtimeHash) {
  throw new Error(`OHOS Node 缓存校验失败，请移除后重新执行 setup：${runtimePath}`);
}
const headersRoot = resolve(runtimeRoot, "../nodeHeaders");
const headersArchive = resolve(headersRoot, "node-v24.2.0-headers.tar.gz");
const headersHash = "aa5506d209cd9da6e3480ffca5ce9a54ed0ae4e169993d9bd14db18548d801b0";
await mkdir(headersRoot, { recursive: true });
if (!existsSync(headersArchive)) {
  const response = await fetch("https://nodejs.org/download/release/v24.2.0/node-v24.2.0-headers.tar.gz");
  if (!response.ok) throw new Error(`下载 Node 头文件失败：HTTP ${response.status}`);
  const bytes = new Uint8Array(await response.arrayBuffer());
  if (new Bun.CryptoHasher("sha256").update(bytes).digest("hex") !== headersHash) throw new Error("Node 头文件下载校验失败");
  await writeAtomic(headersArchive, bytes);
}
if (new Bun.CryptoHasher("sha256").update(await file(headersArchive).arrayBuffer()).digest("hex") !== headersHash) {
  throw new Error(`Node 头文件缓存校验失败：${headersArchive}`);
}
const extraction = Bun.spawn(["tar.exe", "-xf", headersArchive, "-C", headersRoot], { stdout: "inherit", stderr: "inherit" });
if (await extraction.exited !== 0) throw new Error("解压 Node 头文件失败");
const license = await fetch("https://raw.githubusercontent.com/nodejs/node/v24.2.0/LICENSE");
if (!license.ok) throw new Error(`下载 Node 许可失败：HTTP ${license.status}`);
await writeAtomic(resolve(runtimeRoot, "nodeLicense.txt"), await license.text());
console.log(`已准备 OHOS ARM64 Node 共享库和同版本头文件：${runtimePath}`);
