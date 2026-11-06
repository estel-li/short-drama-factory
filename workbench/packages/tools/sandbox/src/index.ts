import { z } from "zod";
import type { ToolPlugin } from "@toonflow/tools-scaffold/runtime";
import { sandboxRequestSchema } from "./schema";

const configSchema = z.object({}).strict();

const plugin: ToolPlugin = {
  validateConfig: config => configSchema.parse(config),
  createTools({ config, sandbox }) {
    configSchema.parse(config);
    if (!sandbox) return [];
    return [{
      name: "sandbox",
      label: "代码沙盒",
      description: "在独立的内存文件系统中执行 Bash、JavaScript（js-exec）和 Python（python3）。工作目录为 /workspace，通过 files 创建文本文件或 imports 导入指定文件；仅成功执行后按 exports 写回工作区，默认不覆盖。返回退出码和输出。环境禁网，JavaScript 不提供完整 Node.js API，Python 不支持 pip 或本机程序。",
      promptSnippet: "在隔离的内存环境中运行技能的 JS/Python 脚本，并显式导入和导出文件。",
      promptGuidelines: [
        "执行技能附带代码前，先读取技能说明，确认需要的脚本、输入文件和依赖。用 imports 导入需要的文件；沙盒不会自动读取脚本相邻文件。",
        "脚本使用 js-exec script.js 或 python3 script.py；JS 含 import/export 时使用 js-exec -m script.js。支持的 fs API 只访问虚拟文件系统。导入和导出文件总大小分别最多 16 MiB，文本输出最多 64 KiB。",
        "每次调用都是全新的 /workspace；需要保留的结果必须显式指定 exports，后续调用需重新导入。覆盖工作区文件前确认用户意图，并显式设置 overwrite=true。",
        "JavaScript 使用 QuickJS，Python 仅提供随附标准库；不支持完整 Node.js、pip、本机程序或联网。遇到缺失依赖应说明限制，不将沙盒成功运行等同于完整技能验证。",
      ],
      parameters: z.toJSONSchema(sandboxRequestSchema, { io: "input", target: "draft-07" }),
      executionMode: "sequential",
      execute(id, params, signal, onUpdate, context) {
        signal?.throwIfAborted();
        return sandbox.execute(id, sandboxRequestSchema.parse(params), signal, onUpdate, context);
      },
    }];
  },
};

export default plugin;
