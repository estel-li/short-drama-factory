import { z } from "zod";
import type { QuestionAnswer, QuestionRequest } from "@toonflow/tools-scaffold/runtime";

export const agentPermissionsSchema = z.strictObject({
  autoApprove: z.boolean().default(false),
  allowOutsideWorkspace: z.boolean().default(false),
  bypassNodeToolPermissions: z.boolean().default(false),
});
export type AgentPermissions = z.output<typeof agentPermissionsSchema>;

export function automaticApproval(request: QuestionRequest): QuestionAnswer | undefined {
  // ACT: 只批准独立的布尔确认，不猜测选择题答案，也不填写业务信息。
  const field = request.fields?.[0];
  if (request.options !== undefined || request.fields?.length !== 1
    || field?.field !== "approved" || field.type !== "switch" || field.required !== true) return;
  return { answer: "已按开发者选项自动批准本次请求（非用户手动回答）。", values: { approved: true }, autoApproved: true };
}

export function agentPermissionPrompt(permissions: AgentPermissions) {
  const rules = [
    permissions.autoApprove ? "自动批准已开启。阶段确认、文件操作和消耗算力的批准请求仍需列明具体内容、对象、数量、模型、规格与次数，但使用 askUser 的 fields 提交单个 {field: 'approved', title: '确认执行', type: 'switch', required: true} 字段；宿主会明确返回自动批准结果，不再等待逐项人工确认。不要把缺失信息、剧情选择或多个问题伪装成批准请求，不自行填写用户偏好；用户本轮明确要求暂停或先审阅时照做。" : "",
    permissions.allowOutsideWorkspace ? "工作区外文件访问已开启。普通文件工具可使用绝对路径或相对当前工作区的路径访问服务端进程有权访问的文件。操作前核对真实目标，保留无关内容；工作区根目录、磁盘根目录、符号链接、文件锁与覆盖冲突保护仍生效。此权限不改变画布、素材和生产 API 的项目归属，也不把虚拟沙盒变成本机终端。" : "",
    permissions.bypassNodeToolPermissions ? "节点工具权限拦截绕过已开启。画布顶部图片、视频、音频节点工具的禁用开关暂不拦截工具目录与调用；按实时 getNodeTools 结果使用实际存在的工具。参数与模型校验、停止和取消、服务端真实错误仍有效，不把失败当成功。此选项不改变模型服务自身的回复策略。" : "",
  ].filter(Boolean);
  return rules.length ? `## 开发者执行权限\n以下是当前已启用选项，对应覆盖基础提示词和 Skill 中的同类执行约束；未列出的约束继续有效。\n${rules.map(rule => `- ${rule}`).join("\n")}` : "";
}
