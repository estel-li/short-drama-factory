import { z } from "zod";
import { readFile } from "@toonflow/file";
import { parseSessionEntries, SessionManager } from "@earendil-works/pi-coding-agent";
import type { FileEntry } from "@earendil-works/pi-coding-agent";
import { getActiveAgentSession, getSubAgentInfo } from "@/agent/runtime/sessions";
import type { AgentSubAgent } from "@/agent/runtime/types";
import { thinkingLevels, type ThinkingLevel } from "@/lib/modelReasoning";
import { resolveWorkspacePath } from "@/utils/workspace/files";

const fileSchema = z.string().regex(/^[\w-]+\.jsonl$/, "Agent 会话标识无效");
const memberSchema = z.object({
  file: fileSchema,
  parentFile: fileSchema,
  name: z.string().min(1),
  task: z.string(),
  status: z.enum(["running", "completed", "error", "limited", "cancelled", "inputRequired"]),
  providerId: z.string().optional(),
  modelId: z.string().optional(),
  thinkingLevel: z.enum(thinkingLevels).optional(),
});
const headerSchema = z.object({ type: z.literal("session"), parentSession: fileSchema.optional() });
const entrySchema = z.object({ type: z.string(), id: z.string().min(1), parentId: z.string().nullable(), timestamp: z.string() });

export type AgentTeamMember = {
  file: string;
  parentFile?: string;
  name: string;
  task?: string;
  status: AgentSubAgent["status"] | "idle";
  providerId?: string;
  modelId?: string;
  thinkingLevel?: ThinkingLevel;
};

export async function getAgentTeam(cwd: string, file: string): Promise<{ selfFile: string; rootFile: string; members: AgentTeamMember[] }> {
  // ACT: 沿会话树读取成员，开销与团队历史总量成正比；成员很多时再维护独立索引。
  fileSchema.parse(file);

  async function readSession(currentFile: string) {
    fileSchema.parse(currentFile);
    const { path } = await resolveWorkspacePath(cwd, `.agent/sessions/${currentFile}`);
    const active = getActiveAgentSession(path);
    let entries: FileEntry[];
    if (active) {
      entries = [active.history.getHeader()!, ...active.history.getEntries()];
    } else {
      const content = await readFile(path, "utf8");
      entries = parseSessionEntries(content);
      // ACT: SDK 会跳过坏行；成员授权不能根据缺损的会话关系继续判断。
      if (entries.length !== content.split("\n").filter(line => line.trim()).length) throw new Error("Agent 会话记录损坏");
    }
    const header = headerSchema.parse(entries[0]);
    const ids = new Set<string>();
    for (const entry of entries.slice(1)) {
      const parsed = entrySchema.parse(entry);
      if (parsed.type === "session" || ids.has(parsed.id) || (parsed.parentId !== null && !ids.has(parsed.parentId))) {
        throw new Error("Agent 会话记录结构无效");
      }
      ids.add(parsed.id);
    }
    const history = SessionManager.inMemory(cwd, undefined, entries);
    const infoEntry = getSubAgentInfo(history);
    const info = infoEntry ? memberSchema.parse(infoEntry.data) : undefined;
    if (Boolean(header.parentSession) !== Boolean(info) || (info && (info.file !== currentFile || info.parentFile !== header.parentSession))) {
      throw new Error("子 Agent 的会话归属不一致");
    }
    const children = new Map<string, z.infer<typeof memberSchema>>();
    for (const entry of history.getEntries()) {
      if (entry.type !== "custom" || entry.customType !== "toonflowSubAgent") continue;
      const child = memberSchema.parse(entry.data);
      if (child.parentFile !== currentFile) throw new Error("子 Agent 的父会话记录不一致");
      children.set(child.file, child);
    }
    return { file: currentFile, path, history, info, parentFile: header.parentSession, children };
  }

  const snapshots = new Map<string, Awaited<ReturnType<typeof readSession>>>();
  async function getSession(currentFile: string) {
    const existing = snapshots.get(currentFile);
    if (existing) return existing;
    const session = await readSession(currentFile);
    snapshots.set(currentFile, session);
    return session;
  }

  let root = await getSession(file);
  const ancestors = new Set<string>();
  while (root.parentFile) {
    if (ancestors.has(root.file)) throw new Error("Agent 父会话关系存在循环");
    ancestors.add(root.file);
    const parent = await getSession(root.parentFile);
    if (!parent.children.has(root.file)) throw new Error("子 Agent 未登记在所属父会话中");
    root = parent;
  }

  const members: AgentTeamMember[] = [];
  const pending: { file: string; parentFile?: string; record?: z.infer<typeof memberSchema> }[] = [{ file: root.file }];
  const visited = new Set<string>();
  for (let index = 0; index < pending.length; index++) {
    const item = pending[index]!;
    if (visited.has(item.file)) throw new Error("Agent 子会话关系存在循环或重复登记");
    visited.add(item.file);
    const session = await getSession(item.file).catch((error: NodeJS.ErrnoException) => {
      if (item.parentFile && error.code === "ENOENT") return undefined;
      throw error;
    });
    if (!session) continue;
    if (session.parentFile !== item.parentFile) throw new Error("子 Agent 不属于当前会话树");
    const context = session.history.buildSessionContext();
    const reasoning = session.history.getBranch().findLast(entry => entry.type === "custom" && entry.customType === "toonflowReasoning");
    const selection = z.object({ thinkingLevel: z.enum(thinkingLevels).nullable() }).safeParse(reasoning?.type === "custom" ? reasoning.data : undefined);
    const record = item.record ?? session.info;
    const status = getActiveAgentSession(session.path) ? "running" : record?.status === "running" ? "cancelled" : record?.status ?? "idle";
    members.push({
      file: session.file,
      parentFile: session.parentFile,
      name: session.history.getSessionName() || record?.name || "主 Agent",
      task: record?.task,
      status,
      providerId: context.model?.provider ?? record?.providerId,
      modelId: context.model?.modelId ?? record?.modelId,
      thinkingLevel: selection.success ? selection.data.thinkingLevel ?? undefined : z.enum(thinkingLevels).optional().parse(context.thinkingLevel ?? record?.thinkingLevel),
    });
    for (const child of session.children.values()) pending.push({ file: child.file, parentFile: session.file, record: child });
  }
  if (!members.some(member => member.file === file)) throw new Error("当前 Agent 不属于此会话树");
  return { selfFile: file, rootFile: root.file, members };
}
