<template>
  <div class="modelSettings">
    <p>默认优先使用 DeepSeek，也可添加其他供应商，用于文本创作、剧本、分镜与 Agent 工具调用。</p>
    <div class="providerPicker">
      <el-select v-model="selectedPreset" aria-label="文本模型供应商" filterable>
        <el-option v-for="item in languageProviders" :key="item.id" :value="item.id" :label="item.id === 'deepSeek' ? `${item.label}（默认）` : item.label" />
        <el-option value="custom" label="自定义供应商" />
      </el-select>
      <el-button type="primary" @click="configureSelected">配置供应商</el-button>
    </div>
    <el-text type="info">预设会填写 API 地址和协议；模型可连接读取后勾选，也可手动填写。保存后在 Agent 的模型菜单中切换。</el-text>
    <el-card v-for="item in customProviders" :key="item.id" class="providerCard" shadow="never">
      <div class="providerHeading">
        <div>
          <strong>{{ item.label }}</strong>
          <el-tag v-if="item.id.toLowerCase() === 'deepseek'" size="small">默认</el-tag>
        </div>
        <el-button :aria-label="`编辑 ${item.label}`" @click="editProvider(item)">编辑</el-button>
      </div>
      <p class="providerAddress">{{ item.apiUrl }}</p>
      <el-text type="info">{{ item.models.length }} 个模型 · {{ item.protocol }}</el-text>
    </el-card>
    <addCustomProviderDialog v-model="editorVisible" :provider="editingProvider" :preset="addingPreset" />
  </div>
</template>

<script setup lang="ts">
import { ref } from "vue";
import { languageProviders } from "@toonflow/providers";
import { customProviders, type CustomProvider } from "@/stores/settings";
import addCustomProviderDialog from "./addCustomProviderDialog.vue";

defineProps<{ visible?: boolean }>();
const selectedPreset = ref<string>(languageProviders[0]?.id ?? "custom");
const editorVisible = ref(false);
const editingProvider = ref<CustomProvider>();
const addingPreset = ref<CustomProvider>();

function editProvider(provider: CustomProvider) {
  addingPreset.value = undefined;
  editingProvider.value = provider;
  editorVisible.value = true;
}

function configureSelected() {
  const existing = customProviders.value.find(provider => provider.id.toLowerCase() === selectedPreset.value.toLowerCase());
  if (existing && selectedPreset.value !== "custom") { editProvider(existing); return; }
  const preset = languageProviders.find(provider => provider.id === selectedPreset.value);
  editingProvider.value = undefined;
  addingPreset.value = preset ? {
    id: preset.id, label: preset.label, icon: preset.icon, apiUrl: preset.apiUrl, protocol: preset.protocol,
    apiKey: "", models: [],
  } : undefined;
  editorVisible.value = true;
}
</script>

<style scoped lang="scss">
.modelSettings {
  display: grid; gap: 16px; max-width: 800px;
  p { margin: 0; line-height: 1.7; }
  .providerPicker { display: flex; gap: 12px; .el-select { flex: 1; min-width: 0; } }
  .providerCard {
    .providerHeading { display: flex; align-items: center; justify-content: space-between; gap: 12px; > div { display: flex; align-items: center; flex-wrap: wrap; gap: 8px; } }
    .providerAddress { margin: 10px 0; overflow-wrap: anywhere; }
  }
}
</style>
