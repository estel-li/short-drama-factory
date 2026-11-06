<template>
  <nodeSkeleton v-bind="nodeProps" :style="{ width: '430px' }">
    <section class="factoryPanel nodrag nopan nowheel" @pointerdown.stop @keydown.stop>
      <div class="statusRow"><strong>{{ data.shotUid ? `H3 镜头 ${shot?.id ?? ''}` : 'H3 项目' }}</strong><span>{{ statusLabel }}</span></div>
      <p v-if="message" class="message" role="status">{{ message }}</p>
      <div v-if="errorText" class="error" role="alert">{{ errorText }}</div>
      <div v-if="!data.projectId" class="setup">
        <label>已有工厂项目 ID<el-input v-model="projectInput" aria-label="工厂项目 ID" /></label>
        <el-button :disabled="busy || !projectInput" @click="ui(() => bindProject(projectInput))">连接项目</el-button>
        <label>分镜请求 JSON<el-input v-model="data.createText" type="textarea" :rows="7" aria-label="分镜请求 JSON" /></label>
        <input type="file" accept="application/json,.json" aria-label="导入分镜请求" @change="readProjectFile" />
        <el-button :disabled="busy || !data.createText" @click="ui(createFromText)">创建工厂项目</el-button>
      </div>
      <template v-else>
        <p class="identity">{{ project?.title ?? data.projectId }}<br /><small>{{ data.projectId }}<template v-if="data.shotUid"> / {{ data.shotUid }}</template></small></p>
        <div class="actions">
          <el-button :disabled="busy" @click="ui(() => refreshProject(true))">重新读取</el-button>
          <el-button v-if="!data.shotUid" :disabled="busy || !project?.story" @click="ui(expandShots)">展开镜头画布</el-button>
          <el-button :disabled="busy" @click="ui(readHistory)">提交记录</el-button>
        </div>
        <template v-if="data.shotUid && data.draft">
          <label>镜头概要<el-input :disabled="busy" v-model="data.draft.summary" aria-label="镜头概要" /></label>
          <label>场景<el-input :disabled="busy" v-model="data.draft.scene" aria-label="镜头场景" /></label>
          <label>动作<el-input :disabled="busy" v-model="data.draft.action" type="textarea" :rows="2" aria-label="镜头动作" /></label>
          <label>机位<el-input :disabled="busy" v-model="data.draft.camera" aria-label="镜头机位" /></label>
          <div class="statusRow"><label>秒数 <el-input-number :disabled="busy" v-model="data.draft.duration" :min="4" :max="15" :step="1" aria-label="镜头时长" /></label></div>
          <el-checkbox :disabled="busy" v-model="data.draft.use_previous_last_frame">接续紧邻前镜的真实末帧</el-checkbox>
          <label>完整 H3 提示词<el-input :disabled="busy" v-model="data.draft.prompt" type="textarea" :rows="7" aria-label="H3 提示词" /></label>
          <el-button :disabled="busy || activeJob" @click="ui(saveDraft)">保存镜头修改</el-button>
        </template>
        <ol v-else-if="project?.story" class="shotList"><li v-for="item in project.story.shots" :key="item.uid">{{ item.summary || item.scene }} <small>{{ item.duration }} 秒{{ item.use_previous_last_frame ? ' · 末帧接续' : '' }}</small></li></ol>
        <div class="actions">
          <el-button :disabled="busy || activeJob" @click="ui(() => makePlan('render'))">{{ data.shotUid ? '计划此镜' : '计划整片' }}</el-button>
          <el-button v-if="!data.shotUid" :disabled="busy || activeJob" @click="ui(() => makePlan('finish'))">计划成片后期</el-button>
          <el-button v-if="data.plan" type="primary" :disabled="busy || activeJob || !data.plan.ready || hasUnsavedDraft" @click="ui(() => runPlan(data.plan!.plan_id))">执行此计划</el-button>
        </div>
        <div v-if="data.plan" class="planSummary">
          <strong>{{ data.plan.ready ? '分镜校验通过' : '计划有阻塞项' }} · 影响 {{ data.plan.affected_uids?.length ?? 0 }} 镜</strong>
          <ul><li v-for="uid in data.plan.affected_uids" :key="uid">{{ project?.story?.shots.find(item => item.uid === uid)?.summary || uid }}</li></ul>
          <p v-for="item in data.plan.blocked" :key="`${item.code}:${item.field}`" class="error">{{ item.message || item.code }}</p>
          <p v-for="(item, index) in planWarnings" :key="index" class="message">{{ item }}</p>
          <details class="details"><summary>执行计划详情</summary><pre>{{ JSON.stringify(data.plan, null, 2) }}</pre></details>
        </div>
        <div v-if="data.jobId" class="job">
          <small>任务 {{ data.jobId }}</small>
          <p>{{ job?.message ?? project?.state.message }}</p>
          <div class="actions">
            <el-button :disabled="busy" @click="ui(pollJob)">刷新进度</el-button>
            <el-button :disabled="busy || !activeJob" @click="ui(() => stopJob(false))">请求停止</el-button>
            <el-button :disabled="busy || activeJob || job?.status === 'done'" @click="ui(resumeJob)">续跑原任务</el-button>
          </div>
        </div>
        <div class="actions"><el-button :disabled="busy || activeJob" @click="ui(syncMedia)">{{ data.shotUid ? '读取镜头结果' : '校验并取回成片' }}</el-button></div>
        <video v-if="previewUrl" :src="previewUrl" controls preload="metadata" aria-label="H3 生成结果" />
        <details v-if="delivery" class="details"><summary>{{ delivery.ready_for_delivery ? '技术交付检查通过' : '交付检查详情' }}</summary><pre>{{ JSON.stringify(delivery.checks, null, 2) }}</pre></details>
      </template>
      <div v-if="data.pendingKey" class="pending"><p>保留的请求：{{ data.pendingKey }}</p><el-button :disabled="busy" @click="ui(() => retryRequest(data.pendingKey!))">复查／补交原请求</el-button></div>
      <details v-if="history.length" class="details" open><summary>持久提交记录</summary><div v-for="item in history" :key="item.request.requestKey" class="historyItem"><small>{{ item.createdAt }} · {{ item.request.action }} · {{ item.status }}</small><el-button :disabled="busy" size="small" @click="ui(() => retryRequest(item.request.requestKey))">读取回执</el-button></div></details>
      <p class="footnote">生成由本地 H3 工厂执行；关闭画布不会取消已提交的任务。</p>
    </section>
  </nodeSkeleton>
</template>

<script setup lang="ts">
import { computed, nextTick, onScopeDispose, ref, watch } from "vue";
import { useVueFlow } from "@vue-flow/core";
import { IconMovie } from "@tabler/icons-vue";
import { ElButton, ElInput, ElInputNumber, ElCheckbox } from "element-plus";
import { nodeSkeleton, useNode, nodeTools, z, validateConnection, type NodeHandle, type NodeOutputs, type NodeMediaValue } from "@toonflow/nodes-scaffold/runtime";
import { createProjectBody, importReferenceBody, factoryId, shotChanges, type FactoryProject, type FactoryShot, type FactoryPlan, type FactoryReceipt, type FactoryDelivery, type FactoryJob, type FactoryRequest } from "./contracts";

defineOptions({
  inheritAttrs: false,
  icon: IconMovie,
  handles: [
    { id: "projectIn", type: "target", dataType: "STRING", label: "工厂项目" },
    { id: "previous", type: "target", dataType: "STRING", label: "紧邻前镜" },
    { id: "project", type: "source", dataType: "STRING", label: "工厂项目" },
    { id: "shot", type: "source", dataType: "STRING", label: "镜头身份／接续" },
    { id: "video", type: "source", dataType: "VIDEO", label: "已采用视频" },
    { id: "report", type: "source", dataType: "FILE", label: "交付检查清单" },
  ] satisfies NodeHandle[],
});
type ShotDraft = Pick<FactoryShot, "scene" | "summary" | "action" | "camera" | "duration" | "prompt" | "use_previous_last_frame"> & { revision: string };
type NodeData = {
  projectId?: string; shotUid?: string; createText?: string; draft?: ShotDraft; plan?: FactoryPlan;
  jobId?: string; pendingKey?: string; previousUid?: string; eventCursor?: number; sourceRevision?: string; sourceShotUid?: string;
};
type JournalView = { createdAt: string; status: string; request: { action: string; requestKey: string }; result?: FactoryReceipt };

const { id, node, nodeProps, outputs, files, nodeEvent } = useNode({ label: "本地 H3 工厂", outputs: {} as NodeOutputs });
const flow = useVueFlow();
const data = computed(() => node.data as NodeData);
const project = ref<FactoryProject>();
const shot = computed(() => project.value?.story?.shots.find(item => item.uid === data.value.shotUid));
const hasUnsavedDraft = computed(() => draftChanged(data.value.draft, shot.value));
const job = ref<FactoryJob>();
const activeJob = computed(() => Boolean(job.value && ["queued", "running"].includes(job.value.status)));
const statusLabel = computed(() => {
  const value = job.value?.status ?? project.value?.state.status;
  const labels: Record<string, string> = { ready: "待生成", queued: "排队中", running: "执行中", done: "任务阶段结束", paused: "已暂停", error: "执行失败", review: "待检查", complete: "成片已完成" };
  if (outputs.value.video?.dataType === "VIDEO" && !activeJob.value) return data.value.shotUid ? "镜头已取回" : "成片已取回";
  return value ? labels[value] ?? value : "未连接";
});
const delivery = ref<FactoryDelivery>();
const history = ref<JournalView[]>([]);
const planWarnings = computed(() => Array.isArray(data.value.plan?.warnings) ? data.value.plan.warnings.map(item => typeof item?.message === "string" ? item.message : "") : []);
const busy = ref(false);
const errorText = ref("");
const message = ref("");
const projectInput = ref("");
const previewUrl = files.useFileUrl(computed(() => outputs.value.video?.dataType === "VIDEO" ? outputs.value.video.value : undefined), fail);
let directory: Promise<string> | undefined;
let disposed = false;
let polling = false;
let timer: ReturnType<typeof setTimeout> | undefined;

function fail(error: unknown) { errorText.value = error instanceof Error ? error.message : String(error); }

function ui(action: () => Promise<unknown>) { void perform(action).catch(() => {}); }

async function perform<T>(action: () => Promise<T>) {
  if (busy.value) throw new Error("当前节点正在操作，请稍后再试");
  busy.value = true;
  errorText.value = "";
  try { return await action(); }
  catch (error) { fail(error); throw error; }
  finally { busy.value = false; }
}

async function factory<T = Record<string, unknown>>(request: FactoryRequest): Promise<T> {
  directory ??= files.getWorkspaceFiles().list().then(value => value.directory);
  const response = await fetch("/api/h3Factory/execute", {
    method: "POST", headers: { "Content-Type": "application/json", "x-toonflow-workspace": "1" },
    body: JSON.stringify({ directory: await directory, nodeId: id, request }), signal: AbortSignal.timeout(130_000),
  });
  const result = await response.json();
  if (!response.ok || result.code !== 200) {
    const details = result.data?.details;
    throw Object.assign(new Error(`${result.message || "工厂请求失败"}${details?.length ? `\n${JSON.stringify(details)}` : ""}`), { status: response.status, details: result.data });
  }
  return result.data as T;
}

function requestKey() {
  if (data.value.pendingKey) throw new Error("还有未确认的提交，请先复查原请求");
  return `h3_${crypto.randomUUID()}`;
}

async function mutate(request: FactoryRequest & { requestKey: string }) {
  if (data.value.pendingKey && data.value.pendingKey !== request.requestKey) throw new Error("还有未确认的提交，请先复查原请求，不能换请求键再次提交");
  data.value.pendingKey = request.requestKey;
  try {
    const receipt = await factory<FactoryReceipt>(request);
    adoptReceipt(receipt);
    data.value.pendingKey = undefined;
    return receipt;
  } catch (error) {
    if (submissionRejected(error)) data.value.pendingKey = undefined;
    throw error;
  }
}

function submissionRejected(error: unknown) {
  const problem = error as { status?: number; details?: { code?: string } };
  return Boolean(problem.status && problem.status >= 400 && problem.status < 500 && problem.status !== 408 && problem.status !== 429 && problem.details?.code !== "EBUSY");
}

function adoptReceipt(receipt: FactoryReceipt) {
  if (receipt.id && data.value.projectId && receipt.id !== data.value.projectId) throw new Error("回执不属于当前项目，未切换任务");
  if (!data.value.projectId && receipt.id) data.value.projectId = receipt.id;
  if (receipt.job_id) {
    if (data.value.jobId !== receipt.job_id) data.value.eventCursor = 0;
    data.value.jobId = receipt.job_id;
    job.value = undefined;
    schedulePoll();
  }
}

function draftChanged(draft: ShotDraft | undefined, saved: FactoryShot | undefined) {
  if (!draft || !saved) return false;
  const { revision: _revision, ...fields } = draft;
  return Object.entries(fields).some(([key, value]) => value !== saved[key]);
}

function publishIdentity() {
  if (!data.value.projectId) return;
  outputs.value.project = { dataType: "STRING", value: JSON.stringify({ kind: "h3Project", projectId: data.value.projectId }) };
  outputs.value.shot = data.value.shotUid ? { dataType: "STRING", value: JSON.stringify({ kind: "h3Shot", projectId: data.value.projectId, shotUid: data.value.shotUid }) } : undefined;
}

async function refreshProject(loadDraft = false) {
  if (!data.value.projectId) return;
  const pid = data.value.projectId;
  const previousShot = shot.value;
  const value = await factory<FactoryProject>({ action: "read", projectId: pid });
  if (disposed || pid !== data.value.projectId) return;
  // 未保存草稿也会随画布持久化；首次读取没有旧镜头，不能据此覆盖草稿。
  const preserveDraft = Boolean(data.value.draft && (!previousShot || draftChanged(data.value.draft, previousShot)));
  project.value = value;
  publishIdentity();
  if (data.value.shotUid && !shot.value) throw new Error("绑定的镜头已不存在，请重新展开项目画布");
  if (shot.value && (loadDraft || !data.value.draft || !preserveDraft)) {
    const { scene, summary, action, camera, duration, prompt, use_previous_last_frame } = shot.value;
    data.value.draft = { scene, summary, action, camera, duration, prompt: prompt ?? "", use_previous_last_frame, revision: value.revision };
  }
  return value;
}

async function bindProject(projectId: string, shotUid?: string) {
  factoryId.parse(projectId);
  if (shotUid) factoryId.parse(shotUid);
  if (data.value.projectId && (data.value.projectId !== projectId || data.value.shotUid !== shotUid)) throw new Error("已绑定节点不能改指其他项目或镜头，请新增节点");
  const value = await factory<FactoryProject>({ action: "read", projectId });
  if (shotUid && !value.story?.shots.some(item => item.uid === shotUid)) throw new Error("项目中没有此镜头");
  data.value.projectId = projectId;
  data.value.shotUid = shotUid;
  return refreshProject(true);
}

async function createProject(body: z.infer<typeof createProjectBody>, key: string) {
  if (data.value.projectId) throw new Error("节点已绑定项目，请新增项目节点");
  const receipt = await mutate({ action: "create", body, requestKey: key });
  await refreshProject(true);
  return receipt;
}

async function createFromText() { return createProject(createProjectBody.parse(JSON.parse(data.value.createText || "")), requestKey()); }

async function readProjectFile(event: Event) {
  const file = (event.target as HTMLInputElement).files?.[0];
  if (!file) return;
  try {
    if (file.size > 2 * 1024 * 1024) throw new Error("分镜 JSON 不能超过 2 MiB");
    const text = await file.text();
    createProjectBody.parse(JSON.parse(text));
    data.value.createText = text;
  } catch (error) { fail(error); }
}

function boundProject() {
  if (!data.value.projectId) throw new Error("请先连接或创建工厂项目");
  return data.value.projectId;
}

function checkPrevious(value: FactoryProject, continuation: boolean) {
  if (!continuation) return;
  const index = value.story?.shots.findIndex(item => item.uid === data.value.shotUid) ?? -1;
  const previous = value.story?.shots[index - 1];
  if (!previous) throw new Error("首镜不能使用前镜末帧");
  if (data.value.previousUid && previous.uid !== data.value.previousUid) throw new Error("接续连线必须来自同一项目的紧邻前镜");
}

async function updateShot(changes: z.infer<typeof shotChanges>, expectedRevision: string, key: string) {
  if (!data.value.shotUid) throw new Error("请在具体镜头节点中修改");
  const value = await refreshProject();
  if (value) checkPrevious(value, changes.use_previous_last_frame === true || (changes.use_previous_last_frame === undefined && Boolean(shot.value?.use_previous_last_frame)));
  const receipt = await mutate({ action: "updateShot", projectId: boundProject(), shotUid: data.value.shotUid, expectedRevision, changes, requestKey: key });
  data.value.plan = undefined;
  outputs.value.video = undefined;
  outputs.value.report = undefined;
  delivery.value = undefined;
  await refreshProject(true);
  for (const candidate of flow.getNodes.value) {
    if (candidate.id !== id && candidate.type === node.type && candidate.data?.projectId === data.value.projectId) {
      candidate.data.sourceShotUid = data.value.shotUid;
      candidate.data.sourceRevision = receipt.revision;
    }
  }
  return receipt;
}

async function saveDraft() {
  if (!data.value.draft) throw new Error("请先读取镜头");
  const { revision, ...changes } = data.value.draft;
  return updateShot({ ...changes, mode: changes.use_previous_last_frame ? "I2VA" : shot.value?.use_previous_last_frame ? "auto" : shot.value?.mode ?? "auto" }, revision, requestKey());
}

async function makePlan(kind: "render" | "finish", regenerate = false) {
  if (kind === "finish" && data.value.shotUid) throw new Error("成片后期请在项目节点执行");
  if (draftChanged(data.value.draft, shot.value)) throw new Error("镜头有未保存修改，请先保存再计划");
  const current = await refreshProject();
  if (current && data.value.shotUid) checkPrevious(current, Boolean(shot.value?.use_previous_last_frame));
  const plan = await factory<FactoryPlan>({ action: "plan", projectId: boundProject(), kind, regenerate, ...(data.value.shotUid ? { uids: [data.value.shotUid] } : {}) });
  data.value.plan = plan;
  message.value = plan.ready ? "分镜与执行范围已校验；模型及 GPU 可用性另见计划中的环境提示。" : "请先解决计划列出的阻塞项。";
  return plan;
}

async function runPlan(planId: string, key = requestKey()) {
  if (hasUnsavedDraft.value) throw new Error("镜头有未保存修改，请先保存并重新计划");
  if (data.value.plan?.plan_id !== planId || !data.value.plan.ready) throw new Error("请先读取本节点的可执行计划");
  const receipt = await mutate({ action: "run", projectId: boundProject(), planId, requestKey: key });
  await pollJob();
  return receipt;
}

async function pollJob() {
  if (!data.value.jobId) throw new Error("此节点没有任务，请读取提交记录");
  const jobId = data.value.jobId;
  const result = await factory<{ job: FactoryJob; events: { items: unknown[]; next_cursor: number } }>({ action: "job", projectId: boundProject(), jobId, after: data.value.eventCursor ?? 0 });
  if (disposed || data.value.jobId !== jobId) return result;
  if (!disposed) { job.value = result.job; data.value.eventCursor = result.events.next_cursor; await refreshProject(); }
  if (activeJob.value || result.events.items.length === 100) schedulePoll();
  return result;
}

function schedulePoll() {
  if (timer) clearTimeout(timer);
  if (disposed) return;
  timer = setTimeout(async () => {
    if (busy.value || polling) { schedulePoll(); return; }
    polling = true;
    try { await pollJob(); }
    catch (error) { fail(error); message.value = "观察中断，任务身份已保留；恢复连接后刷新进度。"; }
    finally { polling = false; }
  }, 5000);
}

async function resumeJob(key = requestKey()) {
  if (!data.value.jobId) throw new Error("没有可续跑的原任务");
  const value = await refreshProject();
  if (!value) throw new Error("无法读取项目版本");
  const receipt = await mutate({ action: "resume", projectId: boundProject(), jobId: data.value.jobId, expectedRevision: value.revision, requestKey: key });
  await pollJob();
  return receipt;
}

async function stopJob(immediate: boolean, key = requestKey()) {
  if (!data.value.jobId) throw new Error("没有可停止的任务");
  const receipt = await mutate({ action: "stop", projectId: boundProject(), jobId: data.value.jobId, immediate, requestKey: key });
  await pollJob();
  return receipt;
}

async function readHistory() {
  history.value = await factory<JournalView[]>({ action: "history" });
  return history.value;
}

async function restoreNode() {
  const records = await factory<JournalView[]>({ action: "history" });
  if (disposed) return;
  const pending = records.find(item => item.status === "pending");
  const created = records.find(item => item.status === "completed" && item.request.action === "create");
  if (!data.value.projectId && created?.result) adoptReceipt(created.result);
  const submitted = records.find(item => item.status === "completed" && ["run", "resume"].includes(item.request.action) && item.result?.job_id && item.result.id === data.value.projectId);
  if (submitted?.result && submitted.result.job_id !== data.value.jobId) adoptReceipt(submitted.result);
  if (!data.value.pendingKey && pending) data.value.pendingKey = pending.request.requestKey;
  if (disposed) return;
  await refreshProject();
  if (data.value.jobId) await pollJob();
}

async function retryRequest(key: string) {
  let receipt: FactoryReceipt;
  try { receipt = await factory<FactoryReceipt>({ action: "retry", requestKey: key }); }
  catch (error) {
    if (submissionRejected(error) && data.value.pendingKey === key) data.value.pendingKey = undefined;
    throw error;
  }
  adoptReceipt(receipt);
  if (data.value.pendingKey === key) data.value.pendingKey = undefined;
  await refreshProject();
  if (data.value.jobId) await pollJob();
  return receipt;
}

async function syncMedia() {
  const manifest = await factory<FactoryDelivery>({ action: "delivery", projectId: boundProject(), verify: !data.value.shotUid });
  delivery.value = manifest;
  if (manifest.localManifestPath) outputs.value.report = { dataType: "FILE", value: { url: manifest.localManifestPath, mimeType: "application/json" } };
  const clip = manifest.shot_clips.find(item => item.uid === data.value.shotUid);
  const artifact = data.value.shotUid ? clip?.artifact : manifest.aliases.original;
  if (!artifact) throw new Error("尚无对应视频，请查看任务状态");
  if (data.value.shotUid && !clip?.current_contract) throw new Error("镜头原片与当前分镜不一致，请按新计划生成后再采用");
  if (!data.value.shotUid && !manifest.ready_for_delivery) throw new Error("整片尚未通过技术交付检查，请查看详情并完成后期");
  const media = await factory<NodeMediaValue & { sha256: string }>({ action: "importArtifact", projectId: boundProject(), relativePath: artifact.relative_path, sha256: artifact.sha256 });
  outputs.value.video = { dataType: "VIDEO", value: { url: media.url, mimeType: media.mimeType } };
  message.value = data.value.shotUid ? "镜头结果已校验哈希并取回。" : "成片完整解码与下载哈希检查通过；画面和声音内容仍需审片。";
  return { manifest, media };
}

async function expandShots() {
  const value = await refreshProject();
  if (!value?.story) throw new Error("项目尚无分镜");
  const nodes = [];
  for (const [index, item] of value.story.shots.entries()) {
    let target = flow.getNodes.value.find(candidate => candidate.type === node.type && candidate.data?.projectId === value.id && candidate.data?.shotUid === item.uid);
    if (!target) {
      const nodeId = crypto.randomUUID();
      flow.addNodes({ id: nodeId, type: node.type, position: { x: node.position.x + 560 + index * 510, y: node.position.y }, data: { label: `镜头 ${item.id} · ${item.scene}`, projectId: value.id, shotUid: item.uid } });
      target = flow.findNode(nodeId);
    }
    if (!target) throw new Error("创建镜头节点失败");
    nodes.push(target);
  }
  // 等待新节点注册端口；仅组织画布，不提交任何渲染任务。
  await nextTick();
  const connect = (source: string, sourceHandle: string, target: string, targetHandle: string) => {
    if (flow.getEdges.value.some(edge => edge.source === source && edge.target === target && edge.sourceHandle === sourceHandle && edge.targetHandle === targetHandle)) return;
    const link = { source, sourceHandle, target, targetHandle };
    const sourceNode = flow.findNode(source);
    const targetNode = flow.findNode(target);
    if (!sourceNode || !targetNode || !validateConnection(link, { sourceNode, targetNode, nodes: flow.getNodes.value, edges: flow.getEdges.value })) throw new Error("镜头端口尚未就绪，请再点展开；已有节点会复用");
    flow.addEdges({ id: crypto.randomUUID(), ...link });
  };
  for (const [index, target] of nodes.entries()) {
    connect(id, "project", target.id, "projectIn");
    if (value.story.shots[index].use_previous_last_frame && index > 0) connect(nodes[index - 1].id, "shot", target.id, "previous");
  }
  return { projectId: value.id, nodes: nodes.map((target, index) => ({ nodeId: target.id, shotUid: value.story!.shots[index].uid })) };
}

nodeEvent.on("canConnect", connection => {
  const source = flow.findNode(connection.source);
  if (source?.type !== node.type || connection.source === id) return false;
  if (connection.targetHandle === "projectIn") return connection.sourceHandle === "project" && (!data.value.projectId || data.value.projectId === source.data?.projectId);
  if (connection.targetHandle !== "previous" || connection.sourceHandle !== "shot" || !source.data?.shotUid) return false;
  if (data.value.projectId && data.value.projectId !== source.data?.projectId) return false;
  if (flow.getEdges.value.some(edge => edge.target === id && edge.targetHandle === "previous" && edge.source !== source.id)) return false;
  if (project.value?.story && data.value.shotUid) {
    const index = project.value.story.shots.findIndex(item => item.uid === data.value.shotUid);
    return index > 0 && project.value.story.shots[index - 1].uid === source.data.shotUid;
  }
  return true;
});
nodeEvent.on("input:projectIn", values => {
  if (!values.length || data.value.projectId) return;
  try {
    const value = JSON.parse(String(values[0].value));
    if (value.kind === "h3Project") void bindProject(value.projectId).catch(fail);
  } catch (error) { fail(error); }
});
nodeEvent.on("input:previous", values => {
  data.value.previousUid = undefined;
  if (!values.length) return;
  try {
    if (values.length !== 1) throw new Error("接续只能连接一条前镜身份");
    const value = JSON.parse(String(values[0].value));
    if (value.kind !== "h3Shot" || value.projectId !== data.value.projectId) throw new Error("接续来源必须是同项目的 H3 镜头");
    data.value.previousUid = value.shotUid;
  } catch (error) { fail(error); }
});
nodeEvent.on("delete", () => { if (busy.value) throw new Error("提交尚未返回，请保留节点并先读取回执"); });
nodeEvent.on("copy", () => ({ jobId: undefined, pendingKey: undefined, plan: undefined, eventCursor: undefined }));

nodeTools.register({ name: "getFactoryState", description: "读取本节点的实时工厂项目、镜头 UID、revision、任务、计划和未保存草稿。修改前先读；不生成。", parameters: z.object({}), execute: () => perform(async () => { await refreshProject(); return { nodeId: id, project: project.value, shotUid: data.value.shotUid, draft: data.value.draft, plan: data.value.plan, jobId: data.value.jobId, pendingKey: data.value.pendingKey }; }) });
nodeTools.register({ name: "connectFactory", description: "只读核对本地工厂目录、协议、能力及 H3 引擎连接，不启动生成。", parameters: z.object({}), execute: () => perform(() => factory({ action: "connect" })) });
nodeTools.register({ name: "getWorkflowPlan", description: "创建项目之前检查基础模型、节点与附加资源；有参考图传 mode:I2VA，核对 ready、base_models 和 mode_status。工厂模型配置与视频生成节点的 ComfyUI 工作流独立，不能据另一入口就绪推断这里就绪。ready:false 时检查具体缺项与其他兼容方案，不用创建项目试探，也不自动下载。", parameters: z.object({ profile: factoryId, mode: z.enum(["T2VA", "I2VA", "L2VA", "FL2VA", "Ref2VA"]).optional() }), execute: args => perform(() => factory({ action: "workflowPlan", ...args })) });
nodeTools.register({ name: "bindProject", description: "将空节点绑定到实际工厂项目；传 shotUid 作为镜头节点，省略作为项目节点。", parameters: z.object({ projectId: factoryId, shotUid: factoryId.optional() }), execute: args => perform(() => bindProject(args.projectId, args.shotUid)) });
nodeTools.register({ name: "createProject", description: "保存当前 AI 根据用户需求编写的完整分镜；必填 storyboard.title、非空 shots，每镜提供 id、duration、完整 prompt。不能用空对象探测字段。有参考图时先创建无 bindings 的 I2VA 草稿，再 importReference 导入、expandShots 并 updateShot 绑定返回的 asset.id。仅保存，不生成。超时以同一 requestKey 复查。", parameters: z.object({ body: createProjectBody, requestKey: factoryId }), execute: args => perform(() => createProject(args.body, args.requestKey)) });
nodeTools.register({ name: "importReference", description: "将工作区真实参考图片导入此节点已绑定的工厂项目，返回 asset.id 与最新 revision；不生成。之后在镜头节点 updateShot 中将 bindings.first_frame 设为 asset.id。重复查询用同一 requestKey，不能把工作区路径直接当素材 ID。", parameters: importReferenceBody.extend({ requestKey: factoryId }), execute: args => perform(async () => {
  const receipt = await mutate({ action: "importReference", projectId: boundProject(), path: args.path, requestKey: args.requestKey });
  await refreshProject();
  return receipt;
}) });
nodeTools.register({ name: "expandShots", description: "将当前项目展开为可编辑镜头节点，连接项目和真实末帧接续关系；复用已存在节点，不生成。", parameters: z.object({}), execute: () => perform(expandShots) });
nodeTools.register({ name: "updateShot", description: "仅在 expandShots 返回的镜头节点操作，按其 UID 保存修改；必须使用最近读取的 expectedRevision。导入参考图后 changes 可为 {bindings:{first_frame:真实asset.id},mode:'I2VA'}。修改素材或剧情可能使旧提示词失效；回执 invalidated_prompts 非空时，先 getFactoryState 读取最新 revision，再单独提交 changes.prompt 后才 planGeneration。不会自动生成。", parameters: z.object({ changes: shotChanges, expectedRevision: z.string().min(1), requestKey: factoryId }), execute: args => perform(() => updateShot(args.changes, args.expectedRevision, args.requestKey)) });
nodeTools.register({ name: "compilePrompt", description: "将外部编写的 H3 段落按本镜实际模式编译；不调用文字模型、不保存。返回 prompt 和 revision 后通过 updateShot 保存。", parameters: z.object({ sections: z.record(z.string(), z.string()) }), execute: args => perform(() => { if (!data.value.shotUid) throw new Error("请选择镜头节点"); return factory({ action: "compile", projectId: boundProject(), shotUid: data.value.shotUid, sections: args.sections }); }) });
nodeTools.register({ name: "planGeneration", description: "计算本镜或整片的严格执行计划和接续影响范围；render 生成，finish 仅后期。不调用内部文字模型，不下载资源。", parameters: z.object({ kind: z.enum(["render", "finish"]).default("render"), regenerate: z.boolean().default(false) }), execute: args => perform(() => makePlan(args.kind, args.regenerate)) });
nodeTools.register({ name: "runPlan", description: "提交刚读取的 ready 计划，立即返回持久任务 ID。后续用 getJobStatus 观察，不能以超时为由另建任务。", parameters: z.object({ planId: z.string().regex(/^[a-f0-9]{64}$/), requestKey: factoryId }), execute: args => perform(() => runPlan(args.planId, args.requestKey)) });
nodeTools.register({ name: "getJobStatus", description: "读取原任务状态和事件，不启动新任务；done 仅代表任务阶段完成。", parameters: z.object({}), execute: () => perform(pollJob) });
nodeTools.register({ name: "resumeJob", description: "续跑此节点保留的原任务，保留工厂缓存和依赖校验；计划过期时应重新计划。", parameters: z.object({ requestKey: factoryId }), execute: args => perform(() => resumeJob(args.requestKey)) });
nodeTools.register({ name: "stopJob", description: "停止本节点原任务；immediate 为 true 时仅中断该任务拥有的引擎提交。", parameters: z.object({ requestKey: factoryId, immediate: z.boolean().default(false) }), execute: args => perform(() => stopJob(args.immediate, args.requestKey)) });
nodeTools.register({ name: "getSubmissionHistory", description: "读取此节点的持久请求记录，页面断开或回执丢失后先查询。", parameters: z.object({}), execute: () => perform(readHistory) });
nodeTools.register({ name: "retrySubmission", description: "以持久保存的原请求及同一请求键复查／补交，不改变内容或重新生成任务身份。", parameters: z.object({ requestKey: factoryId }), execute: args => perform(() => retryRequest(args.requestKey)) });
nodeTools.register({ name: "collectResult", description: "镜头节点取回当前分镜匹配的原片；项目节点完整解码检查成片后取回。下载核对 SHA256，输出工作区视频供画布使用。技术完整性不代表内容审片通过。", parameters: z.object({}), execute: () => perform(syncMedia) });

watch(() => [data.value.projectId, data.value.shotUid], publishIdentity, { immediate: true });
watch(() => data.value.sourceRevision, () => {
  data.value.plan = undefined;
  if (!data.value.shotUid || data.value.shotUid === data.value.sourceShotUid) {
    outputs.value.video = undefined;
    outputs.value.report = undefined;
    delivery.value = undefined;
    message.value = "分镜已更新，请重新计划；旧产物仍保留在工作区中。";
  }
  void refreshProject().catch(fail);
});
void restoreNode().catch(fail);
onScopeDispose(() => { disposed = true; if (timer) clearTimeout(timer); });
</script>

<style scoped lang="scss">
.factoryPanel {
  display: flex; flex-direction: column; gap: 12px; padding: 10px; font-size: 13px;
  .statusRow { display: flex; justify-content: space-between; align-items: center; gap: 8px; }
  label { display: flex; flex-direction: column; gap: 5px; }
  .setup { display: flex; flex-direction: column; gap: 12px; }
  .actions { display: flex; flex-wrap: wrap; gap: 7px; :deep(.el-button) { margin-left: 0; } }
  .identity { margin: 0; word-break: break-all; }
  .message, .footnote { color: var(--el-text-color-secondary); margin: 0; line-height: 1.5; }
  .error { color: var(--el-color-danger); white-space: pre-wrap; overflow-wrap: anywhere; }
  .pending { padding: 8px; background: var(--el-color-warning-light-9); overflow-wrap: anywhere; }
  .shotList { padding-left: 22px; margin: 0; li { margin-bottom: 6px; } small { color: var(--el-text-color-secondary); } }
  .details { summary { cursor: pointer; } pre { max-height: 220px; overflow: auto; white-space: pre-wrap; overflow-wrap: anywhere; font-size: 11px; } }
  .job { border-top: 1px solid var(--el-border-color); padding-top: 10px; small { overflow-wrap: anywhere; } }
  .historyItem { display: flex; justify-content: space-between; gap: 8px; padding: 6px 0; }
  video { width: 100%; max-height: 280px; background: #111; }
}
</style>
