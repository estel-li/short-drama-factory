import { readFile } from "@toonflow/file";
import { spawn, type SpawnOptions } from "node:child_process";
import { registerHooks } from "node:module";
import { text } from "node:stream/consumers";
import { Worker } from "node:worker_threads";
export { setTimeout as sleep } from "node:timers/promises";

// ACT: 依赖由 nodeBuildPlugin 从现有工作区解析后打入包，不在手机上查找开发依赖。
const { parse } = require("@babel/parser") as typeof import("../../apps/server/node_modules/@babel/parser");
const semver = require("semver") as { compare(left: string, right: string, options: { loose: boolean }): number };
const mimeTypes = require("mime-types") as { lookup(path: string): string | false };
const executable = require("which") as { sync(command: string, options: { nothrow: boolean }): string | null };

type NativeBinding = {
  ready(url: string): void;
  log(message: string): void;
  renameExclusive(source: string, target: string): void;
};

function nativeBinding(): NativeBinding {
  return (process as NodeJS.Process & { _linkedBinding(name: string): NativeBinding })._linkedBinding("toonflowNative");
}

export const ready = (url: string) => nativeBinding().ready(url);
export const log = (message: string) => nativeBinding().log(message);
export function renameExclusive(source: string, target: string) {
  if (source.includes("\0") || target.includes("\0")) {
    throw Object.assign(new TypeError("文件路径不能包含空字节"), { code: "ERR_INVALID_ARG_VALUE" });
  }
  nativeBinding().renameExclusive(source, target);
}
export const semverOrder = (left: string, right: string) => semver.compare(left, right, { loose: true });
export const fileMime = (path: string) => mimeTypes.lookup(path) || "application/octet-stream";
export const which = (command: string) => executable.sync(command, { nothrow: true });

export function escapeHtml(value: unknown) {
  const entities: Record<string, string> = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#x27;" };
  return String(value).replace(/[&<>"']/g, character => entities[character]!);
}

export function createTranspiler(options: { loader: "js" | "ts"; target?: string; define?: Record<string, string> }) {
  function syntax(source: string) {
    return parse(source, { sourceType: "unambiguous", plugins: options.loader === "ts" ? ["typescript"] : [] });
  }
  return {
    scan(source: string) {
      const ast = syntax(source);
      const names = new Set<string>();
      const { getBindingIdentifiers } = require("@babel/types") as { getBindingIdentifiers(node: unknown): Record<string, unknown> };
      for (const node of ast.program.body) {
        if (node.type === "ExportDefaultDeclaration") names.add("default");
        if (node.type !== "ExportNamedDeclaration") continue;
        if (node.declaration) for (const name of Object.keys(getBindingIdentifiers(node.declaration))) names.add(name);
        for (const specifier of node.specifiers) names.add(specifier.exported.type === "Identifier" ? specifier.exported.name : specifier.exported.value);
      }
      return { exports: [...names] };
    },
    transformSync(source: string) {
      const ast = syntax(source);
      if (options.define) {
        if (Object.keys(options.define).some(name => name !== "require") || options.define.require !== "undefined") {
          throw new TypeError("OHOS 转译器仅支持当前供应商使用的 require: undefined 定义");
        }
        const edits: { start: number; end: number; value: string }[] = [];
        const traverse = require("@babel/traverse").default;
        traverse(ast, {
          ReferencedIdentifier(path: any) {
            if (path.node.name !== "require" || path.scope.hasBinding("require")) return;
            const shorthand = path.parent.type === "ObjectProperty" && path.parent.shorthand;
            edits.push({ start: path.node.start, end: path.node.end, value: shorthand ? "require: (void 0)" : "(void 0)" });
          },
        });
        for (const edit of edits.sort((left, right) => right.start - left.start)) {
          source = source.slice(0, edit.start) + edit.value + source.slice(edit.end);
        }
      }
      const typescript = require("typescript") as typeof import("../../packages/extScaffold/node_modules/typescript");
      const result = typescript.transpileModule(source, {
        fileName: options.loader === "ts" ? "provider.ts" : "plugin.js",
        compilerOptions: { target: typescript.ScriptTarget.ESNext, module: typescript.ModuleKind.ESNext, verbatimModuleSyntax: true },
        reportDiagnostics: true,
      });
      const errors = result.diagnostics?.filter(item => item.category === typescript.DiagnosticCategory.Error);
      if (errors?.length) throw new SyntaxError(errors.map(item => typescript.flattenDiagnosticMessageText(item.messageText, "\n")).join("\n"));
      return result.outputText;
    },
  };
}

export function registerToolZod(zod: Record<string, unknown>) {
  const key = Symbol.for("toonflow.ohos.toolZod");
  const registry = globalThis as typeof globalThis & { [key: symbol]: unknown };
  if (registry[key]) {
    if (registry[key] !== zod) throw new Error("工具 Zod 已绑定到另一个宿主实例");
    return;
  }
  registry[key] = zod;
  const source = 'const host = globalThis[Symbol.for("toonflow.ohos.toolZod")];\n' + Object.keys(zod)
    .map((name, index) => "const value" + index + " = host[" + JSON.stringify(name) + "]; export { value" + index + " as " + JSON.stringify(name) + " };").join("\n");
  registerHooks({
    resolve(specifier, context, nextResolve) {
      return specifier === "toonflow:tool-zod" ? { url: specifier, shortCircuit: true } : nextResolve(specifier, context);
    },
    load(url, context, nextLoad) {
      return url === "toonflow:tool-zod" ? { format: "module", source, shortCircuit: true } : nextLoad(url, context);
    },
  });
}

export function spawnProcess(command: string[], options: SpawnOptions & { stdin: "ignore"; stdout: "pipe"; stderr: "ignore" }) {
  const [file, ...args] = command;
  if (!file) throw new TypeError("缺少子进程可执行文件");
  const child = spawn(file, args, { ...options, stdio: ["ignore", "pipe", "ignore"] });
  const exited = new Promise<number>((resolve, reject) => {
    let failure: Error | undefined;
    child.on("error", error => { failure ??= error; });
    // 取消错误可能早于 close；进程关闭后调用方才能清理可执行文件。
    child.once("close", code => { if (failure) reject(failure); else resolve(code ?? -1); });
  });
  return { stdout: { text: () => text(child.stdout!) }, exited };
}

type ImageInput = string | ArrayBuffer | ArrayBufferView | Blob;
type ImageResult = { width: number; height: number; format: string; bytes: Uint8Array };
type ImageOptions = { width: number; height: number; format: string; quality: number };

function validateImageOptions(options: Record<string, unknown>, allowed: string[]) {
  if (!options || typeof options !== "object" || Array.isArray(options)) throw new TypeError("图片选项必须是对象");
  for (const key of Object.keys(options)) {
    if (!allowed.includes(key)) throw Object.assign(new Error("HarmonyOS 图片接口不支持选项：" + key), { code: "ENOTSUP" });
  }
}

function processImage(bytes: Uint8Array, options: ImageOptions): Promise<ImageResult> {
  // ACT: 每次处理使用独立 Worker；Node 官方 linked binding 会查找父环境，保持解码不阻塞服务线程。
  const worker = new Worker(`
    const { parentPort, workerData } = require('node:worker_threads');
    try {
      const native = process._linkedBinding('toonflowNative');
      const { bytes, options } = workerData;
      if (options.format === 'source') options.format = native.processImage(bytes, 0, 0, '', 80).format;
      const result = native.processImage(bytes, options.width, options.height, options.format, options.quality);
      parentPort.postMessage({ result }, [result.bytes.buffer]);
    } catch (error) {
      parentPort.postMessage({ error: { message: error.message, name: error.name, code: error.code } });
    } finally {
      parentPort.close();
    }
  `, { eval: true, workerData: { bytes, options } });
  return new Promise((resolve, reject) => {
    worker.once("message", ({ result, error }: { result: ImageResult; error?: { message: string; name: string; code?: string } }) => {
      if (error) reject(Object.assign(new Error(error.message), { name: error.name, code: error.code }));
      else resolve(result);
    });
    worker.once("error", reject);
    worker.once("exit", code => reject(new Error("图片处理线程未返回结果，退出码 " + code)));
  });
}

export class runtimeImage {
  private width = 0;
  private height = 0;
  private format = "source";
  private quality = 80;

  constructor(private readonly input: ImageInput, options: Record<string, unknown> = {}) {
    validateImageOptions(options, []);
    if (typeof input === "string") {
      if (!input || input.includes("\0")) throw new TypeError("图片路径不能为空或包含空字节");
      return;
    }
    if (input instanceof Blob) return;
    const buffer = ArrayBuffer.isView(input) ? input.buffer : input;
    if (!(buffer instanceof ArrayBuffer) || buffer.resizable || buffer.byteLength === 0) {
      throw new TypeError("图片输入必须是路径、Blob 或非共享且不可调整大小的字节缓冲区");
    }
  }

  private async inputBytes(): Promise<Uint8Array> {
    if (typeof this.input === "string") return readFile(this.input);
    if (this.input instanceof Blob) return new Uint8Array(await this.input.arrayBuffer());
    const bytes = ArrayBuffer.isView(this.input)
      ? new Uint8Array(this.input.buffer, this.input.byteOffset, this.input.byteLength)
      : new Uint8Array(this.input);
    // 保留调用方的缓冲区；连续 buffer() 以及并发 metadata() 不转移或分离原始数据。
    return new Uint8Array(bytes);
  }

  async metadata() {
    const { width, height, format } = await processImage(await this.inputBytes(), { width: 0, height: 0, format: "", quality: 80 });
    return { width, height, format };
  }

  resize(width: number, height: number, options: Record<string, unknown> = {}) {
    validateImageOptions(options, ["fit"]);
    if (options.fit !== "fill") throw Object.assign(new Error("HarmonyOS 图片缩放当前支持 fit: fill"), { code: "ENOTSUP" });
    if (![width, height].every(value => Number.isInteger(value) && value > 0 && value <= 0x7fffffff)) {
      throw new RangeError("图片宽高必须是有效的正整数");
    }
    this.width = width;
    this.height = height;
    return this;
  }

  private encode(format: string, options: Record<string, unknown>) {
    validateImageOptions(options, format === "png" ? [] : ["quality"]);
    const quality = options.quality === undefined ? 80 : options.quality;
    if (typeof quality !== "number" || !Number.isInteger(quality) || quality < 1 || quality > 100) {
      throw new RangeError("图片编码质量必须是 1 到 100 之间的整数");
    }
    this.format = format;
    this.quality = quality;
    return this;
  }

  png(options: Record<string, unknown> = {}) { return this.encode("png", options); }
  jpeg(options: Record<string, unknown> = {}) { return this.encode("jpeg", options); }
  webp(options: Record<string, unknown> = {}) { return this.encode("webp", options); }

  async buffer() {
    const options = { width: this.width, height: this.height, format: this.format, quality: this.quality };
    const result = await processImage(await this.inputBytes(), options);
    return Buffer.from(result.bytes.buffer, result.bytes.byteOffset, result.bytes.byteLength);
  }
}

// Zig std.hash.Wyhash 的 64 位算法；保留已保存扩展源码的 revision/hash。
export function hash(data: string | ArrayBufferView | ArrayBuffer | SharedArrayBuffer, seed: bigint | number = 0n): bigint {
  if (typeof seed === "number" && (!Number.isSafeInteger(seed) || seed < 0 || seed >= 2 ** 51)) {
    throw new TypeError("哈希 seed 须为非负 Int52 整数；负数和更大整数请使用 bigint");
  }
  const bytes = typeof data === "string" ? Buffer.from(data, "utf8")
    : ArrayBuffer.isView(data) ? Buffer.from(data.buffer, data.byteOffset, data.byteLength) : Buffer.from(data);
  const secret = [0xa0761d6478bd642fn, 0xe7037ed1a0b428dbn, 0x8ebc6af09c88c6e3n, 0x589965cc75374cc3n];
  const mask = (1n << 64n) - 1n;
  const mix = (left: bigint, right: bigint) => {
    const product = left * right;
    return (product & mask) ^ (product >> 64n);
  };
  const read = (offset: number) => bytes.readBigUInt64LE(offset);
  const length = bytes.length;
  let state = BigInt.asUintN(64, BigInt(seed));
  state ^= mix(state ^ secret[0]!, secret[1]!);
  let first = 0n, second = 0n, offset = 0;
  if (length <= 16) {
    if (length >= 4) {
      const quarter = (length >> 3) << 2, end = length - 4;
      first = (BigInt(bytes.readUInt32LE(0)) << 32n) | BigInt(bytes.readUInt32LE(quarter));
      second = (BigInt(bytes.readUInt32LE(end)) << 32n) | BigInt(bytes.readUInt32LE(end - quarter));
    } else if (length) {
      first = (BigInt(bytes[0]!) << 16n) | (BigInt(bytes[length >> 1]!) << 8n) | BigInt(bytes[length - 1]!);
    }
  } else {
    let middle = state, last = state;
    for (; offset + 48 < length; offset += 48) {
      state = mix(read(offset) ^ secret[1]!, read(offset + 8) ^ state);
      middle = mix(read(offset + 16) ^ secret[2]!, read(offset + 24) ^ middle);
      last = mix(read(offset + 32) ^ secret[3]!, read(offset + 40) ^ last);
    }
    state ^= middle ^ last;
    for (; offset + 16 < length; offset += 16) state = mix(read(offset) ^ secret[1]!, read(offset + 8) ^ state);
    first = read(length - 16);
    second = read(length - 8);
  }
  const product = (first ^ secret[1]!) * (second ^ state);
  return mix((product & mask) ^ secret[0]! ^ BigInt(length), (product >> 64n) ^ secret[1]!);
}
