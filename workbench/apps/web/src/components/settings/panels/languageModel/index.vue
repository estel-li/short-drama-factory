<template>
  <el-form class="modelSettings" labelPosition="top" @submit.prevent="save">
    <p>DeepSeek 用于文本创作、剧本、分镜与 Agent 工具调用。</p>
    <el-form-item label="API 地址"><el-input modelValue="https://api.deepseek.com" readonly /></el-form-item>
    <el-form-item label="API Key"><el-input v-model="apiKey" type="password" showPassword autocomplete="off" :disabled="busy || saving" /></el-form-item>
    <el-space>
      <el-button :loading="busy" :disabled="!apiKey.trim() || saving" @click="refresh">读取模型列表</el-button>
      <el-button type="primary" nativeType="submit" :loading="saving" :disabled="busy">保存</el-button>
    </el-space>
    <p v-if="error" class="error" role="alert">{{ error }}</p>
    <div class="models"><el-tag v-for="model in models" :key="model.id">{{ model.label }}</el-tag></div>
    <el-text type="info">密钥保存在本机配置中。模型列表从 DeepSeek 读取，保存后可在 Agent 中选择。</el-text>
  </el-form>
</template>
<script setup lang="ts">
import { ref, watch } from "vue";
import { ElMessage } from "element-plus";
import http from "@/lib/http";
import { customProviders, saveSettings, type CustomProviderModel } from "@/stores/settings";
const props = defineProps<{ visible?: boolean }>();
const apiKey = ref("");
const models = ref<CustomProviderModel[]>([]);
const busy = ref(false);
const saving = ref(false);
const error = ref("");
watch(() => props.visible, () => {
  if (props.visible === false) return;
  const provider = customProviders.value.find(item => item.id.toLowerCase() === "deepseek");
  apiKey.value = provider?.apiKey ?? "";
  models.value = (provider?.models ?? []).map(model => ({ ...model }));
}, { immediate: true });
async function refresh() {
  busy.value = true; error.value = "";
  try {
    const result = await http<CustomProviderModel[]>({ method: "POST", url: "/api/providers/models", data: {
      apiUrl: "https://api.deepseek.com", protocol: "openai-completions", apiKey: apiKey.value.trim(),
    } });
    if (!result.length) throw new Error("DeepSeek 没有返回可用模型，已保留原列表");
    models.value = result;
  } catch (cause) { error.value = cause instanceof Error ? cause.message : "读取模型失败"; }
  finally { busy.value = false; }
}
async function save() {
  saving.value = true; error.value = "";
  try {
    await saveSettings(() => ({ customProviders: [{ id: "deepSeek", label: "DeepSeek", apiUrl: "https://api.deepseek.com",
      apiKey: apiKey.value.trim(), protocol: "openai-completions", models: models.value }] }));
    ElMessage.success("DeepSeek 配置已保存");
  } catch (cause) { error.value = cause instanceof Error ? cause.message : "保存失败"; }
  finally { saving.value = false; }
}
</script>
<style scoped lang="scss">
.modelSettings { max-width: 680px; .models { display: flex; flex-wrap: wrap; gap: 8px; margin: 20px 0; } .error { color: var(--el-color-danger); } }
</style>
