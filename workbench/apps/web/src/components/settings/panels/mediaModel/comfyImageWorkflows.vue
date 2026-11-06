<template>
  <section class="comfyImageWorkflows" aria-label="内置图片工作流">
    <div class="catalogHeading">
      <strong>内置图片工作流 <el-text type="info">{{ presets.length || '' }}</el-text></strong>
      <el-button size="small" :loading="loading" :disabled="disabled || !!applying || !connectionUrl" @click="refresh">重新读取工作流</el-button>
    </div>
    <p>每个方案独立选择模型文件并加入画布，点击窗口底部“保存”后生效。</p>
    <el-alert v-if="error" type="error" :title="error" :closable="false" />
    <p v-if="message" role="status">{{ message }}</p>
    <el-card v-for="preset in presets" :key="preset.id" class="workflowCard" shadow="never" :data-preset-id="preset.id">
      <div class="cardHeading">
        <div class="modelHeading">
          <modelIcon :model="preset.modelId" :size="24" />
          <div class="modelName">
            <strong>{{ installedModel(preset)?.label || preset.label }}</strong>
            <el-text size="small" type="info">{{ preset.modelId }}</el-text>
          </div>
        </div>
        <div class="actions">
          <el-button text size="small" :icon="IconPlayerPlay" :disabled="disabled || testing || !!applying || !ready(preset) || needsApply(preset)" :aria-label="t`测试工作流 ${preset.label}`" @click="emit('test', preset.modelId)">测试</el-button>
          <el-button text size="small" :icon="IconEdit" :disabled="disabled || !!applying" :aria-label="t`配置工作流 ${preset.label}`" :aria-expanded="expanded === preset.id" @click="expanded = expanded === preset.id ? '' : preset.id">配置</el-button>
          <el-button v-if="installedModel(preset)" text size="small" type="danger" :disabled="disabled || !!applying || testing" :aria-label="t`移出画布 ${preset.label}`" @click="emit('remove', preset.modelId)">移出画布</el-button>
        </div>
      </div>
      <div class="tags">
        <el-tag size="small" type="info">{{ preset.inputMode === 'image' ? translate('图生图') : translate('文生图') }}</el-tag>
        <el-tag size="small" :type="installedModel(preset) ? 'success' : 'info'">{{ installedModel(preset) ? translate('已加入画布') : translate('未加入画布') }}</el-tag>
        <el-tag v-if="!currentCatalog" size="small" type="info">{{ loading ? translate('正在检测') : translate('待重新检测') }}</el-tag>
        <el-button v-else-if="preset.missingNodes.length" size="small" type="warning" plain :aria-label="t`修复工作流节点 ${preset.label}`" @click="repairId = preset.id">节点未加载 {{ preset.missingNodes.length }} · 引导修复</el-button>
        <el-tag v-else-if="missingFields(preset).length" size="small" type="warning">缺少匹配模型</el-tag>
        <el-tag v-else size="small" type="success">环境就绪</el-tag>
        <el-tag v-if="installedModel(preset) && needsApply(preset)" size="small" type="warning">配置待应用</el-tag>
      </div>
      <div v-if="expanded === preset.id" class="configuration">
        <p>{{ preset.description }}</p>
        <el-link :href="preset.source" target="_blank" rel="noopener noreferrer">官方工作流说明</el-link>
        <el-form labelPosition="top" @submit.prevent>
          <el-form-item v-for="field in preset.fields" :key="field.key" :label="field.label">
            <el-select v-model="selections[preset.id]![field.key]" filterable :disabled="disabled || loading || !!applying" :aria-label="t`${preset.label} ${field.label}`" :placeholder="field.options.length ? translate('请选择模型文件') : translate('未发现匹配模型文件')">
              <el-option v-for="file in field.options" :key="file" :value="file" :label="file" />
            </el-select>
            <el-text v-if="selections[preset.id]?.[field.key] && !field.options.includes(selections[preset.id]![field.key]!)" type="warning">原选文件已不可用，请重新选择；不会自动替换为其他模型。</el-text>
          </el-form-item>
        </el-form>
        <p v-if="currentCatalog && missingFields(preset).length">缺少模型文件：{{ missingFields(preset).map(field => field.label).join('、') }}。请在“ComfyUI 环境”中搜索并接入对应目录，再重新读取。</p>
        <div class="actions">
          <el-button type="primary" :loading="applying === preset.id" :disabled="disabled || !!applying || !ready(preset)" @click="apply(preset)">{{ installedModel(preset) ? translate('应用配置') : translate('加入画布') }}</el-button>
          <el-button v-if="installedModel(preset)" :disabled="disabled || !!applying" @click="emit('edit', preset.modelId)">模型参数</el-button>
        </div>
      </div>
    </el-card>
  </section>
  <el-dialog :modelValue="!!repairId" title="检查 ComfyUI 未加载节点" width="min(640px, calc(100vw - 32px))" alignCenter appendToBody :closeOnClickModal="false" @update:modelValue="value => { if (!value) repairId = ''; }">
    <div v-if="repairPreset" class="repairGuide">
      <strong>{{ repairPreset.label }}</strong>
      <p>当前连接：{{ connectionUrl }}。请在运行此 ComfyUI 的电脑上操作。</p>
      <el-alert v-if="error" type="error" :title="error" :closable="false" />
      <template v-if="repairPreset.missingNodes.length">
        <el-alert title="当前运行的 ComfyUI 尚未加载这些内置节点，不代表磁盘上没有节点文件。若刚更新过代码，请先确认依赖已同步，再完整重启 ComfyUI；仅刷新网页不会加载新节点。" type="warning" :closable="false" />
        <div class="missingNodes"><el-tag v-for="name in repairPreset.missingNodes" :key="name" type="warning">{{ name }}</el-tag></div>
        <el-button size="small" @click="copyMissingNodes">复制缺失节点列表</el-button>
        <p>重启后仍未加载时，再按安装方式检查更新和启动日志。更新前等待任务结束，并备份当前环境及数据库。</p>
        <el-radio-group v-model="installType" aria-label="ComfyUI 安装方式">
          <el-radio-button value="portable">Windows 便携版</el-radio-button>
          <el-radio-button value="manual">手动安装</el-radio-button>
          <el-radio-button value="desktop">ComfyUI Desktop</el-radio-button>
        </el-radio-group>
        <ol v-if="installType === 'portable'">
          <li>关闭 ComfyUI，在便携包根目录打开 update 文件夹，运行 update_comfyui.bat 更新本体。</li>
          <li>重新启动原来的 ComfyUI 启动脚本。若启动日志提示依赖错误，按官方说明处理；全量更新 Python 依赖会影响现有环境。</li>
        </ol>
        <ol v-else-if="installType === 'manual'">
          <li>关闭 ComfyUI，进入 ComfyUI 源码目录，激活该环境的 Python 虚拟环境。</li>
          <li>更新源码和依赖。Git 有本地改动或更新冲突时先处理，不强制覆盖。</li>
        </ol>
        <ol v-else>
          <li>在 ComfyUI Desktop 的 Manage 面板打开 Update，更新 ComfyUI 实例。</li>
          <li>需要的新节点尚未包含在稳定版时，按官方说明选择 Latest on GitHub 更新通道，完成后重启。</li>
        </ol>
        <pre v-if="installType === 'manual'">git pull --ff-only
python -m pip install -r requirements.txt</pre>
        <p>重启后点击“修复后重新检测”。节点仍缺失时，检查启动日志和工作台连接地址是否指向刚更新的环境。</p>
        <div class="guideLinks">
          <el-link href="https://docs.comfy.org/installation/update_comfyui" target="_blank" rel="noopener noreferrer">官方更新指南</el-link>
          <el-link :href="repairPreset.source" target="_blank" rel="noopener noreferrer">对应工作流说明</el-link>
        </div>
      </template>
      <el-alert v-else-if="currentCatalog && !loading && !error" title="所需节点已齐全，可以返回配置模型文件。" type="success" :closable="false" />
    </div>
    <template #footer>
      <el-button @click="repairId = ''">关闭</el-button>
      <el-button type="primary" :loading="loading" :disabled="!connectionUrl || !!applying" @click="refresh">修复后重新检测</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from "vue";
import { ElMessage } from "element-plus";
import { IconEdit, IconPlayerPlay } from "@tabler/icons-vue";
import { modelIcon } from "@toonflow/model-icons";
import { t, translate } from "@toonflow/i18n/vue";
import type { MediaProviderModel } from "@toonflow/provider-web/types";
import http from "@/lib/http";
import { writeClipboardText } from "@/lib/clipboard";

type Field = { key: string; label: string; node: string; input: string; options: string[] };
type Preset = { id: string; modelId: string; label: string; inputMode: "text" | "image"; description: string; source: string; missingNodes: string[]; fields: Field[] };
type Applied = { workflow: Record<string, unknown>; outputNode: string; model: MediaProviderModel; label: string; independent: boolean; inputMode: "text" | "image" };
const props = defineProps<{ url: string; models: MediaProviderModel[]; profiles: Record<string, { workflow: string }>; disabled?: boolean; testing?: boolean }>();
const emit = defineEmits<{ apply: [value: Applied]; test: [id: string]; edit: [id: string]; remove: [id: string]; catalog: [ids: string[]]; busy: [value: boolean] }>();
const presets = ref<Preset[]>([]);
const selections = ref<Record<string, Record<string, string>>>({});
const expanded = ref("");
const loading = ref(false);
const applying = ref("");
const error = ref("");
const message = ref("");
const checkedUrl = ref("");
const connectionUrl = computed(() => props.url.trim());
const currentCatalog = computed(() => !!checkedUrl.value && checkedUrl.value === connectionUrl.value);
const repairId = ref("");
const repairPreset = computed(() => presets.value.find(preset => preset.id === repairId.value));
const installType = ref("portable");
let catalogRequest: AbortController | undefined;
let buildRequest: AbortController | undefined;
let refreshTimer: ReturnType<typeof setTimeout> | undefined;

function installedModel(preset: Preset) { return props.models.find(model => model.id === preset.modelId && model.type === "image"); }
function savedFiles(preset: Preset) {
  const profile = props.profiles[preset.modelId];
  if (!profile) return;
  try {
    const nodes = Object.values(JSON.parse(profile.workflow)) as { class_type?: string; inputs?: Record<string, unknown> }[];
    return Object.fromEntries(preset.fields.map(field => {
      const value = nodes.find(node => node?.class_type === field.node)?.inputs?.[field.input];
      return [field.key, typeof value === "string" ? value : ""];
    }));
  } catch { return {}; }
}
function missingFields(preset: Preset) { return preset.fields.filter(field => !field.options.includes(selections.value[preset.id]?.[field.key] ?? "")); }
function ready(preset: Preset) { return currentCatalog.value && !loading.value && !preset.missingNodes.length && !missingFields(preset).length; }
function needsApply(preset: Preset) {
  const saved = savedFiles(preset);
  return !installedModel(preset) || !saved || preset.fields.some(field => saved[field.key] !== selections.value[preset.id]?.[field.key]);
}
async function refresh() {
  catalogRequest?.abort();
  const request = new AbortController(); catalogRequest = request;
  loading.value = true; error.value = ""; checkedUrl.value = "";
  const url = connectionUrl.value;
  try {
    const values = await http<Preset[]>({ method: "POST", url: "/api/localModels/workflows/catalog", data: { url, mediaType: "image" }, signal: request.signal, timeout: 30000 });
    if (request.signal.aborted) return;
    for (const preset of values) selections.value[preset.id] ??= savedFiles(preset) ?? Object.fromEntries(preset.fields.map(field => [field.key, field.options[0] ?? ""]));
    presets.value = values; checkedUrl.value = url;
    emit("catalog", values.map(preset => preset.modelId));
  } catch (cause) { if (!request.signal.aborted) error.value = cause instanceof Error ? cause.message : translate("读取工作流失败"); }
  finally { if (catalogRequest === request) loading.value = false; }
}
async function apply(preset: Preset) {
  if (props.disabled || applying.value || !ready(preset)) return;
  const request = new AbortController(); buildRequest = request;
  applying.value = preset.id; error.value = message.value = "";
  try {
    const value = await http<Applied>({ method: "POST", url: "/api/localModels/workflows/build", data: { url: connectionUrl.value, mediaType: "image", preset: preset.id, models: { ...selections.value[preset.id] } }, signal: request.signal, timeout: 30000 });
    if (request.signal.aborted) return;
    emit("apply", value);
    message.value = t`已应用“${value.label}”，点击窗口底部“保存”后在画布生效。`;
  } catch (cause) {
    if (request.signal.aborted) return;
    if ((cause as { status?: number }).status === 409) { await refresh(); if (!request.signal.aborted) repairId.value = preset.id; }
    if (!request.signal.aborted) error.value = cause instanceof Error ? cause.message : translate("应用工作流失败");
  } finally { if (buildRequest === request) applying.value = ""; }
}
async function copyMissingNodes() {
  try { await writeClipboardText(repairPreset.value?.missingNodes.join("\n") ?? ""); ElMessage.success(translate("缺失节点列表已复制")); }
  catch { ElMessage.error(translate("复制失败，请手动选择节点名称复制")); }
}
watch(connectionUrl, () => {
  clearTimeout(refreshTimer); catalogRequest?.abort(); buildRequest?.abort();
  catalogRequest = buildRequest = undefined;
  presets.value = []; selections.value = {}; checkedUrl.value = expanded.value = repairId.value = applying.value = error.value = message.value = ""; loading.value = false;
  emit("catalog", []);
  if (connectionUrl.value) refreshTimer = setTimeout(() => { void refresh(); }, 400);
}, { immediate: true });
watch(applying, value => emit("busy", !!value), { flush: "sync" });
onBeforeUnmount(() => { clearTimeout(refreshTimer); catalogRequest?.abort(); buildRequest?.abort(); emit("busy", false); });
</script>

<style scoped lang="scss">
.comfyImageWorkflows {
  display: grid; gap: 12px;
  p { margin: 0; line-height: 1.7; color: var(--el-text-color-secondary); }
  .catalogHeading, .cardHeading { display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 12px; }
  .workflowCard {
    .modelHeading { display: flex; align-items: center; gap: 8px; min-width: 0; }
    .modelName { display: grid; gap: 4px; overflow-wrap: anywhere; strong { font-size: 15px; } }
    .actions { display: flex; align-items: center; flex-wrap: wrap; gap: 4px; }
    .tags { display: flex; align-items: center; flex-wrap: wrap; gap: 8px; margin-top: 14px; }
    .configuration { display: grid; gap: 12px; margin-top: 16px; padding-top: 16px; border-top: 1px solid var(--el-border-color-lighter); }
    .el-form-item:last-child { margin-bottom: 0; }
    .el-select { width: 100%; }
    .el-link { justify-self: start; }
  }
}
.repairGuide {
  display: grid; gap: 14px; overflow-wrap: anywhere;
  p, ol { margin: 0; line-height: 1.8; }
  .missingNodes, .guideLinks { display: flex; flex-wrap: wrap; gap: 8px; }
  .el-button { justify-self: start; }
  pre { margin: 0; padding: 12px; background: var(--el-fill-color-light); white-space: pre-wrap; }
}
</style>
