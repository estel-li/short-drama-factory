import { createHash } from "node:crypto";
import { dirname, extname } from "node:path";
import { mkdir, readFile, readdir, writeAtomic } from "@toonflow/file";
import { factoryRequest, type FactoryRequest, type FactoryDelivery, type FactoryArtifact } from "@toonflow/node-h3-factory/contracts";
import { lockWorkspaceFiles, resolveWorkspacePath } from "@/utils/workspace/files";

import { localModelsConfig } from "@/utils/localModels";

type Journal = { request: FactoryRequest; instance: string; nodeId: string; createdAt: string; result?: unknown; status: "pending" | "completed" | "failed"; failure?: { message: string; status: number; factoryError?: unknown } };

function connection() {
  const { factoryUrl: address, applicationRoot: root } = localModelsConfig();
  if (!root) throw Object.assign(new Error("请在设置 → MiniMax H3 / ComfyUI 中填写实际运行的工厂目录"), { status: 503 });
  const url = new URL(address);
  if (!["http:", "https:"].includes(url.protocol) || !["127.0.0.1", "localhost", "[::1]"].includes(url.hostname)
    || url.username || url.password || url.search || url.hash || url.pathname !== "/") {
    throw new Error("SDF_BASE_URL 须为本机回环 HTTP(S) 地址；其他机器请使用已有的安全隧道");
  }
  return { baseUrl: url.origin, applicationRoot: root, identity: `${url.origin}\n${root.replaceAll("\\", "/").replace(/\/$/, "")}` };
}

async function requestJson(config: ReturnType<typeof connection>, path: string, method = "GET", body?: unknown, key?: string) {
  const response = await fetch(config.baseUrl + path, {
    method, headers: { "Content-Type": "application/json", ...(key ? { "Idempotency-Key": key } : {}) },
    body: body === undefined ? undefined : JSON.stringify(body), redirect: "error", signal: AbortSignal.timeout(90_000),
  });
  const value = await response.json() as Record<string, unknown>;
  if (!response.ok) {
    const message = typeof value.message === "string" ? value.message : `工厂请求失败（${response.status}）`;
    throw Object.assign(new Error(message), { status: response.status, factoryError: value });
  }
  return value;
}

async function verifyConnection(config: ReturnType<typeof connection>, directory: string) {
  const health = await requestJson(config, "/api/health");
  const normalize = (value: string) => value.replaceAll("\\", "/").replace(/\/$/, "");
  if (health.protocol_version !== 1 || typeof health.application_root !== "string"
    || normalize(health.application_root) !== normalize(config.applicationRoot)) {
    throw Object.assign(new Error("工厂实例目录或 agent 协议不匹配，已拒绝操作；请核对 SDF_APPLICATION_ROOT"), { status: 409 });
  }
  const capabilities = await requestJson(config, "/api/capabilities");
  const features = capabilities.features as Record<string, unknown> | undefined;
  for (const key of ["exact_jobs", "job_events", "execution_plans", "idempotency", "revisioned_edits", "strict_render", "delivery_manifest", "delivery_verification"]) {
    if (features?.[key] !== true) throw Object.assign(new Error(`工厂缺少能力：${key}`), { status: 409 });
  }
  const folder = await resolveWorkspacePath(directory, ".h3Factory", true);
  await mkdir(folder.path, { recursive: true });
  const path = (await resolveWorkspacePath(directory, ".h3Factory/connection.json")).path;
  try { await writeAtomic(path, JSON.stringify({ instance: config.identity }), { exclusive: true, mode: 0o600 }); }
  catch (error) { if ((error as NodeJS.ErrnoException).code !== "EEXIST") throw error; }
  if (JSON.parse(await readFile(path, "utf8")).instance !== config.identity) {
    throw Object.assign(new Error("此工作区绑定了另一工厂实例，请恢复原连接；连接新的 GPU 工厂时使用新工作区"), { status: 409 });
  }
  return { health, capabilities, baseUrl: config.baseUrl };
}

async function journalPath(directory: string, key: string) {
  const folder = await resolveWorkspacePath(directory, ".h3Factory/operations", true);
  await mkdir(folder.path, { recursive: true });
  return (await resolveWorkspacePath(directory, `.h3Factory/operations/${key}.json`)).path;
}

async function readJournal(path: string): Promise<Journal | undefined> {
  try { return JSON.parse(await readFile(path, "utf8")); }
  catch (error) { if ((error as NodeJS.ErrnoException).code === "ENOENT") return; throw error; }
}

async function importArtifact(directory: string, config: ReturnType<typeof connection>, projectId: string, relativePath: string, sha256: string) {
  const manifest = await requestJson(config, `/api/v2/projects/${projectId}/delivery`) as unknown as FactoryDelivery;
  const artifact = manifest.artifacts.find(item => item.relative_path === relativePath && item.sha256 === sha256);
  if (!artifact) throw Object.assign(new Error("产物已变化或不在交付清单中，请重新读取交付结果"), { status: 409 });
  const suffix = extname(artifact.relative_path).toLowerCase();
  const path = `assets/h3Factory/${projectId}/${artifact.sha256}${suffix}`;
  const target = await resolveWorkspacePath(directory, path, true);
  const release = lockWorkspaceFiles([target.path]);
  try {
    const existing = await readFile(target.path).catch((error: NodeJS.ErrnoException) => { if (error.code !== "ENOENT") throw error; });
    if (existing) verifyBytes(existing, artifact);
    else {
      // ACT: 三镜头原型单产物最多 512 MiB；更大成片需要流式校验导入。
      if (artifact.size > 512 * 1024 * 1024) throw new Error("单个产物超过 512 MiB，请使用工厂交付 CLI 下载");
      const relative = artifact.relative_path.split("/").map(encodeURIComponent).join("/");
      const response = await fetch(`${config.baseUrl}/api/v2/projects/${projectId}/delivery/files/${relative}`, { redirect: "error", signal: AbortSignal.timeout(120_000) });
      if (!response.ok) throw new Error(`下载工厂产物失败（${response.status}）`);
      const bytes = Buffer.from(await response.arrayBuffer());
      verifyBytes(bytes, artifact);
      await mkdir(dirname(target.path), { recursive: true });
      await resolveWorkspacePath(directory, path);
      await writeAtomic(target.path, bytes, { exclusive: true });
    }
    return { url: path, mimeType: artifact.mime, sha256: artifact.sha256, size: artifact.size };
  } finally { release(); }
}

function verifyBytes(bytes: Uint8Array, artifact: FactoryArtifact) {
  if (bytes.byteLength !== artifact.size || createHash("sha256").update(bytes).digest("hex") !== artifact.sha256) {
    throw new Error("产物大小或 SHA256 不匹配，未采用此文件");
  }
}

async function dispatch(directory: string, config: ReturnType<typeof connection>, input: FactoryRequest): Promise<unknown> {
  const projectId = "projectId" in input ? input.projectId : "";
  const projectPath = `/api/v2/projects/${projectId}`;
  if ("jobId" in input) {
    const job = await requestJson(config, `/api/jobs/${input.jobId}`);
    if (job.project_id !== projectId) throw Object.assign(new Error("任务不属于当前工厂项目"), { status: 409 });
  }
  switch (input.action) {
    case "create": return requestJson(config, "/api/v2/projects", "POST", input.body, input.requestKey);
    case "read": return requestJson(config, projectPath);
    case "updateShot": return requestJson(config, projectPath, "PATCH", { expected_revision: input.expectedRevision, shots: [{ uid: input.shotUid, changes: input.changes }] }, input.requestKey);
    case "validate": return requestJson(config, `${projectPath}/validate`, "POST", {});
    case "compile": return requestJson(config, `${projectPath}/shots/${input.shotUid}/compile`, "POST", { sections: input.sections });
    case "plan": return requestJson(config, `${projectPath}/plans`, "POST", { action: input.kind, internal_text: "forbid", ...(input.uids ? { uids: input.uids } : {}), regenerate: input.regenerate });
    case "run": return requestJson(config, `${projectPath}/run`, "POST", { plan_id: input.planId }, input.requestKey);
    case "job": return { job: await requestJson(config, `/api/jobs/${input.jobId}`), events: await requestJson(config, `/api/jobs/${input.jobId}/events?after=${input.after}`) };
    case "resume": return requestJson(config, `/api/v2/jobs/${input.jobId}/resume`, "POST", { expected_revision: input.expectedRevision }, input.requestKey);
    case "stop": return requestJson(config, `/api/v2/jobs/${input.jobId}/stop`, "POST", { immediate: input.immediate }, input.requestKey);
    case "delivery": {
      const manifest = await requestJson(config, `${projectPath}/delivery?verify=${input.verify}`);
      if (input.verify && typeof manifest.fingerprint === "string" && /^[a-f0-9]{64}$/.test(manifest.fingerprint)) {
        const relative = `deliveries/h3Factory/${projectId}/${manifest.fingerprint}/delivery.json`;
        const target = await resolveWorkspacePath(directory, relative, true);
        await mkdir(dirname(target.path), { recursive: true });
        await resolveWorkspacePath(directory, relative);
        try { await writeAtomic(target.path, JSON.stringify(manifest, null, 2), { exclusive: true }); }
        catch (error) { if ((error as NodeJS.ErrnoException).code !== "EEXIST") throw error; }
        return { ...manifest, localManifestPath: relative };
      }
      return manifest;
    }
    case "importArtifact": return importArtifact(directory, config, projectId, input.relativePath, input.sha256);
    default: throw new Error("不支持的工厂操作");
  }
}

export async function executeFactory(directory: string, nodeId: string, input: FactoryRequest): Promise<unknown> {
  const config = connection();
  if (input.action === "history") {
    const folder = dirname(await journalPath(directory, "history"));
    const names = (await readdir(folder, { withFileTypes: true })).filter(item => item.isFile() && /^[a-zA-Z0-9_-]+\.json$/.test(item.name));
    const journals = await Promise.all(names.map(async item => readJournal((await resolveWorkspacePath(directory, `.h3Factory/operations/${item.name}`)).path)));
    return journals.filter((item): item is Journal => Boolean(item && item.nodeId === nodeId && item.instance === config.identity))
      .sort((a, b) => b.createdAt.localeCompare(a.createdAt)).slice(0, 50).map(item => ({
        createdAt: item.createdAt, status: item.status, result: item.result, failure: item.failure,
        request: { action: item.request.action, requestKey: "requestKey" in item.request ? item.request.requestKey : undefined },
      }));
  }
  if (input.action === "connect") return verifyConnection(config, directory);
  if (input.action === "retry") {
    const saved = await readJournal(await journalPath(directory, input.requestKey));
    if (!saved || saved.nodeId !== nodeId || saved.instance !== config.identity) throw Object.assign(new Error("找不到当前节点和实例的原请求"), { status: 404 });
    return executeFactory(directory, nodeId, factoryRequest.parse(saved.request));
  }
  if (!("requestKey" in input)) {
    await verifyConnection(config, directory);
    return dispatch(directory, config, input);
  }
  const path = await journalPath(directory, input.requestKey);
  const release = lockWorkspaceFiles([path]);
  try {
    let saved = await readJournal(path);
    if (saved && (saved.instance !== config.identity || saved.nodeId !== nodeId || JSON.stringify(saved.request) !== JSON.stringify(input))) {
      throw Object.assign(new Error("请求键已用于其他内容，请查询原请求，不要覆盖"), { status: 409 });
    }
    if (saved?.status === "completed") return saved.result;
    if (saved?.status === "failed" && saved.failure) throw Object.assign(new Error(saved.failure.message), saved.failure);
    if (!saved) {
      saved = { request: input, instance: config.identity, nodeId, createdAt: new Date().toISOString(), status: "pending" };
      await writeAtomic(path, JSON.stringify(saved, null, 2), { exclusive: true, mode: 0o600 });
    }
    // ACT: 超时仍保留原请求；只以同一请求键补交，由工厂回执防止重复生成。
    let result: unknown;
    try {
      await verifyConnection(config, directory);
      result = await dispatch(directory, config, input);
    } catch (cause) {
      const problem = cause as Error & { status?: number; factoryError?: unknown };
      if (problem.status && problem.status >= 400 && problem.status < 500 && problem.status !== 408 && problem.status !== 429) {
        await writeAtomic(path, JSON.stringify({ ...saved, status: "failed", failure: { message: problem.message, status: problem.status, factoryError: problem.factoryError } }, null, 2), { mode: 0o600 });
      }
      throw cause;
    }
    await writeAtomic(path, JSON.stringify({ ...saved, status: "completed", result }, null, 2), { mode: 0o600 });
    return result;
  } finally { release(); }
}
