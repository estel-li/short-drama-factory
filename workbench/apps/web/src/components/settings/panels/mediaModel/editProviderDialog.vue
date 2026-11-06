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
      <comfyPresets v-if="provider?.id === 'comfyUi'" :mediaType="mediaType" :url="String(formValues[mediaType === 'image' ? 'imageUrl' : 'videoUrl'] || '')" :disabled="saving || !formApi" @apply="applyPreset" />
      <messageMarkdown v-if="provider?.readme" class="providerReadme" :content="provider.readme" />
      <form-create :key="formVersion" v-model="formValues" v-model:api="formApi" :rule="formRules" :option="formOptions" />
      <section v-if="provider?.id === 'comfyUi'" class="comfyControls">
        <el-space wrap>
          <el-button :loading="checkingComfy" :disabled="saving" @click="inspectComfy">检查连接并读取模型</el-button>
          <el-button :disabled="saving" @click="workflowFile?.click()">导入 API 工作流</el-button>
          <input ref="workflowFile" type="file" accept=".json,application/json" hidden @change="importWorkflow" />
        </el-space>
        <p v-if="comfyStatus" role="status">{{ comfyStatus }}</p>
        <el-collapse v-if="modelGroups.some(group => group.files.length)" v-model="expandedModelGroups" class="comfyModelGroups">
          <el-collapse-item v-for="group in modelGroups.filter(group => group.files.length)" :key="group.id" :name="group.id" :title="`${translate(modelGroupLabels[group.id] ?? group.id)}（${group.files.length}）`">
            <ul><li v-for="file in group.files" :key="file">{{ file }}</li></ul>
          </el-collapse-item>
        </el-collapse>
        <el-collapse v-if="unclassifiedModelGroups.length" class="comfyModelGroups">
          <el-collapse-item title="用途待确认的文件（不加入模型候选）" name="unclassified">
            <p>这些文件的用途无法从目录和文件名确定，请核对对应工作流。</p>
            <div v-for="group in unclassifiedModelGroups" :key="group.id">
              <strong>{{ translate(modelGroupLabels[group.id] ?? group.id) }}（{{ group.files.length }}）</strong>
              <ul><li v-for="file in group.files" :key="file">{{ file }}</li></ul>
            </div>
          </el-collapse-item>
        </el-collapse>
        <el-text v-if="comfyStatus" type="info">分类依据模型目录和明确的模型家族文件名；用途待确认的文件单独列出。</el-text>
        <el-text v-if="modelGroups.length" type="info">Checkpoint 用于默认 SD / SDXL 流程。扩散模型需在对应 API 工作流的加载节点中选择，H3 模型使用 H3 工作流。</el-text>
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
            <el-tag v-if="workflowModels[item.id]" size="small" type="success">独立图片工作流</el-tag>
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
import { translate, t } from "@toonflow/i18n/vue";

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
import comfyPresets from "./comfyPresets.vue";

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
const formVersion = ref(0);
type WorkflowProfile = { mediaType: "image"; workflow: string; outputNode: string; inputMode?: "image" | "text" };
const workflowModels = ref<Record<string, WorkflowProfile>>({});
const changedWorkflows = ref<Record<string, WorkflowProfile>>({});
const workflowFile = ref<HTMLInputElement>();
const modelGroups = ref<{ id: string; files: string[] }[]>([]);
const unclassifiedModelGroups = ref<{ id: string; files: string[] }[]>([]);
const expandedModelGroups = ref<string[]>([]);
const modelGroupLabels: Record<string, string> = { checkpoints: "Checkpoint", diffusionModels: "扩散模型 / UNet", textEncoders: "文本编码器", vae: "VAE", loras: "LoRA" };
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
let comfyLoading: AbortController | undefined;
const modelTypes = { get image() { return translate("图片"); }, get video() { return translate("视频"); }, get audio() { return translate("音频"); }, get text() { return translate("文本"); } };
const modeLabels: Record<string, string> = {
  singleImage: "单图参考", multiReference: "多图参考", startEndRequired: "首尾帧必填",
  endFrameOptional: "尾帧可选", startFrameOptional: "首帧可选",
  imageReference: "图片参考", videoReference: "视频参考", audioReference: "音频参考",
};

function applyPreset(value: { workflow: Record<string, unknown>; outputNode: string; model: MediaProviderModel; independent: boolean; inputMode: "image" | "text" }) {
  if (value.independent) {
    const profile: WorkflowProfile = { mediaType: "image", workflow: JSON.stringify(value.workflow, null, 2), outputNode: value.outputNode, inputMode: value.inputMode };
    workflowModels.value[value.model.id] = profile;
    changedWorkflows.value[value.model.id] = profile;
  } else setWorkflow(value.workflow, value.outputNode);
  const index = models.value.findIndex(item => item.id === value.model.id);
  if (index < 0) models.value.push(value.model); else models.value.splice(index, 1, value.model);
  formError.value = "";
}

function setWorkflow(workflow: Record<string, unknown>, outputNode = "") {
  const api = formApi.value;
  if (!api) return;
  const values = { ...api.formData(), [mediaType === "image" ? "imageWorkflow" : "videoWorkflow"]: JSON.stringify(workflow, null, 2),
    [mediaType === "image" ? "imageOutputNode" : "videoOutputNode"]: outputNode };
  // 用当前表单快照重新挂载，避免 FormCreate 的输入缓存仍显示上一个工作流。
  formApi.value = undefined;
  formRules.value = formCreate.copyRules(formRules.value);
  formValues.value = values;
  formVersion.value++;
}

async function inspectComfy() {
  comfyLoading?.abort();
  const controller = new AbortController();
  comfyLoading = controller;
  checkingComfy.value = true;
  formError.value = comfyStatus.value = "";
  resetComfyCatalog();
  try {
    const values = formApi.value?.formData() ?? formValues.value;
    const url = values[mediaType === "image" ? "imageUrl" : "videoUrl"];
    const result = await http<{ checkpoints: string[]; modelGroups: { id: string; files: string[] }[]; unclassifiedGroups: { id: string; files: string[] }[]; excludedModelCount: number }>({ method: "POST", url: "/api/localModels/inspect", data: { url, mediaType }, signal: controller.signal });
    if (controller.signal.aborted || (formApi.value?.formData() ?? formValues.value)[mediaType === "image" ? "imageUrl" : "videoUrl"] !== url) return;
    if (mediaType === "image") {
      formApi.value?.updateRule("checkpoint", { options: result.checkpoints.map(name => ({ label: name, value: name })) });
      formApi.value?.sync("checkpoint");
    }
    modelGroups.value = result.modelGroups;
    unclassifiedModelGroups.value = result.unclassifiedGroups;
    const diffusionCount = result.modelGroups.find(group => group.id === "diffusionModels")?.files.length ?? 0;
    expandedModelGroups.value = [result.modelGroups.find(group => group.files.length)?.id ?? ""];
    comfyStatus.value = mediaType === "image"
      ? t`ComfyUI 已连接：可选图片 Checkpoint ${result.checkpoints.length} 个，识别到图片扩散模型 ${diffusionCount} 个。已排除 ${result.excludedModelCount} 个视频模型；视频模型请在视频设置中查看。`
      : t`ComfyUI 已连接：识别到 ${diffusionCount + result.checkpoints.length} 个视频模型。已排除 ${result.excludedModelCount} 个图片模型。`;
  } catch (error) { if (!controller.signal.aborted) formError.value = error instanceof Error ? error.message : translate("连接失败"); }
  finally { if (comfyLoading === controller) { comfyLoading = undefined; checkingComfy.value = false; } }
}

function resetComfyCatalog() {
  modelGroups.value = []; unclassifiedModelGroups.value = []; expandedModelGroups.value = []; comfyStatus.value = "";
  if (provider?.id === "comfyUi" && mediaType === "image") {
    formApi.value?.updateRule("checkpoint", { options: [] });
    formApi.value?.sync("checkpoint");
  }
}

watch(() => formValues.value[mediaType === "image" ? "imageUrl" : "videoUrl"], () => {
  comfyLoading?.abort(); comfyLoading = undefined; checkingComfy.value = false;
  resetComfyCatalog();
});

async function importWorkflow(event: Event) {
  const input = event.target as HTMLInputElement;
  const file = input.files?.[0]; input.value = "";
  if (!file) return;
  try {
    if (file.size > 2 * 1024 * 1024) throw new Error("工作流不能超过 2 MB");
    const value = JSON.parse(await file.text());
    if (!value || typeof value !== "object" || Array.isArray(value) || !Object.keys(value).length
      || Object.values(value).some((node: any) => !node || typeof node.class_type !== "string" || !node.inputs)) throw new Error("请从 ComfyUI 导出 API 格式的工作流");
    setWorkflow(value);
    comfyStatus.value = "工作流已导入，请确认提示词和参考图绑定后保存。";
    formError.value = "";
  } catch (error) { formError.value = error instanceof Error ? error.message : "导入失败"; }
}

watch(visible, isVisible => {
  comfyLoading?.abort();
  comfyLoading = undefined;
  checkingComfy.value = false;
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
  // 兼容已经安装的旧版 ComfyUI 适配器，只增强此字段，不覆盖供应商文件。
  if (provider?.id === "comfyUi" && mediaType === "image") {
    const checkpointRule = formRules.value.find(rule => rule.field === "checkpoint");
    if (checkpointRule) {
      checkpointRule.type = "select";
      checkpointRule.props = { ...checkpointRule.props, filterable: true, allowCreate: true, defaultFirstOption: true, clearable: true,
        placeholder: translate("连接读取后选择，也可输入完整文件名"), noDataText: translate("暂无图片 Checkpoint，可手动输入文件名") };
      checkpointRule.options = [];
    }
  }
  const values = structuredClone(toRaw((provider && configs?.[provider.id]) ?? {}));
  workflowModels.value = provider?.id === "comfyUi" ? structuredClone((values.workflowModels ?? {}) as Record<string, WorkflowProfile>) : {};
  changedWorkflows.value = {};
  const local = settings.value.localModels as { comfyUrl?: string } | undefined;
  formValues.value = provider?.id === "comfyUi" ? { imageUrl: local?.comfyUrl || "http://127.0.0.1:8188", videoUrl: local?.comfyUrl || "http://127.0.0.1:8188", ...values } : values;
  resetComfyCatalog();
  revision.value = provider?.revision ?? "";
  models.value = JSON.parse(JSON.stringify(provider?.models ?? []));
}, { immediate: true });
onBeforeUnmount(() => { testLoading?.abort(); comfyLoading?.abort(); });

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
    if (provider.id === "comfyUi") config.workflowModels = structuredClone(toRaw(workflowModels.value));
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
      if (providerId === "comfyUi" && Object.keys(changedWorkflows.value).length) {
        config.workflowModels = { ...(current?.workflowModels as Record<string, WorkflowProfile> | undefined), ...structuredClone(toRaw(changedWorkflows.value)) };
      }
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
  .comfyModelGroups { ul { margin: 0; padding-left: 20px; max-height: 220px; overflow-y: auto; } li { overflow-wrap: anywhere; line-height: 1.8; } }

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
