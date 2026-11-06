<template>
  <section class="modelSearch">
    <h3>搜索本地模型</h3>
    <p class="hint">指定文件夹或盘符（例如 E:\），每行一个。搜索 safetensors、ckpt、gguf、pt、pth、bin；按目录推测类型，接入前可修改。</p>
    <el-input v-model="directories" aria-label="模型搜索目录" type="textarea" :rows="3" placeholder="E:\AI动漫\短剧工厂\models&#10;D:\" :disabled="running || pending" />
    <div class="actions">
      <el-button :disabled="running || pending" @click="choose">选择文件夹</el-button>
      <el-button type="primary" :disabled="running || pending || !directories.trim()" :loading="pending && !running" @click="start">开始搜索</el-button>
      <el-button v-if="running" :disabled="pending" @click="stop">停止搜索</el-button>
    </div>
    <p v-if="state" role="status">{{ statusLabel }} · 已扫描 {{ state.scanned }} 个目录 · 找到 {{ state.items.length }} 个候选 · 跳过 {{ state.skipped }} 项</p>
    <p v-if="state?.current" class="currentPath">{{ state.current }}</p>
    <el-alert v-if="state?.message" :title="state.message" type="info" :closable="false" />
    <el-alert v-if="error" :title="error" type="error" :closable="false" showIcon />
    <template v-if="state?.items.length">
      <el-input v-model="filter" aria-label="筛选模型" placeholder="按文件名或路径筛选，如 qwen、flux" clearable @input="page = 1" />
      <el-table :data="pageItems" rowKey="id" size="small" maxHeight="360">
        <el-table-column width="42">
          <template #header><el-checkbox :modelValue="pageSelected" :disabled="running || pending" aria-label="选择本页模型" @change="selectPage(!!$event)" /></template>
          <template #default="{ row }"><el-checkbox :modelValue="selected.includes(row.id)" :disabled="running || pending" :aria-label="`选择 ${row.name}`" @change="select(row.id, !!$event)" /></template>
        </el-table-column>
        <el-table-column label="模型与位置" minWidth="240"><template #default="{ row }"><strong>{{ row.name }}</strong><div class="modelPath">{{ row.path }}</div></template></el-table-column>
        <el-table-column label="大小" width="80"><template #default="{ row }">{{ (row.size / 1024 ** 3).toFixed(2) }} GB</template></el-table-column>
        <el-table-column label="模型类型" width="165"><template #default="{ row }"><el-select :modelValue="types[row.id] || row.category" :disabled="running || pending" :aria-label="`${row.name} 模型类型`" @update:modelValue="types[row.id] = $event"><el-option v-for="(label, value) in categories" :key="value" :label="label" :value="value" /></el-select></template></el-table-column>
      </el-table>
      <el-pagination v-model:currentPage="page" :pageSize="30" :total="filtered.length" layout="prev, pager, next, total" />
      <p class="hint">接入会在已保存的 ComfyUI 中创建目录链接，不复制或移动模型；同目录文件也会出现。未知类型须先选择正确类别。源目录需保持原位。</p>
      <el-button type="primary" :disabled="running || pending || !selected.length" @click="attach">接入所选模型目录（{{ selected.length }}）</el-button>
    </template>
    <el-alert v-if="message" :title="message" type="info" :closable="false" />
    <ul v-if="failures.length"><li v-for="item in failures" :key="item.path">{{ item.path }}：{{ item.message }}</li></ul>
    <p class="hint">跳过无权限目录、目录链接、Windows 系统目录及开发依赖目录。搜索只识别候选文件，不保证所有格式或模型均兼容当前工作流。</p>
  </section>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from "vue";
import http from "@/lib/http";
type Candidate = { id: string; name: string; path: string; size: number; category: string };
type Search = { id: string; status: string; scanned: number; skipped: number; current: string; message: string; items: Candidate[] };
const props = defineProps<{ visible?: boolean }>();
const directories = ref("");
const state = ref<Search | null>(null);
const pending = ref(false);
const error = ref("");
const message = ref("");
const failures = ref<{ path: string; message: string }[]>([]);
const filter = ref("");
const page = ref(1);
const selected = ref<string[]>([]);
const types = ref<Record<string, string>>({});
const categories: Record<string, string> = { unknown: "待确认", checkpoints: "Checkpoint", diffusion_models: "扩散模型 / UNet", text_encoders: "文本编码器", vae: "VAE", loras: "LoRA", controlnet: "ControlNet", clip_vision: "视觉编码器", upscale_models: "放大模型", embeddings: "Embedding", model_patches: "模型补丁", latent_upscale_models: "Latent 放大模型" };
const running = computed(() => state.value?.status === "running");
const statusLabel = computed(() => ({ running: "正在搜索", done: "搜索完成", stopped: "已停止", limited: "部分结果", error: "搜索出错" })[state.value?.status ?? "done"]);
const filtered = computed(() => (state.value?.items ?? []).filter(item => item.path.toLowerCase().includes(filter.value.toLowerCase())));
const pageItems = computed(() => filtered.value.slice((page.value - 1) * 30, page.value * 30));
const pageSelected = computed(() => pageItems.value.length > 0 && pageItems.value.every(item => selected.value.includes(item.id)));
let timer: ReturnType<typeof setTimeout> | undefined;
let disposed = false;
function select(id: string, value: boolean) { selected.value = value ? [...new Set([...selected.value, id])] : selected.value.filter(item => item !== id); }
function selectPage(value: boolean) { pageItems.value.forEach(item => select(item.id, value)); }
async function refresh() {
  clearTimeout(timer);
  const result = await http<Search | null>({ method: "GET", url: "/api/localModels/search/get" });
  if (state.value?.id !== result?.id) { selected.value = []; types.value = {}; page.value = 1; }
  state.value = result;
  if (!disposed && props.visible !== false && running.value) timer = setTimeout(() => void refresh().catch(report), 1200);
}
function report(cause: unknown) { error.value = cause instanceof Error ? cause.message : "操作失败"; }
async function perform(action: () => Promise<void>) {
  if (pending.value) return;
  pending.value = true; error.value = "";
  try { await action(); } catch (cause) { report(cause); } finally { pending.value = false; }
}
async function choose() {
  await perform(async () => {
    const result = await http<{ directory: string | null }>({ method: "POST", url: "/api/localModels/environment/selectDirectory", timeout: 0 });
    if (result.directory) directories.value = [directories.value.trim(), result.directory].filter(Boolean).join("\n");
  });
}
async function start() {
  await perform(async () => {
    await http({ method: "POST", url: "/api/localModels/search/start", data: { directories: directories.value.split(/\r?\n/).map(value => value.trim()).filter(Boolean) } });
    message.value = ""; failures.value = [];
    await refresh();
  });
}
async function stop() { await perform(async () => { await http({ method: "POST", url: "/api/localModels/search/stop", data: { id: state.value?.id } }); await refresh(); }); }
async function attach() {
  await perform(async () => {
    const items = (state.value?.items ?? []).filter(item => selected.value.includes(item.id)).map(item => ({ id: item.id, category: types.value[item.id] || item.category }));
    if (items.some(item => item.category === "unknown")) throw new Error("请先为选中的未知文件选择模型类型");
    if (items.length > 500) throw new Error("每次最多接入 500 个模型，请分批操作");
    const result = await http<{ results: { path: string; status: string; message?: string }[]; message: string }>({ method: "POST", url: "/api/localModels/search/attach", data: { searchId: state.value?.id, items }, timeout: 90000 });
    failures.value = result.results.filter(item => item.status === "error").map(item => ({ path: item.path, message: item.message ?? "接入失败" }));
    message.value = `成功 ${result.results.length - failures.value.length} 项，失败 ${failures.value.length} 项。${result.message}`;
  });
}
watch(() => props.visible, visible => { clearTimeout(timer); if (visible !== false) void refresh().catch(report); }, { immediate: true });
onBeforeUnmount(() => { disposed = true; clearTimeout(timer); });
</script>

<style scoped lang="scss">
.modelSearch {
  display: flex; flex-direction: column; align-items: stretch; gap: 12px;
  h3, p { margin: 0; }
  .hint, .modelPath { color: var(--el-text-color-secondary); line-height: 1.6; }
  .modelPath, .currentPath, li { overflow-wrap: anywhere; font-size: 12px; }
  .actions { display: flex; gap: 8px; flex-wrap: wrap; .el-button { margin: 0; } }
  > .el-button { align-self: flex-start; }
}
</style>
