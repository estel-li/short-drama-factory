<template>
  <section class="agentPermissions" aria-label="Agent 执行权限">
    <h3>Agent 执行权限</h3>
    <p>默认全部关闭，仅在独立运行的服务器本机设置。开启后会扩大 Agent 的自动操作范围；关闭恢复原有检查，已开始的操作不会撤销。</p>
    <div class="permissionRow">
      <div>
        <label :for="`${controlId}-approval`">自动批准</label>
        <p>自动批准单项确认，包括阶段、算力消耗和插件安装。缺信息、选剧情等问题仍需回答；结果会注明“自动批准”。</p>
      </div>
      <el-switch :id="`${controlId}-approval`" v-model="draft.autoApprove" :disabled="saving || unavailable" aria-label="自动批准" />
    </div>
    <div class="permissionRow">
      <div>
        <label :for="`${controlId}-files`">允许工作区外文件访问</label>
        <p>文件工具可读写、重命名和删除当前工作区以外的文件，范围取决于服务进程的系统权限。保留根目录、符号链接和文件冲突保护。</p>
      </div>
      <el-switch :id="`${controlId}-files`" v-model="draft.allowOutsideWorkspace" :disabled="saving || unavailable" aria-label="允许工作区外文件访问" />
    </div>
    <div class="permissionRow">
      <div>
        <label :for="`${controlId}-tools`">绕过节点工具权限拦截</label>
        <p>忽略画布顶部图片、视频和音频工具的禁用开关，恢复其目录展示与调用。原开关设置保留，关闭此项后重新生效；不改变模型服务自身的回复策略。</p>
      </div>
      <el-switch :id="`${controlId}-tools`" v-model="draft.bypassNodeToolPermissions" :disabled="saving || unavailable" aria-label="绕过节点工具权限拦截" />
    </div>
    <p>保存后新的工具调用读取权限，新的回复读取对应提示词，其他已打开页面需刷新。等待中的提问需手动处理；停止与取消、模型参数和生产任务校验保持有效。</p>
    <el-text v-if="error" type="danger" role="alert">{{ error }}</el-text>
    <div class="permissionActions">
      <el-button :disabled="saving || unavailable" @click="draft = agentPermissionsSchema.parse({})">全部关闭</el-button>
      <el-button type="primary" :loading="saving" :disabled="unavailable" @click="save">保存执行权限</el-button>
    </div>
  </section>
</template>

<script setup lang="ts">
import axios from "axios";
import { computed, ref, useId, watch } from "vue";
import { ElMessage } from "element-plus";
import { agentPermissionsSchema } from "@toonflow/server/agentPermissions";
import { agentDeveloperPermissions, multiTenantEnabled, saveSettings } from "@/stores/settings";
import { isRemoteConnection } from "@/lib/platform";

const controlId = useId();
const draft = ref({ ...agentDeveloperPermissions.value });
const saving = ref(false);
const error = ref("");
const unavailable = computed(() => isRemoteConnection || multiTenantEnabled.value);
watch(agentDeveloperPermissions, value => { if (!saving.value) draft.value = { ...value }; });

async function save() {
  if (saving.value || unavailable.value) return;
  const permissions = agentPermissionsSchema.parse(draft.value);
  saving.value = true;
  error.value = "";
  try {
    await saveSettings(() => ({ agentDeveloperPermissions: permissions }));
    draft.value = { ...agentDeveloperPermissions.value };
    ElMessage.success("Agent 执行权限已保存");
  } catch (cause) {
    error.value = axios.isAxiosError<{ message?: string }>(cause) ? cause.response?.data?.message || "保存失败，请重试" : cause instanceof Error ? cause.message : "保存失败，请重试";
  } finally { saving.value = false; }
}
</script>

<style lang="scss" scoped>
.agentPermissions {
  padding: 16px;
  border: 1px solid var(--el-border-color);
  border-radius: 8px;
  h3 { margin: 0 0 8px; }
  p { margin: 4px 0; color: var(--el-text-color-secondary); font-size: 13px; line-height: 1.6; }
  .permissionRow {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 20px;
    margin: 16px 0;
    label { font-weight: 600; cursor: pointer; }
  }
  .permissionActions { display: flex; justify-content: flex-end; flex-wrap: wrap; gap: 8px; margin-top: 12px; }
}
</style>
