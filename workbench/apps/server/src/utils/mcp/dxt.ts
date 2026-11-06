import { randomUUID } from "node:crypto";
import { homedir } from "node:os";
import { dirname, isAbsolute, join, relative, resolve, sep } from "node:path";
import { chmod, lstat, mkdir, realpath, rm, writeFile } from "@toonflow/file";
import { z } from "zod";
import { mcpServerSchema } from "@toonflow/mcp/client";
import type { McpServerConfig } from "@toonflow/mcp/client";
import conf from "@/utils/conf";
import { decodeText, skillPath, skillZip } from "@/utils/plugins/install";
import { saveImportedMcpServers } from "@/utils/mcp/servers";
import { isWithin } from "@/utils/workspace/files";
import { getRuntimePlatform } from "@/lib/platform";
import { t, translateMessage } from "@/lib/i18n";

export const maxDxtBytes = 50 * 1024 * 1024;
const textSchema = z.string().max(8192).refine(value => !value.includes("\0"), "内容不能包含空字符");
const userValueSchema = z.union([textSchema, z.number().finite(), z.boolean(), z.array(textSchema).max(256)]);
export const dxtUserConfigSchema = z.record(z.string().min(1).max(128), userValueSchema);
const configFields = {
  command: textSchema.refine(value => !!value.trim(), "DXT 启动命令不能为空"),
  args: z.array(textSchema).max(256).optional(),
  env: z.record(z.string().min(1).max(256), textSchema).optional(),
};
const userOptionSchema = z.strictObject({
  type: z.enum(["string", "number", "boolean", "directory", "file"]),
  title: z.string().min(1).max(200),
  description: z.string().max(4000).optional(),
  required: z.boolean().optional(),
  default: userValueSchema.optional(),
  sensitive: z.boolean().optional(),
  multiple: z.boolean().optional(),
  min: z.number().finite().optional(),
  max: z.number().finite().optional(),
});
const manifestSchema = z.object({
  dxt_version: z.string().optional(),
  manifest_version: z.string().optional(),
  name: z.string().min(1).max(100),
  display_name: z.string().min(1).max(100).optional(),
  version: z.string().min(1).max(100),
  description: z.string().max(4000),
  author: z.object({ name: z.string().min(1) }),
  server: z.strictObject({
    type: z.enum(["node", "python", "binary"]),
    entry_point: z.string().min(1).max(1024),
    mcp_config: z.strictObject({
      ...configFields,
      platform_overrides: z.partialRecord(z.enum(["win32", "darwin", "linux"]), z.strictObject(configFields).partial()).optional(),
    }),
  }),
  compatibility: z.object({ platforms: z.array(z.enum(["win32", "darwin", "linux"])).optional() }).optional(),
  user_config: z.record(z.string().min(1).max(128), userOptionSchema).optional(),
});
type Manifest = z.infer<typeof manifestSchema>;
type UserValue = z.infer<typeof userValueSchema>;
type Variables = Record<string, string | string[]>;

function invalid(message: string, status = 400): never {
  throw Object.assign(new Error(message), { status });
}

function systemVariables(): Variables {
  const userHome = homedir();
  // ACT: 使用宿主默认用户目录；重定向目录可在导入表单改写，后续可接入宿主已知文件夹接口。
  return {
    HOME: userHome,
    DESKTOP: join(userHome, "Desktop"),
    DOCUMENTS: join(userHome, "Documents"),
    DOWNLOADS: join(userHome, "Downloads"),
    pathSeparator: sep,
    "/": sep,
  };
}

function replaceVariables(value: string, variables: Variables) {
  if (value.replace(/\$\{[^}]*\}/g, "").includes("${")) invalid("DXT 包包含不完整的变量表达式");
  return value.replace(/\$\{([^}]*)\}/g, (_token, key: string) => {
    if (!Object.hasOwn(variables, key)) invalid(t`DXT 包包含未支持的变量或未填写的配置：${key}`);
    const replacement = variables[key]!;
    if (Array.isArray(replacement)) invalid(t`DXT 多值配置只能作为独立启动参数使用：${key}`);
    return replacement;
  });
}

function defaultValue(value: UserValue | undefined, variables: Variables) {
  if (typeof value === "string") return replaceVariables(value, variables);
  if (Array.isArray(value)) return value.map(item => replaceVariables(item, variables));
  return value;
}

function readDxt(fileName: string, content: string) {
  if (getRuntimePlatform().mobile) invalid("当前移动端不支持安装本地 DXT，请在桌面端或服务器本机导入");
  if (fileName.length > 128 || /[\\/]/.test(fileName) || !/\.(dxt|mcpb)$/i.test(fileName)) invalid("请选择 .dxt 或 .mcpb 文件");
  if (content.length > Math.ceil(maxDxtBytes / 3) * 4) invalid("DXT 压缩包不能超过 50 MB", 413);
  const bytes = Buffer.from(content, "base64");
  if (!bytes.length || bytes.length > maxDxtBytes) invalid("DXT 压缩包为空或超过 50 MB", 413);
  const fileModes = new Map<string, number>();
  const files = skillZip(bytes, { maxBytes: 200 * 1024 * 1024, maxEntries: 20_000, fileModes });
  const raw = files.get("manifest.json");
  if (!raw || raw.length > 1024 * 1024) invalid("DXT 包根目录必须包含不超过 1 MB 的 manifest.json");
  let source: unknown;
  try { source = JSON.parse(decodeText(raw)); }
  catch { invalid("DXT manifest.json 不是有效的 UTF-8 JSON"); }
  const parsed = manifestSchema.safeParse(source);
  if (!parsed.success) invalid(t`DXT 清单格式无效：${parsed.error.issues.map(issue => `${issue.path.join(".")} ${translateMessage(issue.message)}`).join("; ")}`);
  const manifest = parsed.data;
  const version = manifest.manifest_version ?? manifest.dxt_version;
  if (!version || !["0.1", "0.2", "0.3"].includes(version)) invalid("当前仅支持 DXT/MCPB 0.1、0.2、0.3 的静态 node、python 或 binary 服务");
  if (manifest.manifest_version && manifest.dxt_version && manifest.manifest_version !== manifest.dxt_version) invalid("DXT 清单中的规范版本不一致");
  if (manifest.compatibility?.platforms && !manifest.compatibility.platforms.includes(process.platform as "win32" | "darwin" | "linux")) invalid("此 DXT 包不支持当前操作系统");
  let entry: string;
  try { entry = skillPath(manifest.server.entry_point); }
  catch { invalid("DXT entry_point 必须是包内安全的相对文件路径"); }
  if (!files.has(entry) && !(manifest.server.type === "binary" && process.platform === "win32" && files.has(`${entry}.exe`))) invalid(t`DXT 包缺少入口文件：${entry}`);
  const options = manifest.user_config ?? {};
  if (Object.keys(options).length > 128) invalid("DXT 最多支持 128 个配置项");
  const variables = systemVariables();
  const userConfig = Object.entries(options).map(([key, option]) => {
    if (option.multiple && !["file", "directory"].includes(option.type)) invalid(t`DXT 多值配置仅支持文件或目录：${key}`);
    if (option.min !== undefined && option.max !== undefined && option.min > option.max) invalid(t`DXT 配置的最小值大于最大值：${key}`);
    return { key, ...option, default: defaultValue(option.default, variables) };
  });
  return { files, fileModes, manifest, userConfig };
}

function selectedConfig(manifest: Manifest) {
  const base = manifest.server.mcp_config;
  const platform = base.platform_overrides?.[process.platform as "win32" | "darwin" | "linux"];
  return {
    command: platform?.command ?? base.command,
    args: platform?.args ?? base.args ?? [],
    env: { ...base.env, ...platform?.env },
  };
}

function resolveConfig(manifest: Manifest, variables: Variables) {
  const config = selectedConfig(manifest);
  return {
    command: replaceVariables(config.command, variables),
    args: config.args.flatMap(arg => {
      const key = arg.match(/^\$\{(user_config\.[^}]+)\}$/)?.[1];
      return key && Array.isArray(variables[key]) ? variables[key] as string[] : [replaceVariables(arg, variables)];
    }),
    env: Object.fromEntries(Object.entries(config.env).map(([key, value]) => [key, replaceVariables(value, variables)])),
  };
}

export function inspectDxt(fileName: string, content: string) {
  const { manifest, userConfig } = readDxt(fileName, content);
  // ACT: 预览只检查模板与声明，不启动包内代码，不要求用户此时已填写必填项。
  resolveConfig(manifest, {
    ...systemVariables(), __dirname: "",
    ...Object.fromEntries(userConfig.map(option => [`user_config.${option.key}`, option.multiple ? [] : ""])),
  });
  return { name: manifest.display_name ?? manifest.name, version: manifest.version, description: manifest.description, userConfig };
}

function userVariables(options: ReturnType<typeof readDxt>["userConfig"], values: Record<string, UserValue>): Variables {
  if (Object.keys(values).some(key => !options.some(option => option.key === key))) invalid("DXT 配置中包含清单未声明的字段");
  return Object.fromEntries(options.flatMap(option => {
    const value = Object.hasOwn(values, option.key) ? values[option.key] : option.default;
    if (value === undefined) {
      if (option.required) invalid(t`请填写 DXT 配置：${option.title}`);
      // ACT: 可选项未填写时传空值，不把清单声明的可选项变成必填项。
      return [[`user_config.${option.key}`, option.multiple ? [] : ""]];
    }
    const valid = option.multiple ? Array.isArray(value) && value.every(item => typeof item === "string")
      : option.type === "number" ? typeof value === "number" && Number.isFinite(value)
        : option.type === "boolean" ? typeof value === "boolean" : typeof value === "string";
    if (!valid) invalid(t`DXT 配置类型不正确：${option.title}`);
    if (option.required && (typeof value === "string" && !value.trim() || Array.isArray(value) && (!value.length || value.some(item => !item.trim())))) invalid(t`请填写 DXT 配置：${option.title}`);
    if (typeof value === "number" && (option.min !== undefined && value < option.min || option.max !== undefined && value > option.max)) invalid(t`DXT 配置超出允许范围：${option.title}`);
    return [[`user_config.${option.key}`, Array.isArray(value) ? value : String(value)]];
  }));
}

async function bundleRoot(create = false) {
  const root = resolve(dirname(conf.path), "mcpBundles");
  if (create) await mkdir(root, { recursive: true, mode: 0o700 });
  const info = await lstat(root).catch((error: NodeJS.ErrnoException) => {
    if (error.code === "ENOENT" && !create) return null;
    throw error;
  });
  if (!info) return;
  if (!info.isDirectory() || info.isSymbolicLink() || relative(root, await realpath(root)) !== "") invalid("MCP 包目录不能包含符号链接或重定向路径", 403);
  return root;
}

async function removeBundleDirectory(bundleId: string) {
  if (!z.uuid().safeParse(bundleId).success) invalid("MCP 包目录标识无效", 403);
  const root = await bundleRoot();
  if (!root) return;
  const target = resolve(root, bundleId);
  if (!isWithin(root, target) || dirname(target) !== root) invalid("MCP 包目录越界", 403);
  const info = await lstat(target).catch((error: NodeJS.ErrnoException) => {
    if (error.code === "ENOENT") return null;
    throw error;
  });
  if (!info) return;
  if (!info.isDirectory() || info.isSymbolicLink() || relative(target, await realpath(target)) !== "") invalid("MCP 包目录不能包含符号链接或重定向路径", 403);
  await rm(target, { recursive: true, force: false });
}

export async function importDxt(fileName: string, content: string, userConfig: Record<string, UserValue>) {
  const { manifest, files, fileModes, userConfig: options } = readDxt(fileName, content);
  const values = dxtUserConfigSchema.parse(userConfig);
  const bundleId = randomUUID();
  const root = await bundleRoot(true);
  const directory = resolve(root!, bundleId);
  const config = resolveConfig(manifest, { ...systemVariables(), __dirname: directory, ...userVariables(options, values) });
  if (manifest.server.type === "binary" || /[\\/]/.test(config.command) && !isAbsolute(config.command)) {
    config.command = resolve(directory, config.command);
    if (manifest.server.type === "binary" && process.platform === "win32" && !config.command.toLowerCase().endsWith(".exe")) config.command += ".exe";
    const commandPath = relative(directory, config.command).split(sep).join("/");
    if (!isWithin(directory, config.command) || !files.has(commandPath)) invalid("DXT 启动文件必须存在于包内，且不能指向包外目录");
  }
  const server: McpServerConfig = { name: manifest.display_name ?? manifest.name, transport: "stdio", enabled: true, cwd: directory, ...config };
  mcpServerSchema.parse(server);
  await mkdir(directory, { mode: 0o700 });
  try {
    for (const [path, bytes] of files) {
      const target = resolve(directory, path);
      if (!isWithin(directory, target)) invalid("DXT 文件路径越界", 403);
      await mkdir(dirname(target), { recursive: true, mode: 0o700 });
      await writeFile(target, bytes, { flag: "wx", mode: 0o600 | ((fileModes.get(path) ?? 0) & 0o100) });
    }
    if (manifest.server.type === "binary" && process.platform !== "win32") await chmod(config.command, 0o700);
    return { server: saveImportedMcpServers([server], bundleId)[0]! };
  } catch (error) {
    await removeBundleDirectory(bundleId);
    throw error;
  }
}

export async function removeMcpBundle(id: string) {
  const bundleId = conf.get("mcpBundles", {})[id];
  if (!bundleId) return;
  await removeBundleDirectory(bundleId);
  const bundles = conf.get("mcpBundles", {});
  if (bundles[id] !== bundleId) return;
  delete bundles[id];
  conf.set("mcpBundles", bundles);
}
