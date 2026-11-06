<template>
  <el-dialog
    v-model="visible"
    :title="`配置${mediaType === 'video' ? '视频' : '图片'}模型：${provider?.label ?? ''}`"
    width="min(800px, calc(100vw - 32px))"
    alignCenter
    appendToBody
    destroyOnClose
    :closeOnClickModal="false"
    :closeOnPressEscape="!saving"
    :showClose="!saving"
    @closed="formApi = undefined">
    <div class="providerEditor">
      <messageMarkdown v-if="provider?.readme" class="providerReadme" :content="provider.readme" />
      <form-create v-model="formValues" v-model:api="formApi" :rule="formRules" :option="formOptions" />
      <section v-if="provider?.id === 'comfyUi'" class="comfyControls">
        <el-space wrap>
          <el-button :loading="checkingComfy" :disabled="saving" @click="inspectComfy">检查连接并读取大模型</el-button>
          <el-button :disabled="saving" @click="workflowFile?.click()">导入 API 工作流</el-button>
          <input ref="workflowFile" type="file" accept=".json,application/json" hidden @change="importWorkflow" />
        </el-space>
        <el-select v-if="mediaType === 'image' && checkpoints.length" placeholder="选择服务器上的 Checkpoint" filterable :disabled="saving" @change="selectCheckpoint">
          <el-option v-for="name in checkpoints" :key="name" :label="name" :value="name" />
        </el-select>
        <p v-if="comfyStatus" role="status">{{ comfyStatus }}</p>
        <el-text type="info">API 工作流中，把正向提示词输入替换为 <code v-pre>{{prompt}}</code>；图生图的图片输入替换为 <code v-pre>{{image0}}</code>。普通画布 JSON 不能直接运行。</el-text>
      </section>
      <div class="modelHeader">
        <h4>模型配置 <el-text type="info">{{ visibleModels.length }}</el-text></h4>
        <el-button :icon="IconPlus" size="small" :disabled="saving" @click="editModel()">手动添加</el-button>
      </div>
      <div class="modelList">
        <el-card v-for="{ item, index } in visibleModels" :key="index" class="modelCard" shadow="never">
          <div class="topInfo">
            <div class="modelNameWrap">
              <modelIcon :model="item.id" :size="24" />
              <div class="modelInfo">
                <span class="modelName">{{ item.label }}</span>
                <el-text class="modelId" type="info" size="small">{{ item.id }}</el-text>
              </div>
            </div>
            <div class="actionButtons">
              <el-button text size="small" :icon="IconPlayerPlay" :loading="loadingTestModel === index" :disabled="saving || loadingTestModel !== undefined || item.type === 'text'" :title="item.type === 'text' ? '此处支持图片、视频和音频模型测试' : undefined" :aria-label="`测试模型 ${item.label}`" @click="testModel(index)">测试</el-button>
              <el-button text size="small" :icon="IconEdit" :disabled="saving" :aria-label="`编辑模型 ${item.label}`" @click="editModel(index)">编辑</el-button>
              <el-button text size="small" type="danger" :icon="IconTrash" :disabled="saving" :aria-label="`删除模型 ${item.label}`" @click="models.splice(index, 1)">删除</el-button>
            </div>
          </div>
          <div class="modelTags">
            <el-tag size="small">{{ modelTypes[item.type] }}</el-tag>
            <el-tag v-for="(tag, tagIndex) in modelTags(item)" :key="tagIndex" size="small" type="info">{{ tag }}</el-tag>
          </div>
        </el-card>
        <el-text v-if="!visibleModels.length" type="info">暂无模型</el-text>
      </div>
    </div>
    <el-alert v-if="formError" class="formError" :title="formError" type="error" :closable="false" showIcon />
    <template #footer>
      <el-button :disabled="saving" @click="visible = false">取消</el-button>
      <el-button type="primary" :icon="IconDeviceFloppy" :loading="saving" :disabled="!formApi" @click="saveModels">保存</el-button>
    </template>
    <component
      :is="modelEditorDialog"
      v-model="modelEditorVisible"
      :model="editingModelIndex === undefined ? { id: '', label: '', type: mediaType } : models[editingModelIndex]"
      :models="models"
      @confirmed="confirmModel" />
  </el-dialog>
  <el-dialog v-model="testVisible" :title="`测试媒体模型：${testProvider?.label ?? ''}`" width="min(1120px, calc(100vw - 32px))" alignCenter appendToBody destroyOnClose :closeOnClickModal="false">
    <div class="modelTestBody">
      <providerTestPanel v-if="testVisible && testProvider" :source="testSource" :provider="testProvider" :config="testConfig" :modelId="testModelId" :models="testProvider.models" />
    </div>
  </el-dialog>
</template>

<script setup lang="ts">
import { translate } from "@toonflow/i18n/vue";

import axios from "axios";
import { computed, defineAsyncComponent, onBeforeUnmount, ref, shallowRef, toRaw, watch, type Component } from "vue";
import { IconPlus, IconTrash, IconDeviceFloppy, IconEdit, IconPlayerPlay } from "@tabler/icons-vue";
import formCreate, { type Api, type Options } from "@toonflow/provider-web/formCreate";
import { modelIcon } from "@toonflow/model-icons";
import messageMarkdown from "@/components/messageMarkdown.vue";
import type { MediaProvider, MediaProviderModel } from "@toonflow/provider-web/types";
import { settings, saveSettings } from "@/stores/settings";
import { invalidateNodeModels } from "@toonflow/nodes-scaffold/nodeAi";
import providerTestPanel from "./providerTestPanel.vue";
import http from "@/lib/http";

const { provider, mediaType = "video" } = defineProps<{ provider?: MediaProvider; mediaType?: "image" | "video" }>();
const modelEditorDialog = shallowRef<Component>();
const visible = defineModel<boolean>({ default: false });
const emit = defineEmits<{ saved: [provider: MediaProvider] }>();
const models = ref<MediaProviderModel[]>([]);
const visibleModels = computed(() => models.value.map((item, index) => ({ item, index })).filter(({ item }) => item.type === mediaType));
const modelEditorVisible = ref(false);
const editingModelIndex = ref<number>();
const saving = ref(false);
const formApi = shallowRef<Api>();
const formRules = shallowRef<ReturnType<typeof formCreate.copyRules>>([]);
const formValues = ref<Record<string, unknown>>({});
const workflowFile = ref<HTMLInputElement>();
const checkpoints = ref<string[]>([]);
const checkingComfy = ref(false);
const comfyStatus = ref("");
const formOptions = computed<Options>(() => ({ form: { labelPosition: "top", disabled: saving.value }, appendValue: false, submitBtn: false, resetBtn: false }));
const revision = ref("");
const formError = ref("");
const testVisible = ref(false);
const loadingTestModel = ref<number>();
const testModelId = ref("");
const testProvider = shallowRef<MediaProvider>();
const testSource = ref("");
const testConfig = ref<Record<string, unknown>>({});
let testLoading: AbortController | undefined;
const modelTypes = { get image() { return translate("图片"); }, get video() { return translate("视频"); }, get audio() { return translate("音频"); }, get text() { return translate("文本"); } };
const modeLabels: Record<string, string> = {
  singleImage: "单图参考", multiReference: "多图参考", startEndRequired: "首尾帧必填",
  endFrameOptional: "尾帧可选", startFrameOptional: "首帧可选",
  imageReference: "图片参考", videoReference: "视频参考", audioReference: "音频参考",
};

async function inspectComfy() {
  checkingComfy.value = true;
  formError.value = comfyStatus.value = "";
  try {
    const values = formApi.value?.formData() ?? formValues.value;
    const result = await http<{ checkpoints: string[] }>({ method: "POST", url: "/api/localModels/inspect", data: { url: values[mediaType === "image" ? "imageUrl" : "videoUrl"] } });
    checkpoints.value = result.checkpoints;
    comfyStatus.value = `ComfyUI 已连接，读取到 ${result.checkpoints.length} 个 Checkpoint。其他架构的模型请使用对应工作流。`;
  } catch (error) { formError.value = error instanceof Error ? error.message : "连接失败"; }
  finally { checkingComfy.value = false; }
}

function selectCheckpoint(value: string) {
  formApi.value?.setValue("checkpoint", value);
}

async function importWorkflow(event: Event) {
  const input = event.target as HTMLInputElement;
  const file = input.files?.[0]; input.value = "";
  if (!file) return;
  try {
    if (file.size > 2 * 1024 * 1024) throw new Error("工作流不能超过 2 MB");
    const value = JSON.parse(await file.text());
    if (!value || typeof value !== "object" || Array.isArray(value) || !Object.keys(value).length
      || Object.values(value).some((node: any) => !node || typeof node.class_type !== "string" || !node.inputs)) throw new Error("请从 ComfyUI 导出 API 格式的工作流");
    formApi.value?.setValue(mediaType === "image" ? "imageWorkflow" : "videoWorkflow", JSON.stringify(value, null, 2));
    comfyStatus.value = "工作流已导入，请确认提示词和参考图绑定后保存。";
    formError.value = "";
  } catch (error) { formError.value = error instanceof Error ? error.message : "导入失败"; }
}

watch(visible, isVisible => {
  testLoading?.abort();
  testLoading = undefined;
  loadingTestModel.value = undefined;
  testVisible.value = false;
  if (!isVisible) return;
  formError.value = "";
  modelEditorVisible.value = false;
  editingModelIndex.value = undefined;
  const configs = settings.value.mediaProviderConfigs as Record<string, Record<string, unknown>> | undefined;
  formRules.value = formCreate.copyRules((provider?.rules ?? []).filter(rule => !rule.mediaType || rule.mediaType === mediaType));
  const values = structuredClone(toRaw((provider && configs?.[provider.id]) ?? {}));
  const local = settings.value.localModels as { comfyUrl?: string } | undefined;
  formValues.value = provider?.id === "comfyUi" ? { imageUrl: local?.comfyUrl || "http://127.0.0.1:8188", videoUrl: local?.comfyUrl || "http://127.0.0.1:8188", ...values } : values;
  checkpoints.value = []; comfyStatus.value = "";
  revision.value = provider?.revision ?? "";
  models.value = JSON.parse(JSON.stringify(provider?.models ?? []));
}, { immediate: true });
onBeforeUnmount(() => testLoading?.abort());

async function testModel(index: number) {
  const model = models.value[index];
  if (saving.value || loadingTestModel.value !== undefined || !provider || !model || model.type === "text") return;
  const controller = new AbortController();
  testLoading = controller;
  loadingTestModel.value = index;
  formError.value = "";
  try {
    const currentProvider = { ...provider, models: JSON.parse(JSON.stringify(models.value)) as MediaProviderModel[] };
    const currentRevision = revision.value;
    const config = structuredClone(toRaw(formApi.value?.formData() ?? formValues.value));
    const modelId = model.id;
    const { data } = await axios.get<{ code: number; data: { source: string; revision: string }; message?: string }>("/api/providers/media/source", {
      params: { fileName: currentProvider.fileName }, headers: { "x-toonflow-workspace": "1" }, signal: controller.signal,
    });
    if (controller.signal.aborted) return;
    if (data.code !== 200 || !data.data) throw new Error(data.message || "读取供应商代码失败");
    if (data.data.revision !== currentRevision) throw new Error("供应商代码已更新，请重新打开编辑窗口后测试");
    testSource.value = data.data.source;
    testProvider.value = currentProvider;
    testConfig.value = config;
    testModelId.value = modelId;
    testVisible.value = true;
  } catch (error) {
    if (!controller.signal.aborted) formError.value = axios.isAxiosError(error) ? error.response?.data?.message || error.message : error instanceof Error ? error.message : "读取供应商代码失败";
  } finally {
    if (testLoading === controller) { testLoading = undefined; loadingTestModel.value = undefined; }
  }
}

function modelTags(model: MediaProviderModel) {
  const modes = Array.isArray(model.mode) ? model.mode.flat().filter((mode): mode is string => typeof mode === "string") : [];
  return modes.map(mode => {
    if (mode === "text") return model.type === "image" ? translate("文生图") : translate("文生视频");
    const reference = /^(imageReference|videoReference|audioReference):(\d+)$/.exec(mode);
    return reference ? `${modeLabels[reference[1]!]} ×${reference[2]}` : modeLabels[mode] ?? mode;
  });
}

function editModel(index?: number) {
  modelEditorDialog.value ??= defineAsyncComponent(() => import("@toonflow/provider-web/modelEditor"));
  editingModelIndex.value = index;
  modelEditorVisible.value = true;
}

function confirmModel(model: MediaProviderModel) {
  if (model.type !== mediaType) { formError.value = "请在对应的模型分类中添加此模型"; return; }
  const index = editingModelIndex.value;
  if (index === undefined) models.value.push(model);
  else models.value.splice(index, 1, model);
}

async function saveModels() {
  if (saving.value || !provider || !formApi.value) return;
  const { id: providerId, fileName } = provider;
  formError.value = "";
  let modelsSaved = false;
  let configSaved = false;
  saving.value = true;
  try {
    if (!(await formApi.value.validate().then(() => true, () => false))) return;
    const config = formApi.value.formData();
    if ("apiKey" in config) {
      config.apiKey = typeof config.apiKey === "string" ? config.apiKey.trim() : "";
      if ((config.apiKey as string).length > 8192) throw new Error("API Key 过长");
    }
    const ids = new Set<string>();
    const values = models.value.map((item, index) => {
      const id = item.id.trim();
      const label = item.label.trim();
      if (!id || !label) throw new Error(`请填写第 ${index + 1} 个模型的 ID 和显示名称`);
      if (ids.has(id)) throw new Error(`模型 ID 重复：${id}`);
      ids.add(id);
      return { ...item, id, label };
    });
    const { data } = await axios.put<{ code: number; data: MediaProvider; message?: string }>("/api/providers/media/save", {
      fileName, revision: revision.value, models: values,
    }, { headers: { "x-toonflow-workspace": "1" } });
    if (data.code !== 200 || !data.data) throw new Error(data.message || "保存模型失败");
    revision.value = data.data.revision;
    modelsSaved = true;
    invalidateNodeModels("media");
    await saveSettings(settings => {
      const configs = settings.mediaProviderConfigs as Record<string, Record<string, unknown>> | undefined;
      if (configs !== undefined && (!configs || typeof configs !== "object" || Array.isArray(configs))) throw new Error("媒体供应商配置格式无效");
      const current = configs?.[providerId];
      if (current !== undefined && (!current || typeof current !== "object" || Array.isArray(current))) throw new Error("当前供应商配置格式无效");
      if (Object.entries(config).every(([field, value]) => JSON.stringify(value) === JSON.stringify(current?.[field]))) return;
      return { mediaProviderConfigs: { ...configs, [providerId]: { ...current, ...config } } };
    });
    configSaved = true;
    const response = await axios.get<{ code: number; data: MediaProvider[]; message?: string }>("/api/providers/media/list");
    if (response.data.code !== 200 || !Array.isArray(response.data.data)) throw new Error(response.data.message || "读取最新模型失败");
    const latest = response.data.data.find(item => item.fileName === fileName);
    if (!latest) throw new Error("供应商已不存在");
    revision.value = latest.revision;
    emit("saved", latest);
    visible.value = false;
  } catch (error) {
    const message = axios.isAxiosError(error) ? error.response?.data?.message || error.message : error instanceof Error ? error.message : translate("保存失败，请重试");
    formError.value = configSaved ? `模型与连接配置已保存，读取最新模型失败：${message}。请重新打开编辑。`
      : modelsSaved ? `模型已保存，连接配置未保存：${message}。填写内容已保留，请重试。` : message;
  } finally {
    saving.value = false;
  }
}
</script>

<style lang="scss" scoped>
.providerEditor {
  max-height: 65dvh;
  padding: 8px 4px;
  overflow-y: auto;
  overscroll-behavior: contain;

  .providerReadme { margin-bottom: 20px; }
  .comfyControls { display: grid; gap: 12px; margin: 12px 0 24px; }

  .modelHeader {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    margin-bottom: 12px;

    h4 { margin: 0; }
  }

  .modelList {
    display: flex;
    flex-direction: column;
    gap: 10px;

    .modelCard {
      .topInfo {
        display: flex;
        align-items: center;
        justify-content: space-between;
        flex-wrap: wrap;
        gap: 12px;

        .modelNameWrap {
          display: flex;
          align-items: center;
          gap: 8px;
          min-width: 0;

          .modelInfo {
            display: flex;
            flex-direction: column;
            gap: 4px;
            min-width: 0;
            overflow-wrap: anywhere;

            .modelName { font-size: 15px; font-weight: 600; }
            .modelId { align-self: flex-start; }
          }
        }

        .actionButtons {
          display: flex;
          flex-shrink: 0;
          margin-left: auto;
        }
      }

      .modelTags {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        margin-top: 16px;
      }
    }
  }
}

.formError { margin-top: 16px; }
.modelTestBody { height: min(660px, calc(100dvh - 160px)); min-height: 0; }
</style>
