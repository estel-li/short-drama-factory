<template>
  <el-form class="mediaSettings" labelPosition="top" @submit.prevent="save">
    <h3>H3 工厂与独立工作流节点</h3>
    <p>此连接用于独立的 ComfyUI 工作流节点。图片／视频节点使用上方对应模型的连接配置。H3 工厂负责分镜计划、缓存、续跑和成片交付。</p>
    <el-form-item label="ComfyUI 地址"><el-input v-model="config.comfyUrl" placeholder="http://127.0.0.1:8188" :disabled="saving || loading" /></el-form-item>
    <el-form-item label="H3 工厂地址"><el-input v-model="config.factoryUrl" placeholder="http://127.0.0.1:8765" :disabled="saving || loading" /></el-form-item>
    <el-form-item label="实际运行的工厂目录"><el-input v-model="config.applicationRoot" placeholder="填写运行实例的完整目录" :disabled="saving || loading" /></el-form-item>
    <el-space>
      <el-button type="primary" nativeType="submit" :loading="saving" :disabled="loading">保存连接</el-button>
      <el-button :loading="checking" :disabled="saving || loading" @click="check">检查已保存连接</el-button>
    </el-space>
    <p v-if="error" class="error" role="alert">{{ error }}</p>
    <p v-if="status" role="status">{{ status }}</p>
    <el-text type="info">ComfyUI 支持本机或局域网 HTTP(S) 地址，例如 http://192.168.1.4:8188。H3 工厂仍通过现有 SSH 隧道核对实例身份。</el-text>
  </el-form>
</template>
<script setup lang="ts">
import { ref, watch } from "vue";
import { ElMessage } from "element-plus";
import http from "@/lib/http";
import { saveSettings } from "@/stores/settings";
const props = defineProps<{ visible?: boolean }>();
const config = ref({ comfyUrl: "http://127.0.0.1:8188", factoryUrl: "http://127.0.0.1:8765", applicationRoot: "" });
const loading = ref(true);
const saving = ref(false);
const checking = ref(false);
const error = ref("");
const status = ref("");
watch(() => props.visible, async () => {
  if (props.visible === false) return;
  loading.value = true;
  try { config.value = await http({ method: "GET", url: "/api/localModels/config" }); }
  catch (cause) { error.value = cause instanceof Error ? cause.message : "读取连接失败"; }
  finally { loading.value = false; }
}, { immediate: true });
async function save() {
  saving.value = true; error.value = ""; status.value = "";
  try { await saveSettings(() => ({ localModels: { ...config.value } })); ElMessage.success("本地媒体连接已保存"); }
  catch (cause) { error.value = cause instanceof Error ? cause.message : "保存失败"; }
  finally { saving.value = false; }
}
async function check() {
  checking.value = true; error.value = "";
  try {
    const result = await http<{ comfy: string; factory: string }>({ method: "GET", url: "/api/localModels/status" });
    status.value = `ComfyUI：${result.comfy}；H3 工厂：${result.factory}`;
  } catch (cause) { error.value = cause instanceof Error ? cause.message : "连接检查失败"; }
  finally { checking.value = false; }
}
</script>
<style scoped lang="scss">
.mediaSettings { max-width: 680px; p { line-height: 1.7; } .error { color: var(--el-color-danger); } }
</style>
