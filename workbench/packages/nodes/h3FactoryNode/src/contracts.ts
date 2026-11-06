import { z } from "zod";

export const factoryId = z.string().regex(/^[a-zA-Z0-9_-]{1,100}$/);
const requestKey = z.string().regex(/^[a-zA-Z0-9_-]{1,120}$/);
const revision = z.string().min(1).max(200);
const jsonObject = z.record(z.string(), z.json());
export const shotChanges = jsonObject.refine(value => !Object.hasOwn(value, "uid") && !Object.hasOwn(value, "id"), "保留镜头 UID 和顺序；排序使用完整分镜");
export const createProjectBody = z.strictObject({
  input: z.string().max(50000).default(""),
  options: jsonObject,
  storyboard: jsonObject,
});
export const factoryRequest = z.discriminatedUnion("action", [
  z.strictObject({ action: z.literal("connect") }),
  z.strictObject({ action: z.literal("history") }),
  z.strictObject({ action: z.literal("retry"), requestKey }),
  z.strictObject({ action: z.literal("create"), requestKey, body: createProjectBody }),
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
  duration: number; prompt: string; use_previous_last_frame: boolean; mode: string;
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
