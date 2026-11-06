<template>
  <div class="comfyEnvironment" v-loading="loading">
    <p class="intro">管理图片、视频和工作流共用的本地 ComfyUI。选择已有环境，或下载安装新环境。</p>
    <div class="runtimeCard">
      <div class="runtimeHeading">
        <strong>生成引擎</strong>
        <el-tag :type="state?.connected ? 'success' : 'info'">{{ state?.connected ? '运行中' : '未连接' }}</el-tag>
        <el-button link :disabled="!!pending" @click="reload">刷新状态</el-button>
      </div>
      <p class="runtimeAddress">{{ state?.environment.comfy_url || '尚未读取环境' }}</p>
      <div class="actions">
        <el-button type="primary" :disabled="!state?.environment.python || busy || !!pending || state?.connected" :loading="pending === 'start'" @click="start">启动已保存环境</el-button>
        <el-button v-if="state?.connected" tag="a" :href="state.environment.comfy_url" target="_blank" rel="noopener noreferrer">打开 ComfyUI</el-button>
      </div>
    </div>
    <el-alert v-if="error" :title="error" type="error" :closable="false" showIcon />
    <div v-if="state?.job" class="jobCard" role="status" aria-live="polite">
      <strong>{{ jobLabel }}</strong>
      <p>{{ state.progress.message || state.job.message }}</p>
      <template v-if="busy && state.progress.total">
        <el-progress :percentage="percentage" />
        <small>{{ state.progress.file }} · {{ bytes(state.progress.bytes || 0) }} / {{ bytes(state.progress.total) }}</small>
      </template>
      <el-button v-if="busy && state.job.kind === 'install'" :disabled="!!pending || !!state.job.cancel_requested" @click="stop">{{ state.job.cancel_requested ? '正在停止' : '暂停安装' }}</el-button>
    </div>
    <el-tabs v-model="mode">
      <el-tab-pane label="搜索本地模型" name="search"><modelSearch :visible="visible !== false && mode === 'search'" /></el-tab-pane>
      <el-tab-pane label="使用已有环境" name="existing">
        <el-form labelPosition="top" :disabled="busy || !!pending" @submit.prevent="save(false)">
          <el-form-item label="ComfyUI 文件夹">
            <div class="pathField">
              <el-input v-model="local.comfy_dir" placeholder="选择 ComfyUI 目录或便携包根目录" @input="local.python = ''" />
              <el-button @click="choose('comfy_dir')">选择文件夹</el-button>
            </div>
          </el-form-item>
          <el-button :disabled="!local.comfy_dir" :loading="pending === 'inspect'" @click="inspect">识别环境</el-button>
          <el-form-item label="推理 Python 路径">
            <el-input v-model="local.python" placeholder="自动识别，也可填写 python.exe 的完整路径" />
          </el-form-item>
          <el-form-item label="本地服务地址">
            <el-input v-model="local.comfy_url" placeholder="http://127.0.0.1:8188" />
          </el-form-item>
          <el-checkbox v-model="syncConnections">同步到图片、视频及工作流的 ComfyUI 地址</el-checkbox>
          <div class="actions">
            <el-button :disabled="!local.comfy_dir || !local.python" :loading="pending === 'save'" @click="save(false)">保存环境</el-button>
            <el-button type="primary" :disabled="!local.comfy_dir || !local.python" :loading="pending === 'saveStart'" @click="save(true)">保存并启动</el-button>
          </div>
          <p class="hint">保存后生效。已运行的服务需要关闭后重新启动，才会使用新的目录和 Python。</p>
        </el-form>
      </el-tab-pane>
      <el-tab-pane label="自动下载安装" name="fresh">
        <p class="hint">使用工厂现有安装清单，包含 ComfyUI、Python / CUDA 运行依赖及 H3 模型。支持 Windows x64 + NVIDIA；先预览下载量，再确认安装。</p>
        <el-form labelPosition="top" :disabled="busy || !!pending" @submit.prevent="preview">
          <el-form-item label="安装方案">
            <el-select v-model="install.manifest"><el-option v-for="item in state?.manifests" :key="item.id" :value="item.id" :label="item.name" /></el-select>
          </el-form-item>
          <el-form-item label="环境安装目录">
            <div class="pathField"><el-input v-model="install.install_dir" /><el-button @click="choose('install_dir')">选择文件夹</el-button></div>
          </el-form-item>
          <el-form-item label="模型保存目录">
            <div class="pathField"><el-input v-model="install.models_dir" /><el-button @click="choose('models_dir')">选择文件夹</el-button></div>
          </el-form-item>
          <el-form-item label="本地服务地址"><el-input v-model="install.comfy_url" placeholder="http://127.0.0.1:8188" /></el-form-item>
          <el-form-item label="已有模型搜索目录（可选，每行一个）"><el-input v-model="searchDirs" type="textarea" :rows="2" placeholder="已有模型可复用，减少重复下载" /></el-form-item>
          <el-checkbox v-model="syncConnections">同步到图片、视频及工作流的 ComfyUI 地址</el-checkbox>
          <div class="actions"><el-button type="primary" nativeType="submit" :loading="pending === 'plan'" :disabled="!install.manifest || !install.install_dir || !install.models_dir">预览安装清单</el-button></div>
        </el-form>
        <div v-if="plan" class="planCard">
          <h3>安装清单</h3>
          <p>预计下载 {{ bytes(plan.download_bytes) }} · 模型磁盘可用 {{ bytes(plan.hardware.free_disk_bytes) }}</p>
          <p class="hint">{{ plan.note }}</p>
          <el-table :data="planItems" maxHeight="280" size="small">
            <el-table-column prop="name" label="文件" minWidth="210" />
            <el-table-column label="大小" width="95"><template #default="{ row }">{{ bytes(row.size) }}</template></el-table-column>
            <el-table-column label="处理方式" width="85"><template #default="{ row }">{{ row.action === 'reuse' ? '复用' : '下载' }}</template></el-table-column>
          </el-table>
          <el-alert v-if="installBlock" :title="installBlock" type="warning" :closable="false" />
          <el-button type="primary" :loading="pending === 'install'" :disabled="busy || !!pending || !!installBlock" @click="beginInstall">确认下载并安装</el-button>
        </div>
      </el-tab-pane>
    </el-tabs>
    <el-collapse><el-collapse-item title="工厂连接设置" name="connection"><localConnection :visible="visible" /></el-collapse-item></el-collapse>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, reactive, ref, watch } from "vue";
import { ElMessage } from "element-plus";
import { translate } from "@toonflow/i18n/vue";
import http from "@/lib/http";
import { saveSettings } from "@/stores/settings";
import localConnection from "../mediaModel/localConnection.vue";
import modelSearch from "./modelSearch.vue";

type Environment = { comfy_dir: string; python: string; comfy_url: string; mode: string };
type State = {
  environment: Environment; connected: boolean; defaults: { install_dir: string; models_dir: string };
  manifests: { id: string; name: string }[];
  job: { id: string; kind: string; status: string; message: string; cancel_requested: number } | null;
  progress: { bytes?: number; total?: number; file?: string; message?: string };
};
type PlanItem = { name: string; size: number; action?: string };
type Plan = {
  download_bytes: number; confirmation_token: string; note: string;
  hardware: { os: string; architecture: string; gpu: unknown[]; free_disk_bytes: number };
  portable: PlanItem; runtime_wheels: PlanItem[]; models: PlanItem[];
};
const props = defineProps<{ visible?: boolean }>();
const state = ref<State>();
const local = reactive({ comfy_dir: "", python: "", comfy_url: "http://127.0.0.1:8188" });
const install = reactive({ mode: "fresh", manifest: "", install_dir: "", models_dir: "", comfy_url: "http://127.0.0.1:8188" });
const mode = ref("existing");
const searchDirs = ref("");
const syncConnections = ref(true);
const loading = ref(false);
const pending = ref("");
const error = ref("");
const plan = ref<Plan>();
let timer: ReturnType<typeof setTimeout> | undefined;
let disposed = false;
const busy = computed(() => ["queued", "running"].includes(state.value?.job?.status ?? ""));
const jobLabel = computed(() => translate(({ queued: "正在排队", running: "正在执行", done: "任务已完成", error: "任务失败", paused: "任务已暂停", cancelled: "任务已取消" } as Record<string, string>)[state.value?.job?.status ?? ""] ?? "任务状态"));
const percentage = computed(() => Math.min(100, Math.floor((state.value?.progress.bytes ?? 0) / (state.value?.progress.total || 1) * 100)));
const planItems = computed(() => plan.value ? [plan.value.portable, ...plan.value.runtime_wheels, ...plan.value.models] : []);
const installBlock = computed(() => {
  const hardware = plan.value?.hardware;
  if (!hardware) return "";
  if (hardware.os !== "Windows" || !["amd64", "x86_64"].includes(hardware.architecture.toLowerCase()) || !hardware.gpu.length) return translate("自动安装需要 Windows x64 和 NVIDIA 显卡");
  return hardware.free_disk_bytes < (plan.value?.download_bytes ?? 0) ? translate("模型保存磁盘空间不足，请更换目录") : "";
});
function bytes(value: number) { return value < 1024 ** 3 ? `${(value / 1024 ** 2).toFixed(1)} MB` : `${(value / 1024 ** 3).toFixed(2)} GB`; }
function options() { return { ...install, model_search_dirs: searchDirs.value.split(/\r?\n/).map(value => value.trim()).filter(Boolean) }; }
watch([install, searchDirs], () => { plan.value = undefined; }, { deep: true });

async function refresh(initial = false) {
  clearTimeout(timer);
  try {
    state.value = await http<State>({ method: "GET", url: "/api/localModels/environment/get", timeout: 30000 });
    if (initial) {
      Object.assign(local, { comfy_dir: state.value.environment.comfy_dir, python: state.value.environment.python, comfy_url: state.value.environment.comfy_url });
      Object.assign(install, state.value.defaults, { comfy_url: local.comfy_url, manifest: state.value.manifests[0]?.id ?? "" });
    }
  } finally {
    if (!disposed && props.visible !== false && busy.value) timer = setTimeout(() => { void refresh().catch(reportError); }, 3000);
  }
}
function reportError(cause: unknown) { error.value = cause instanceof Error ? cause.message : translate("操作失败，请重试"); }
async function perform(name: string, action: () => Promise<void>) {
  if (pending.value) return;
  pending.value = name; error.value = "";
  try { await action(); } catch (cause) { reportError(cause); } finally { pending.value = ""; }
}
async function reload() { await perform("refresh", () => refresh()); }
watch(() => props.visible, async visible => {
  clearTimeout(timer);
  if (visible === false) return;
  loading.value = true;
  try { await refresh(true); } catch (cause) { reportError(cause); } finally { loading.value = false; }
}, { immediate: true });
onBeforeUnmount(() => { disposed = true; clearTimeout(timer); });

async function choose(field: "comfy_dir" | "install_dir" | "models_dir") {
  await perform("choose", async () => {
    const { directory } = await http<{ directory: string | null }>({ method: "POST", url: "/api/localModels/environment/selectDirectory", timeout: 0 });
    if (!directory) return;
    if (field === "comfy_dir") {
      local.comfy_dir = directory; local.python = "";
      await detect();
    } else install[field] = directory;
  });
}
async function detect() {
  const result = await http<{ comfy_dir: string; python: string }>({ method: "POST", url: "/api/localModels/environment/inspect", data: { comfy_dir: local.comfy_dir, python: local.python } });
  Object.assign(local, { comfy_dir: result.comfy_dir, python: result.python });
  if (!result.python) error.value = translate("未识别到推理 Python，请手动填写完整路径");
}
async function inspect() { await perform("inspect", detect); }
async function linkConnections(url: string) {
  if (!syncConnections.value) return;
  const connection = await http<Record<string, string>>({ method: "GET", url: "/api/localModels/config" });
  await saveSettings(current => {
    const providers = current.mediaProviderConfigs as Record<string, Record<string, unknown>> | undefined;
    return { localModels: { ...connection, comfyUrl: url }, mediaProviderConfigs: { ...providers, comfyUi: { ...providers?.comfyUi, imageUrl: url, videoUrl: url } } };
  });
}
async function enqueueStart() {
  await http({ method: "POST", url: "/api/localModels/environment/start" });
  await refresh();
}
async function save(launch: boolean) {
  await perform(launch ? "saveStart" : "save", async () => {
    await http({ method: "POST", url: "/api/localModels/environment/save", data: { ...local } });
    await linkConnections(local.comfy_url);
    if (launch) await enqueueStart(); else await refresh();
    ElMessage.success(translate(launch ? "已提交启动任务" : "环境已保存"));
  });
}
async function start() { await perform("start", enqueueStart); }
async function preview() { await perform("plan", async () => { plan.value = await http<Plan>({ method: "POST", url: "/api/localModels/environment/plan", data: options(), timeout: 120000 }); }); }
async function beginInstall() {
  if (!plan.value) return;
  const request = { ...options(), download_confirmation: plan.value.confirmation_token };
  await perform("install", async () => {
    await http({ method: "POST", url: "/api/localModels/environment/install", data: request, timeout: 120000 });
    plan.value = undefined;
    await refresh();
    await linkConnections(request.comfy_url);
    ElMessage.success(translate("已提交安装任务"));
  });
}
async function stop() { await perform("stop", async () => { await http({ method: "POST", url: "/api/localModels/environment/stop" }); await refresh(); }); }
</script>

<style scoped lang="scss">
.comfyEnvironment {
  display: flex;
  flex-direction: column;
  gap: 16px;
  max-width: 760px;
  .intro, .hint { color: var(--el-text-color-secondary); line-height: 1.7; margin: 0 0 12px; }
  .runtimeCard, .jobCard, .planCard { padding: 16px; border: 1px solid var(--el-border-color); border-radius: 10px; }
  .runtimeHeading { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
  .runtimeAddress, .jobCard p { overflow-wrap: anywhere; line-height: 1.6; }
  .actions { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 16px; .el-button { margin: 0; } }
  .pathField { display: flex; width: 100%; gap: 8px; .el-input { flex: 1; min-width: 0; } }
  .el-form > .el-button { margin: -6px 0 18px; }
  .el-checkbox { white-space: normal; height: auto; :deep(.el-checkbox__label) { white-space: normal; line-height: 1.7; } }
  .planCard { margin-top: 18px; h3 { margin-top: 0; } > .el-button, > .el-alert { margin-top: 16px; } }
  .jobCard { display: flex; flex-direction: column; align-items: stretch; gap: 8px; p { margin: 0; } .el-button { align-self: flex-start; } }
  @media (max-width: 700px) { .pathField { flex-wrap: wrap; .el-input { flex-basis: 100%; } } }
}
</style>
