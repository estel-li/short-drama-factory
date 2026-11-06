<template>
  <el-form class="importForm" labelPosition="top" :disabled="importing" @submit.prevent="importServers">
    <el-form-item :label="mode === 'json' ? '配置文件' : 'DXT 包'">
      <div class="fileSource">
        <input ref="fileInput" type="file" :accept="mode === 'json' ? '.json' : '.dxt,.mcpb'" hidden @change="selectFile" />
        <el-input :modelValue="fileName" :prefixIcon="mode === 'json' ? IconFileCode : IconPackage" placeholder="尚未选择文件" readonly aria-label="已选择的 MCP 文件" />
        <el-button :icon="IconFolderOpen" :loading="reading" @click="fileInput?.click()">选择文件</el-button>
      </div>
    </el-form-item>
    <template v-if="mode === 'json'">
      <el-form-item label="JSON 配置">
        <el-input v-model="source" class="sourceInput" type="textarea" :rows="10" resize="none" :disabled="reading" :maxlength="1024 * 1024" autocomplete="off" spellcheck="false" dir="ltr" />
        <el-text class="fieldHint" size="small" type="info">支持 mcpServers 批量配置、带 name 的单个配置或配置数组，导入后新增服务。</el-text>
      </el-form-item>
    </template>
    <template v-else-if="packageInfo">
      <div class="packageInfo">
        <div class="packageHeading">
          <el-text tag="strong">{{ packageInfo.name }}</el-text>
          <el-tag size="small" type="info" effect="plain">v{{ packageInfo.version }}</el-tag>
        </div>
        <el-text v-if="packageInfo.description" class="packageDescription" size="small" type="info">{{ packageInfo.description }}</el-text>
      </div>
      <el-form-item v-for="field in fields" :key="field.key" :label="field.title" :required="field.required">
        <el-switch v-if="field.type === 'boolean'" v-model="field.booleanValue" :aria-label="field.title" />
        <el-input-number v-else-if="field.type === 'number'" v-model="field.numberValue" :min="field.min" :max="field.max" controlsPosition="right" :aria-label="field.title" />
        <el-input
          v-else
          v-model="field.textValue"
          :type="field.multiple ? 'textarea' : field.sensitive ? 'password' : 'text'"
          :showPassword="!field.multiple && field.sensitive"
          :rows="3"
          autocomplete="off"
          spellcheck="false"
          :aria-label="field.title" />
        <el-text v-if="field.description" class="fieldHint" size="small" type="info">{{ field.description }}</el-text>
        <el-text v-if="field.multiple" class="fieldHint" size="small" type="info">每行一个路径。</el-text>
      </el-form-item>
    </template>
    <el-alert v-if="error" class="importError" :title="error" type="error" :closable="false" showIcon />
  </el-form>
</template>

<script setup lang="ts">
import { translate } from "@toonflow/i18n/vue";
import axios from "axios";
import { computed, onBeforeUnmount, ref } from "vue";
import { IconFileCode, IconPackage, IconFolderOpen } from "@tabler/icons-vue";

type DxtField = {
  key: string;
  type: "string" | "number" | "boolean" | "directory" | "file";
  title: string;
  description?: string;
  required?: boolean;
  default?: string | number | boolean | string[];
  sensitive?: boolean;
  multiple?: boolean;
  min?: number;
  max?: number;
};
type DxtInfo = { name: string; version: string; description?: string; userConfig: DxtField[] };
type FieldDraft = DxtField & { textValue: string; numberValue: number | undefined; booleanValue: boolean };
const { mode, localSupported } = defineProps<{ mode: "json" | "dxt"; localSupported: boolean }>();
const emit = defineEmits<{ busy: [value: boolean]; saved: [count: number] }>();
const requestHeaders = { "x-toonflow-workspace": "1" };
const fileInput = ref<HTMLInputElement>();
const fileName = ref("");
const source = ref("");
const reading = ref(false);
const importing = ref(false);
const error = ref("");
const packageInfo = ref<DxtInfo>();
const fields = ref<FieldDraft[]>([]);
const packagePayload = ref<{ fileName: string; content: string }>();
const ready = computed(() => !reading.value && !importing.value && (mode === "json" ? !!source.value.trim() : localSupported && !!packageInfo.value && !!packagePayload.value));
const controller = new AbortController();
let inspectController: AbortController | undefined;
let fileReader: FileReader | undefined;
onBeforeUnmount(() => {
  controller.abort();
  inspectController?.abort();
  fileReader?.abort();
});
defineExpose({ importServers, ready });

function errorMessage(cause: unknown) {
  return axios.isAxiosError(cause) ? cause.response?.data?.message || cause.message : cause instanceof Error ? cause.message : translate("导入失败");
}

async function selectFile(event: Event) {
  const input = event.target as HTMLInputElement;
  const file = input.files?.[0];
  input.value = "";
  if (!file || importing.value) return;
  inspectController?.abort();
  fileReader?.abort();
  const currentController = new AbortController();
  inspectController = currentController;
  error.value = "";
  fileName.value = file.name;
  source.value = "";
  packageInfo.value = undefined;
  packagePayload.value = undefined;
  fields.value = [];
  reading.value = true;
  try {
    const maxBytes = (mode === "json" ? 1 : 50) * 1024 * 1024;
    if (!file.size || file.size > maxBytes) throw new Error(`请选择非空且不超过 ${mode === "json" ? 1 : 50} MB 的文件`);
    if (mode === "json") {
      if (!/\.json$/i.test(file.name)) throw new Error("请选择 .json 配置文件");
      const content = await file.text();
      if (!currentController.signal.aborted) source.value = content;
      return;
    }
    if (!localSupported) throw new Error("当前平台不支持导入本地 MCP 包");
    if (!/\.(dxt|mcpb)$/i.test(file.name)) throw new Error("请选择 .dxt 或 .mcpb 包");
    const content = await new Promise<string>((resolve, reject) => {
      const reader = new FileReader();
      fileReader = reader;
      reader.onload = () => resolve((reader.result as string).split(",", 2)[1]!);
      reader.onerror = () => reject(reader.error);
      reader.onabort = () => reject(new DOMException("文件读取已取消", "AbortError"));
      reader.readAsDataURL(file);
    });
    if (currentController.signal.aborted) return;
    const payload = { fileName: file.name, content };
    const { data } = await axios.post<{ code: number; data: DxtInfo; message?: string }>(
      "/api/mcp/servers/inspectDxt", payload, { headers: requestHeaders, signal: currentController.signal }
    );
    if (currentController.signal.aborted) return;
    if (data.code !== 200) throw new Error(data.message || "读取 DXT 包失败");
    if (!data.data || typeof data.data.name !== "string" || typeof data.data.version !== "string" || !Array.isArray(data.data.userConfig)) {
      throw new Error("DXT 包信息格式错误");
    }
    packageInfo.value = data.data;
    packagePayload.value = payload;
    fields.value = data.data.userConfig.map(field => ({
      ...field,
      textValue: Array.isArray(field.default) ? field.default.join("\n") : typeof field.default === "string" ? field.default : "",
      numberValue: typeof field.default === "number" ? field.default : undefined,
      booleanValue: typeof field.default === "boolean" ? field.default : false,
    }));
  } catch (cause) {
    if (!currentController.signal.aborted) error.value = errorMessage(cause);
  } finally {
    if (inspectController === currentController) reading.value = false;
  }
}

function readUserConfig() {
  return Object.fromEntries(fields.value.flatMap(field => {
    const value = field.type === "boolean" ? field.booleanValue
      : field.type === "number" ? field.numberValue
      : field.multiple ? field.textValue.split(/\r?\n/).filter(line => line.trim()) : field.textValue;
    const missing = value === undefined || value === "" || (Array.isArray(value) && !value.length);
    if (missing && field.required) throw new Error(`请填写${field.title}`);
    return value === undefined ? [] : [[field.key, value]];
  }));
}

async function importServers() {
  if (!ready.value) return;
  error.value = "";
  try {
    const payload = mode === "json" ? { source: source.value } : { ...packagePayload.value!, userConfig: readUserConfig() };
    importing.value = true;
    emit("busy", true);
    const { data } = await axios.post(
      `/api/mcp/servers/${mode === "json" ? "importJson" : "importDxt"}`, payload, { headers: requestHeaders, signal: controller.signal }
    );
    if (controller.signal.aborted) return;
    if (data.code !== 200) throw new Error(data.message || "导入 MCP 失败");
    const count = mode === "json" && Array.isArray(data.data?.servers) ? data.data.servers.length : 1;
    emit("saved", count);
  } catch (cause) {
    if (!controller.signal.aborted) error.value = errorMessage(cause);
  } finally {
    importing.value = false;
    emit("busy", false);
  }
}
</script>

<style scoped lang="scss">
.importForm {
  .fileSource {
    display: flex;
    width: 100%;
    gap: 8px;
    .el-input { min-width: 0; }
    .el-button { flex-shrink: 0; }
  }
  .sourceInput :deep(.el-textarea__inner) {
    height: min(28dvh, 240px);
    min-height: 140px;
    padding: 12px;
    font-family: "Cascadia Code", "SFMono-Regular", Consolas, monospace;
    font-size: 13px;
    line-height: 1.7;
  }
  .packageInfo {
    margin-bottom: 18px;
    overflow-wrap: anywhere;
    .packageHeading { display: flex; align-items: center; flex-wrap: wrap; gap: 8px; }
    .packageDescription { display: block; margin-top: 8px; line-height: 1.5; }
  }
  .fieldHint { display: block; width: 100%; margin-top: 6px; line-height: 1.5; }
  .importError { margin-top: 12px; }
}
</style>
