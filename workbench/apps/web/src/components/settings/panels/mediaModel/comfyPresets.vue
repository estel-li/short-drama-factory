<template>
  <section class="comfyPresets">
    <div class="heading"><strong>内置工作流</strong><el-button size="small" :loading="loading" :disabled="disabled || !url" @click="refresh">读取可用工作流</el-button></div>
    <p>选择固定方案，读取对应模型后应用。参数与提示词绑定会自动填入下方表单。</p>
    <template v-if="presets.length">
      <el-select v-model="selected" aria-label="内置工作流" :disabled="disabled || loading || applying" @change="choose"><el-option v-for="item in presets" :key="item.id" :value="item.id" :label="item.label" /></el-select>
      <template v-if="preset">
        <p>{{ preset.description }} <a :href="preset.source" target="_blank" rel="noopener noreferrer">官方工作流来源</a></p>
        <el-alert v-if="preset.missingNodes.length" type="warning" :closable="false" :title="`缺少节点：${preset.missingNodes.join('、')}。请更新 ComfyUI 或切换环境后重新读取。`" />
        <el-form labelPosition="top">
          <el-form-item v-for="field in preset.fields" :key="field.key" :label="field.label">
            <el-select v-model="models[field.key]" :aria-label="`工作流${field.label}`" filterable :disabled="disabled || loading || applying" :placeholder="field.options.length ? '请选择模型' : '未发现匹配模型，请先到 ComfyUI 环境中搜索接入'">
              <el-option v-for="file in field.options" :key="file" :value="file" :label="file" />
            </el-select>
          </el-form-item>
        </el-form>
        <el-button type="primary" :loading="applying" :disabled="disabled || loading || !ready" @click="apply">{{ independent ? '加入画布模型列表' : '应用到当前配置' }}</el-button>
        <small v-if="independent">此方案独立保存，与已有方案同时出现在画布下拉列表。再次应用同名方案可更新它的模型文件，点击窗口底部“保存”后生效。</small>
        <small v-else>应用会替换当前{{ mediaType === 'image' ? '图片' : '视频' }}默认工作流，已有的独立图生图方案保留，点击窗口底部“保存”后生效。</small>
      </template>
    </template>
    <el-alert v-if="error" type="error" :title="error" :closable="false" />
    <p v-if="message" role="status">{{ message }}</p>
  </section>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from "vue";
import http from "@/lib/http";
import type { MediaProviderModel } from "@toonflow/provider-web/types";
type Preset = { id: string; label: string; description: string; source: string; missingNodes: string[]; fields: { key: string; label: string; options: string[] }[] };
type Applied = { workflow: Record<string, unknown>; outputNode: string; label: string; model: MediaProviderModel; independent: boolean; inputMode: "image" | "text" };
const props = defineProps<{ mediaType: "image" | "video"; url: string; disabled?: boolean }>();
const emit = defineEmits<{ apply: [value: Applied] }>();
const presets = ref<Preset[]>([]);
const selected = ref("");
const models = ref<Record<string, string>>({});
const loading = ref(false);
const applying = ref(false);
const error = ref("");
const message = ref("");
const preset = computed(() => presets.value.find(item => item.id === selected.value));
const independent = computed(() => props.mediaType === "image" && (selected.value.endsWith("Edit") || selected.value.startsWith("qwen")));
const ready = computed(() => !!preset.value && !preset.value.missingNodes.length && preset.value.fields.every(field => field.options.includes(models.value[field.key] ?? "")));
let controller: AbortController | undefined;
function choose() { models.value = Object.fromEntries((preset.value?.fields ?? []).map(field => [field.key, field.options[0] ?? ""])); message.value = ""; }
async function refresh() {
  controller?.abort();
  const request = new AbortController(); controller = request;
  loading.value = true; error.value = "";
  try {
    const values = await http<Preset[]>({ method: "POST", url: "/api/localModels/workflows/catalog", data: { url: props.url, mediaType: props.mediaType }, signal: request.signal, timeout: 30000 });
    if (request.signal.aborted) return;
    presets.value = values;
    if (!values.some(item => item.id === selected.value)) selected.value = values[0]?.id ?? "";
    choose();
  } catch (cause) { if (!request.signal.aborted) error.value = cause instanceof Error ? cause.message : "读取工作流失败"; }
  finally { if (controller === request) loading.value = false; }
}
async function apply() {
  if (!ready.value || applying.value) return;
  controller?.abort();
  const request = new AbortController(); controller = request;
  applying.value = true; error.value = ""; message.value = "";
  try {
    const value = await http<Applied>({ method: "POST", url: "/api/localModels/workflows/build", data: { url: props.url, mediaType: props.mediaType, preset: selected.value, models: { ...models.value } }, signal: request.signal, timeout: 30000 });
    if (request.signal.aborted) return;
    emit("apply", value);
    message.value = value.independent ? `已加入“${value.label}”，保存后可直接在画布选择；已有方案保留。` : `已应用“${value.label}”，可先测试，再保存配置。`;
  } catch (cause) { if (!request.signal.aborted) error.value = cause instanceof Error ? cause.message : "应用工作流失败"; }
  finally { if (controller === request) applying.value = false; }
}
watch(() => [props.url, props.mediaType], () => { controller?.abort(); controller = undefined; presets.value = []; selected.value = ""; loading.value = applying.value = false; error.value = message.value = ""; });
onBeforeUnmount(() => controller?.abort());
</script>

<style scoped lang="scss">
.comfyPresets {
  display: grid; gap: 12px; padding: 16px; margin-bottom: 20px;
  border: 1px solid var(--el-border-color); border-radius: 10px;
  .heading { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
  p, small { margin: 0; line-height: 1.7; color: var(--el-text-color-secondary); }
  .el-form-item:last-child { margin-bottom: 0; }
  .el-select { width: 100%; }
  a { color: var(--el-color-primary); }
}
</style>
