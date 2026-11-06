import { z } from "zod";

export const factoryId = z.string().regex(/^[a-zA-Z0-9_-]{1,100}$/);
const requestKey = z.string().regex(/^[a-zA-Z0-9_-]{1,120}$/);
const revision = z.string().min(1).max(200);
const jsonObject = z.record(z.string(), z.json());
const mode = z.enum(["auto", "T2VA", "I2VA", "FL2VA", "L2VA", "Ref2VA"]);
const bindings = z.object({
  first_frame: z.string().min(1).optional().describe("importReference 返回的真实 asset.id；不是工作区文件路径或自行编造的 ID"),
  last_frame: z.string().min(1).optional(),
}).catchall(z.json());
const storyShot = z.object({
  id: z.number().int().positive(),
  uid: z.string().regex(/^[a-zA-Z0-9_-]{1,80}$/).optional(),
  scene: z.string().optional(), summary: z.string().optional(), action: z.string().optional(), camera: z.string().optional(),
  duration: z.number().min(4).max(15),
  prompt: z.string().trim().min(1).max(40000).describe("由当前 AI 编写的完整 H3 画面及声音提示词，不能留空或填写 probe"),
  mode: mode.optional(), bindings: bindings.optional(),
  characters: z.array(z.string()).optional(),
  use_previous_last_frame: z.boolean().optional(), first_frame_reason: z.string().max(1000).optional(),
  dialogue: z.array(z.object({ speaker: z.string().optional(), text: z.string().max(2000), narration: z.boolean().optional() })).optional(),
}).catchall(z.json());
export const shotChanges = storyShot.omit({ id: true, uid: true }).partial().refine(value => !Object.hasOwn(value, "uid") && !Object.hasOwn(value, "id"), "保留镜头 UID 和顺序；排序使用完整分镜");
export const createProjectBody = z.strictObject({
  input: z.string().max(50000).default(""),
  options: z.object({
    input_mode: z.literal("storyboard").default("storyboard"),
    execution_mode: z.enum(["auto", "review"]).optional(),
    duration_rule: z.enum(["total", "count", "manual"]).optional().describe("单镜 8 秒用 count、shot_count:1、total_seconds:8；manual 必须同时提供 manual_durations"),
    total_seconds: z.number().min(4).max(600).optional(), shot_seconds: z.number().min(4).max(15).optional(),
    shot_count: z.number().int().min(1).max(150).optional(), allow_long_shots: z.boolean().optional(),
    manual_durations: z.array(z.number().min(4).max(15)).min(1).max(150).optional(),
    ratio: z.string().optional(), style: z.string().optional(),
    profile: z.string().optional().describe("先 connectFactory 查询工作流名称，再 getWorkflowPlan 确认 ready:true；目录中出现不代表模型已安装"),
    h3_mode: mode.optional(), missing_reference: z.enum(["error", "text"]).optional(),
    auto_reference: z.literal(false).default(false), subtitles: z.boolean().optional(), narration: z.boolean().optional(), music: z.string().optional(),
  }).catchall(z.json()).refine(value => value.duration_rule !== "manual" || !!value.manual_durations?.length, "duration_rule 为 manual 时必须填写 manual_durations；单镜可使用 count、shot_count:1、total_seconds:镜头秒数"),
  storyboard: z.object({
    title: z.string().trim().min(1).max(200), aspect_ratio: z.string().optional(), style: z.string().optional(),
    characters: z.array(z.object({ id: z.string().regex(/^[a-zA-Z0-9_-]{1,40}$/), name: z.string().min(1).max(100), visual_description: z.string().min(1).max(4000), voice_description: z.string().optional() }).catchall(z.json())).optional(),
    scenes: z.array(jsonObject).optional(), props: z.array(jsonObject).optional(),
    shots: z.array(storyShot).min(1).max(150),
  }).catchall(z.json()).refine(value => !Object.hasOwn(value, "assets"), "参考图必须先通过 importReference 导入项目，再用真实 asset.id 更新镜头 bindings；不能在 storyboard.assets 中虚构素材"),
});
export const importReferenceBody = z.strictObject({ path: z.string().min(1).max(4096).describe("工作区内 PNG、JPEG、WebP 的相对路径，最多 8 MB") });
export const factoryRequest = z.discriminatedUnion("action", [
  z.strictObject({ action: z.literal("connect") }),
  z.strictObject({ action: z.literal("workflowPlan"), profile: factoryId }),
  z.strictObject({ action: z.literal("history") }),
  z.strictObject({ action: z.literal("retry"), requestKey }),
  z.strictObject({ action: z.literal("create"), requestKey, body: createProjectBody }),
  z.strictObject({ action: z.literal("importReference"), projectId: factoryId, requestKey, ...importReferenceBody.shape }),
  z.strictObject({ action: z.literal("read"), projectId: factoryId }),
  z.strictObject({ action: z.literal("updateShot"), projectId: factoryId, shotUid: factoryId, expectedRevision: revision, changes: shotChanges, requestKey }),
  z.strictObject({ action: z.literal("validate"), projectId: factoryId }),
  z.strictObject({ action: z.literal("compile"), projectId: factoryId, shotUid: factoryId, sections: z.record(z.string(), z.string().max(40000)) }),
  z.strictObject({ action: z.literal("plan"), projectId: factoryId, kind: z.enum(["render", "finish"]).default("render"), uids: z.array(factoryId).min(1).max(150).optional(), regenerate: z.boolean().default(false) }),
  z.strictObject({ action: z.literal("run"), projectId: factoryId, planId: z.string().regex(/^[a-f0-9]{64}$/), requestKey }),
  z.strictObject({ action: z.literal("job"), projectId: factoryId, jobId: factoryId, after: z.number().int().nonnegative().default(0) }),
  z.strictObject({ action: z.literal("resume"), projectId: factoryId, jobId: factoryId, expectedRevision: revision, requestKey }),
  z.strictObject({ action: z.literal("stop"), projectId: factoryId, jobId: factoryId, immediate: z.boolean().default(false), requestKey }),
  z.strictObject({ action: z.literal("delivery"), projectId: factoryId, verify: z.boolean().default(false) }),
  z.strictObject({ action: z.literal("importArtifact"), projectId: factoryId, relativePath: z.string().min(1).max(4096), sha256: z.string().regex(/^[a-f0-9]{64}$/) }),
]);
export type FactoryRequest = z.infer<typeof factoryRequest>;
export type FactoryShot = {
  uid: string; id: number; scene: string; summary: string; action: string; camera: string;
  duration: number; prompt: string; use_previous_last_frame: boolean; mode: z.infer<typeof mode>;
  [key: string]: unknown;
};
export type FactoryProject = {
  id: string; title: string; revision: string; settings: Record<string, unknown>;
  story: { title: string; shots: FactoryShot[]; [key: string]: unknown } | null;
  state: { status?: string; message?: string; current_stage?: string; shots_by_uid?: Record<string, Record<string, unknown>>; [key: string]: unknown };
};
export type FactoryPlan = {
  plan_id: string; ready: boolean; affected_uids: string[];
  blocked: { code: string; message?: string; field?: string }[];
  [key: string]: unknown;
};
export type FactoryReceipt = { id?: string; project_id?: string; job_id?: string; revision?: string; request_key?: string; [key: string]: unknown };
export type FactoryArtifact = { relative_path: string; sha256: string; size: number; mime: string; kind: string; api_url: string };
export type FactoryDelivery = {
  project_id: string; revision: string; fingerprint: string; ready_for_delivery: boolean;
  localManifestPath?: string;
  aliases: { original: FactoryArtifact | null; subtitled: FactoryArtifact | null };
  shot_clips: { uid: string; current_contract: boolean; artifact: FactoryArtifact | null }[];
  checks: Record<string, unknown>; artifacts: FactoryArtifact[];
};
export type FactoryJob = { id: string; project_id: string; status: string; message?: string; [key: string]: unknown };
