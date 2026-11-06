import { basename, join, relative } from "node:path";
import { RE2JS } from "re2js";
import { z } from "zod";
import type { ToolContext, ToolDefinition } from "@toonflow/tools-scaffold/runtime";

const pathSchema = z.string().min(1).max(4096).optional().describe("当前工作区内的搜索路径，默认工作区根目录");
const globSchema = z.string().min(1).max(512)
  .refine(pattern => !/[{}\[\]]|[@+?!*]\(/.test(pattern), "glob 仅支持 *、**、?，不支持花括号、字符集合或 extglob")
  .describe("文件 glob，例如 *.ts、**/*.json 或 src/**/*.ts；支持 *、**、?，不支持 {}、[] 或 extglob");
const findSchema = z.object({
  pattern: globSchema,
  path: pathSchema,
  limit: z.number().int().min(1).max(2000).default(1000),
}).strict();
const grepSchema = z.object({
  pattern: z.string().min(1).max(1024).describe("RE2 正则表达式；literal=true 时按普通文本匹配"),
  path: pathSchema,
  glob: globSchema.optional(),
  ignoreCase: z.boolean().default(false),
  literal: z.boolean().default(false),
  context: z.number().int().min(0).max(10).default(0),
  limit: z.number().int().min(1).max(1000).default(100),
}).strict();

function createGlobMatcher(pattern: string) {
  const segments = pattern.split("/");
  let expression = "^";
  for (let index = 0; index < segments.length; index++) {
    const segment = segments[index]!;
    if (segment === "**") {
      expression += index === segments.length - 1 ? ".*" : "(?:[^/]+/)*";
      continue;
    }
    for (const character of segment) {
      if (character === "*") expression += "[^/]*";
      else if (character === "?") expression += "[^/]";
      else expression += /[\\^$.*+?()[\]{}|]/.test(character) ? `\\${character}` : character;
    }
    if (index < segments.length - 1) expression += "/";
  }
  return RE2JS.compile(`${expression}$`);
}

export function createSearchTools({ cwd, files, resolvePath }: Pick<ToolContext, "cwd" | "files" | "resolvePath">): ToolDefinition[] {
  return ["grep", "find"].map(name => ({
    name,
    label: name === "grep" ? "搜索文件内容" : "查找文件",
    description: name === "grep"
      ? "搜索当前工作区内的文本，返回工作区相对路径、行号和匹配内容。支持 RE2 正则、普通文本、大小写和上下文选项。跳过 .git、node_modules、符号链接、二进制及超过 8 MiB 的文件；搜索总量最多 64 MiB。正则工作量超限会提示跳过或停止，可用 literal 搜索长行。"
      : "按 glob 查找当前工作区内的文件，返回工作区相对路径。跳过 .git、node_modules 和符号链接。不会查询工作区以外的目录。",
    promptSnippet: name === "grep" ? "搜索工作区文本内容。" : "按 glob 查找工作区文件。",
    promptGuidelines: ["grep/find 仅搜索当前工作区，不读取全局技能目录；达到结果、遍历或容量限制会明确提示，必要时缩小 path 或 glob。"],
    parameters: z.toJSONSchema(name === "grep" ? grepSchema : findSchema, { io: "input", target: "draft-07" }),
    async execute(_id, params, signal) {
      const grep = name === "grep" ? grepSchema.parse(params) : undefined;
      const request = grep ?? findSchema.parse(params);
      const timeoutSignal = AbortSignal.timeout(30000);
      signal = signal ? AbortSignal.any([signal, timeoutSignal]) : timeoutSignal;
      signal?.throwIfAborted();
      const root = await resolvePath(request.path ?? ".");
      const info = await files.stat(root);
      if (!info.isDirectory() && !(grep && info.isFile())) throw new Error("请指定工作区内的普通文件夹，grep 也可指定普通文件");
      const matcher = grep && !grep.literal ? RE2JS.compile(grep.pattern, grep.ignoreCase ? RE2JS.CASE_INSENSITIVE : 0) : undefined;
      const regexSize = matcher?.programSize() ?? 0;
      if (regexSize > 10000) throw new Error("正则表达式过于复杂，请简化 pattern 或使用 literal");
      const literal = grep?.ignoreCase ? grep.pattern.toLowerCase() : grep?.pattern;
      const pattern = (grep ? grep.glob : request.pattern)?.replaceAll("\\", "/");
      const globMatcher = pattern ? createGlobMatcher(pattern) : undefined;
      const pending = [root];
      const output: string[] = [];
      let count = 0;
      let visited = 0;
      let skipped = 0;
      let skippedLines = 0;
      let regexWork = 0;
      let batchWork = 0;
      let inputBytes = 0;
      let outputBytes = 0;
      let notice = "";
      const deadline = Date.now() + 30000;
      const append = (line: string) => {
        const text = line.length > 2000 ? `${line.slice(0, 2000)}…（此行已截断）` : line;
        outputBytes += Buffer.byteLength(text) + 1;
        if (outputBytes > 50 * 1024) {
          notice = "结果达到 50 KiB 上限，请缩小搜索范围";
          return false;
        }
        output.push(text);
        return true;
      };
      // ACT: 复用文件入口逐项授权，不使用会自行访问磁盘的 rg/fd；最多遍历 20000 项、30 秒。
      while (pending.length && !notice) {
        signal?.throwIfAborted();
        if (++visited > 20000 || Date.now() >= deadline) {
          notice = "搜索达到遍历或时间上限，请缩小 path";
          break;
        }
        const path = pending.pop()!;
        let entry;
        try { entry = await files.stat(path); }
        catch (error) {
          const failure = error as NodeJS.ErrnoException & { status?: number };
          if (failure.code !== "ENOENT" && failure.status !== 403) throw error;
          skipped++;
          continue;
        }
        if (entry.isDirectory()) {
          const entries = (await files.readdir(path, false, signal)).filter(item => item !== ".git" && item !== "node_modules").sort();
          if (visited + pending.length + entries.length > 20000) {
            notice = "搜索目录包含过多项目，请缩小 path";
            break;
          }
          for (const entry of entries.reverse()) pending.push(join(path, entry));
          continue;
        }
        if (!entry.isFile()) { skipped++; continue; }
        const matchPath = info.isDirectory() ? relative(root, path).replaceAll("\\", "/") : basename(path);
        if (globMatcher && !globMatcher.test(pattern!.includes("/") ? matchPath : basename(path))) continue;
        const displayPath = relative(cwd, path).replaceAll("\\", "/");
        if (!grep) {
          if (!append(displayPath)) break;
          count++;
        } else {
          if (entry.size > 8 * 1024 * 1024) { skipped++; continue; }
          if (inputBytes + entry.size > 64 * 1024 * 1024) {
            notice = "搜索达到 64 MiB 读取上限，请缩小 path 或 glob";
            break;
          }
          // readOnly=false 仅允许工作区；流读取防止 stat 后文件增长突破容量上限。
          const maxBytes = Math.min(8 * 1024 * 1024, 64 * 1024 * 1024 - inputBytes);
          let content: Buffer;
          try { content = await files.readFile(path, false, { signal, maxBytes }); }
          catch (error) {
            if ((error as NodeJS.ErrnoException).code !== "EFBIG") throw error;
            inputBytes += maxBytes + 1;
            if (inputBytes >= 64 * 1024 * 1024) {
              notice = "搜索达到 64 MiB 读取上限，请缩小 path 或 glob";
              break;
            }
            skipped++;
            continue;
          }
          inputBytes += content.byteLength;
          if (inputBytes > 64 * 1024 * 1024) {
            notice = "搜索达到 64 MiB 读取上限，请缩小 path 或 glob";
            break;
          }
          if (content.byteLength > 8 * 1024 * 1024 || content.subarray(0, 8192).includes(0)) { skipped++; continue; }
          const lines = content.toString("utf8").split(/\r\n|\n|\r/);
          let lastOutput = -1;
          for (let index = 0; index < lines.length; index++) {
            if (index % 256 === 0 || batchWork >= 2000000) {
              await new Promise<void>(resolve => setImmediate(resolve));
              batchWork = 0;
              signal?.throwIfAborted();
              if (Date.now() >= deadline) { notice = "搜索达到时间上限，请缩小范围"; break; }
            }
            const line = lines[index]!;
            // ACT: RE2 的工作量仍与状态数×行长相关；限制单行/累计成本，更大搜索需可终止的 worker。
            const work = regexSize * Math.max(1, line.length);
            if (work > 2000000) { skippedLines++; continue; }
            regexWork += work;
            batchWork += work;
            if (regexWork > 50000000) { notice = "搜索达到正则工作量上限，请缩小范围或使用 literal"; break; }
            if (!(matcher ? matcher.test(line) : (grep.ignoreCase ? line.toLowerCase() : line).includes(literal!))) continue;
            count++;
            for (let row = Math.max(lastOutput + 1, index - grep.context); row <= Math.min(lines.length - 1, index + grep.context); row++) {
              if (!append(`${displayPath}:${row + 1}: ${lines[row]}`)) break;
              lastOutput = row;
            }
            if (notice || count >= request.limit) break;
          }
        }
        if (count >= request.limit) notice = `结果达到 ${request.limit} 条上限，可缩小范围或提高 limit`;
      }
      signal?.throwIfAborted();
      const text = output.length ? output.join("\n") : "未找到匹配项";
      const notes = [notice, skipped ? `跳过 ${skipped} 项符号链接、特殊文件、二进制、过大或已删除的文件` : "",
        skippedLines ? `跳过 ${skippedLines} 行超出正则工作量上限的内容，可使用 literal 或简化 pattern` : ""].filter(Boolean);
      return {
        content: [{ type: "text", text: `${text}${notes.length ? `\n\n[${notes.join("；")}]` : ""}` }],
        details: { count, visited, skipped, skippedLines, truncated: !!notice || skippedLines > 0 },
      };
    },
  }));
}
