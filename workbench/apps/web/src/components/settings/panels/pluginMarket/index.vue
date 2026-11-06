<template>
  <div class="pluginMarket">
    <div class="marketToolbar">
      <div class="marketHeader">
        <nav class="marketNav" aria-label="插件列表">
          <button class="navButton" type="button" :aria-pressed="activeTab === 'installed'" @click="activeTab = 'installed'">已安装</button>
          <button class="navButton" type="button" :aria-pressed="activeTab === 'mcp'" @click="activeTab = 'mcp'">MCP</button>
          <button class="navButton" type="button" :aria-pressed="activeTab === 'ffmpeg'" @click="activeTab = 'ffmpeg'">FFmpeg</button>
        </nav>

      </div>
      <div v-if="activeTab === 'installed'" class="marketControls">
        <form class="marketSearch" role="search" @submit.prevent="applySearch">
          <el-input v-model="searchQuery" size="small" placeholder="搜索插件" aria-label="搜索插件" clearable @clear="applySearch" />
          <el-button size="small" nativeType="submit">搜索</el-button>
        </form>
        <div class="marketActions">
          <template v-if="activeTab === 'installed'">
            <el-button size="small" type="primary" :icon="IconUpload" :loading="installing" aria-label="安装本地插件" @click="pluginFileInput?.click()">
              安装插件
            </el-button>
            <input ref="pluginFileInput" type="file" :accept="agentMarketEnabled ? '.umd.js,.tool.js,.agent.zip,.zip,.md,.tar,.tar.gz,.tgz' : '.umd.js,.tool.js,.zip,.md,.tar,.tar.gz,.tgz'" hidden @change="installFile" />
            <template v-if="agentMarketEnabled && selectedType === 'agent'">
              <el-button size="small" :icon="IconLink" :disabled="loading || !canManageAgents" @click="agentConnectVisible = true">连接远程 Agent</el-button>
              <el-button size="small" :icon="IconSettings" :disabled="loading || !canManageAgents" @click="a2aSettingsVisible = true">A2A 服务</el-button>
            </template>
          </template>
        </div>
      </div>
      <div v-if="activeTab === 'installed'" class="marketFilters">
        <div class="typeFilters" role="group" aria-label="插件类型">
          <button class="filterButton" type="button" :aria-pressed="selectedType === 'all'" @click="selectedType = 'all'">
            全部
            <span v-if="activeTab === 'installed' && installedCounts.all !== undefined" class="filterCount">{{ installedCounts.all }}</span>
          </button>
          <button
            v-for="(category, type) in pluginTypes"
            :key="type"
            class="filterButton"
            type="button"
            :disabled="type === 'agent' && !agentMarketEnabled"
            :title="type === 'agent' && !agentMarketEnabled ? '测试阶段，暂未开放' : undefined"
            :aria-pressed="selectedType === type"
            @click="selectedType = type">
            {{ category.label }}
            <span v-if="activeTab === 'installed' && installedCounts[type] !== undefined" class="filterCount">{{ installedCounts[type] }}</span>
          </button>
        </div>
        <div class="filterOptions">
          <el-checkbox v-if="activeTab === 'installed'" v-model="hideBuiltin" class="builtinFilter" size="small">隐藏内置插件</el-checkbox>
        </div>
      </div>
    </div>

    <ffmpeg v-if="activeTab === 'ffmpeg'" :visible />
    <mcpServers v-else-if="activeTab === 'mcp'" :visible />
    <template v-else>
      <template v-if="activeTab === 'installed'">
        <el-alert v-for="message in visibleLoadErrors" :key="message" class="loadError" :title="message" type="error" :closable="false" showIcon />
      </template>

      <div
        class="pluginList"
        :aria-label="`${tabs[activeTab]}列表`"
        :aria-busy="loading">
        <el-card
          v-for="plugin in visiblePlugins"
          :key="plugin.key"
          class="pluginCard"
          :class="{ viewable: canViewPlugin(plugin) }"
          shadow="never"
          role="group"
          :aria-label="plugin.displayName"
          :aria-haspopup="canViewPlugin(plugin) ? 'dialog' : undefined"
          :tabindex="canViewPlugin(plugin) ? 0 : undefined"
          @click="openPlugin(plugin)"
          @keydown.enter.self.prevent="openPlugin(plugin)"
          @keydown.space.self.prevent="openPlugin(plugin)">
          <img v-if="plugin.type === 'node' && plugin.coverUrl" class="pluginCover" :src="plugin.coverUrl" :alt="`${plugin.displayName} 节点截图`" loading="lazy" referrerpolicy="no-referrer" />
          <div class="pluginHeader">
            <div class="pluginHeading">
              <h3 class="pluginName">
                <component :is="pluginTypes[plugin.type].icon" :size="18" aria-hidden="true" />
                <span class="pluginTitle">{{ plugin.displayName }}</span>
                <a
                  v-if="plugin.github && !plugin.github.includes('HBAI-Ltd/Toonflow-app')"
                  class="repoLink"
                  :href="plugin.github"
                  target="_blank"
                  rel="noopener noreferrer"
                  :aria-label="`${plugin.displayName} 的 GitHub`"
                  title="GitHub"
                  @click.stop>
                  <icon-external-link :size="14" aria-hidden="true" />
                </a>
              </h3>
              <span class="pluginId" :title="plugin.name">{{ plugin.name }}</span>
            </div>
            <div class="pluginTags">
              <el-tag v-if="plugin.demoVideoUrl" type="info" size="small" effect="plain">效果演示</el-tag>
              <el-tag v-if="plugin.builtin || installedByKey.get(`${plugin.type}:${plugin.name}`)?.builtin" type="info" size="small" effect="plain">内置</el-tag>
              <el-tag
                v-for="(tag, index) in plugin.tags"
                :key="index"
                class="pluginLabel"
                type="info"
                size="small"
                effect="plain"
                :style="getPluginTagStyle(tag.color)">{{ tag.text }}</el-tag>
              <el-tag :type="pluginTypes[plugin.type].tagType" size="small">{{ pluginTypes[plugin.type].label }}</el-tag>
            </div>
          </div>
          <p v-if="plugin.description" class="pluginDescription">{{ plugin.description }}</p>
          <el-text v-if="plugin.loadError" type="danger" size="small">{{ plugin.loadError }}</el-text>
          <div v-if="plugin.author || plugin.version" class="pluginMeta">
            <span v-if="plugin.author" class="pluginAuthor">{{ plugin.author === "Toonflow" ? "内置" : plugin.author }}</span>
            <span v-if="plugin.version" class="pluginVersion" type="info" size="small" effect="plain">v{{ plugin.version }}</span>
          </div>
          <div class="pluginFooter pluginControls" @click.stop>
            <label class="pluginToggle">
              <span>{{ plugin.enabled === false ? "已禁用" : "已启用" }}</span>
              <el-switch
                :modelValue="plugin.enabled !== false"
                size="small"
                :loading="pendingPlugins.has(plugin.key)"
                :disabled="!canEditPlugin(plugin) || loading || pendingPlugins.has(plugin.key)"
                :aria-label="`启用 ${plugin.displayName}`"
                @change="updatePlugin(plugin, 'setEnabled', $event === true)" />
            </label>
            <div class="pluginActions">
              <el-button
                v-if="plugin.type === 'node' || plugin.type === 'skill' || plugin.type === 'tool' || plugin.type === 'ext' || (plugin.type === 'agent' && plugin.kind === 'local')"
                size="small"
                :icon="IconShare"
                :loading="exportingPlugins.has(plugin.key)"
                :disabled="loading || pendingPlugins.has(plugin.key) || (plugin.type === 'tool' && !canManageTools) || (plugin.type === 'agent' && !canManageAgents) || (plugin.type === 'ext' && !plugin.canManage)"
                :aria-label="`导出分享 ${plugin.displayName}`"
                title="导出分享"
                @click="exportPlugin(plugin)" />
              <el-button v-if="plugin.type === 'agent' && plugin.kind === 'local'" size="small" :disabled="!canManageAgents || loading || pendingPlugins.has(plugin.key)" @click="selectedAgent = plugin">编辑</el-button>
              <el-button v-if="plugin.type === 'agent' && plugin.cardUrl" size="small" :icon="IconCopy" @click="copyCard(plugin.cardUrl)">Card</el-button>
              <el-badge v-if="(plugin.type === 'tool' || plugin.type === 'node' || plugin.type === 'ext') && plugin.configRules?.length" isDot :hidden="!hasMissingConfig(plugin)">
                <el-button
                  size="small"
                  :disabled="!canConfigurePlugin(plugin) || loading || pendingPlugins.has(plugin.key)"
                  :aria-label="`配置 ${plugin.displayName}${hasMissingConfig(plugin) ? '，有必填配置未填写' : ''}`"
                  @click="
                    selectedConfigPlugin = plugin;
                    configVisible = true;
                  ">
                  配置
                </el-button>
              </el-badge>
              <el-popconfirm
                v-if="!plugin.builtin"
                :title="`确定卸载“${plugin.displayName}”${plugin.type === 'skill' ? '及其附属文件' : ''}吗？`"
                width="280"
                confirmButtonText="卸载"
                cancelButtonText="取消"
                confirmButtonType="danger"
                hideIcon
                @confirm="updatePlugin(plugin, 'uninstall')">
                <template #reference>
                  <el-button
                    size="small"
                    :loading="pendingPlugins.has(plugin.key)"
                    :disabled="!canEditPlugin(plugin) || loading || pendingPlugins.has(plugin.key) || exportingPlugins.has(plugin.key)"
                    :aria-label="`卸载 ${plugin.displayName}`">
                    卸载
                  </el-button>
                </template>
              </el-popconfirm>
            </div>
          </div>
        </el-card>
      </div>
      <p v-if="loading" class="listStatus" role="status">正在加载插件…</p>
      <p v-else-if="!visiblePlugins.length && !visibleLoadErrors.length" class="listStatus">
        暂无符合条件的插件
      </p>
      <pluginConfigDialog v-if="selectedConfigPlugin" v-model="configVisible" :plugin="selectedConfigPlugin" :canManage="canConfigurePlugin(selectedConfigPlugin)" />
      <agentEditorDialog v-if="selectedAgent" :key="selectedAgent.key" :agent="selectedAgent" :canManage="canManageAgents" @saved="refreshInstalled" @closed="selectedAgent = undefined" />
      <agentConnectDialog v-if="agentConnectVisible" @saved="refreshInstalled" @closed="agentConnectVisible = false" />
      <a2aSettingsDialog v-if="a2aSettingsVisible" @saved="refreshInstalled" @closed="a2aSettingsVisible = false" />
      <skillEditorDialog
        v-if="selectedSkill"
        :key="selectedSkill.key"
        :skill="selectedSkill"
        @saved="refreshInstalled"
        @closed="selectedSkill = undefined" />
      <el-dialog
        v-if="selectedPlugin"
        v-model="detailsVisible"
        :title="selectedPlugin.displayName"
        width="min(800px, calc(100vw - 32px))"
        alignCenter
        appendToBody
        destroyOnClose
        @closed="selectedPlugin = undefined">
        <div class="pluginContent" tabindex="0" aria-label="插件详情">
          <div v-if="selectedPlugin.id !== undefined" class="detailMeta">
            <el-tag :type="pluginTypes[selectedPlugin.type].tagType" size="small">{{ pluginTypes[selectedPlugin.type].label }}</el-tag>
            <span>{{ selectedPlugin.name }}</span>
            <span v-if="selectedPlugin.version">v{{ selectedPlugin.version }}</span>
            <span v-if="selectedPlugin.author">{{ selectedPlugin.author === "Toonflow" ? "内置" : selectedPlugin.author }}</span>
          </div>
          <div v-if="selectedPlugin.tags?.length" class="detailLabels" aria-label="插件标签">
            <el-tag
              v-for="(tag, index) in selectedPlugin.tags"
              :key="index"
              type="info"
              size="small"
              effect="plain"
              :style="getPluginTagStyle(tag.color)">{{ tag.text }}</el-tag>
          </div>
          <p v-if="selectedPlugin.description && selectedPlugin.id !== undefined" class="detailDescription">{{ selectedPlugin.description }}</p>
          <img v-if="selectedPlugin.coverUrl" class="detailCover" :src="selectedPlugin.coverUrl" :alt="`${selectedPlugin.displayName} 插件封面`" referrerpolicy="no-referrer" />
          <section v-if="selectedPlugin.demoVideoUrl" class="detailDemo" aria-label="效果演示">
            <h3>效果演示</h3>
            <el-alert v-if="demoVideoFailed" title="演示视频加载失败，请重试" type="error" :closable="false" showIcon>
              <el-button size="small" @click="demoVideoFailed = false">重试</el-button>
            </el-alert>
            <videoPlayer
              v-else
              :key="selectedPlugin.demoVideoUrl"
              class="demoPlayer"
              :src="selectedPlugin.demoVideoUrl"
              :label="`${selectedPlugin.displayName} 效果演示`"
              :active="detailsVisible && visible"
              @error="demoVideoFailed = true" />
          </section>
          <messageMarkdown v-if="selectedPlugin.readme" :content="selectedPlugin.readme" />
        </div>
      </el-dialog>
    </template>
  </div>
</template>

<script setup lang="ts">
import { translate } from "@toonflow/i18n/vue";
import axios from "axios";
import { computed, defineAsyncComponent, markRaw, onMounted, onBeforeUnmount, ref, watch } from "vue";
import { IconBox, IconBook, IconTool, IconFileText, IconExternalLink, IconSparkles2, IconUpload, IconCloudUpload, IconShare, IconStar, IconStarFilled, IconLink, IconSettings, IconCopy } from "@tabler/icons-vue";
import { ElMessage, ElMessageBox } from "element-plus";
import videoPlayer from "@/components/videoPlayer.vue";
import saveFile from "@/lib/saveFile";
import { writeClipboardText } from "@/lib/clipboard";
import pluginConfigDialog from "./pluginConfigDialog.vue";
import skillEditorDialog from "./skillEditorDialog.vue";
import ffmpeg from "./ffmpeg.vue";
import mcpServers from "./mcpServers.vue";
import agentEditorDialog from "./agentEditorDialog.vue";
import agentConnectDialog from "./agentConnectDialog.vue";
import a2aSettingsDialog from "./a2aSettingsDialog.vue";
import type { Plugin, PluginType } from "./types";
import { installPluginFile } from "../../installPluginFile";

const { visible = true } = defineProps<{ visible?: boolean }>();
// ACT: Agent 插件市场仍在测试，暂时关闭入口。
const agentMarketEnabled = false;
const pluginTypes = {
  node: { label: "节点", path: "nodes", icon: IconBox, tagType: "primary" },
  ext: { label: "文件扩展", path: "ext", icon: IconFileText, tagType: "info" },
  skill: { label: "技能", path: "skills", icon: IconBook, tagType: "success" },
  tool: { label: "工具", path: "tools", icon: IconTool, tagType: "warning" },
  agent: { label: "Agent", path: agentMarketEnabled ? "agents" : null, icon: IconSparkles2, tagType: "danger" },
} as const;
const tabs = { get installed() { return translate("已安装"); }, mcp: "MCP", ffmpeg: "FFmpeg" } as const;
const activeTab = ref<keyof typeof tabs>("installed");

const selectedType = ref<PluginType | "all">("all");
const installedPlugins = ref<Plugin[]>([]);
const hideBuiltin = ref(false);
const filteredInstalledPlugins = computed(() => installedPlugins.value.filter(plugin => !(plugin.type === "skill" && ["workflow", "v118workflow"].includes(plugin.name)) && (!hideBuiltin.value || !plugin.builtin)));
const installedByKey = computed(() => new Map(installedPlugins.value.map((plugin) => [plugin.key, plugin])));
const loading = ref(false);
const loadErrors = ref<Partial<Record<PluginType, string>>>({});
const canManageTools = ref(false);
const canManageAgents = ref(false);
const selectedAgent = ref<Plugin>();
const agentConnectVisible = ref(false);
const a2aSettingsVisible = ref(false);
const pendingPlugins = ref(new Set<string>());
const exportingPlugins = ref(new Set<string>());
const pluginFileInput = ref<HTMLInputElement>();
const installing = ref(false);
const refreshKey = ref(0);
const refreshInstalled = () => {
  refreshKey.value++;
};
onMounted(() => window.addEventListener("toonflow:plugin-installed", refreshInstalled));
onBeforeUnmount(() => window.removeEventListener("toonflow:plugin-installed", refreshInstalled));
const selectedConfigPlugin = ref<Plugin>();
const configVisible = ref(false);
const selectedPlugin = ref<Plugin>();
const selectedSkill = ref<Plugin>();
const detailsVisible = ref(false);
const demoVideoFailed = ref(false);
const messageMarkdown = defineAsyncComponent(() => import("@/components/messageMarkdown.vue"));
const requestHeaders = { "x-toonflow-workspace": "1" };

function getPluginTagStyle(color: string) {
  const backgroundColor = /^#[0-9a-f]{6}(?:[0-9a-f]{2})?$/i.test(color) ? color : "#0052D9";
  return { backgroundColor, borderColor: backgroundColor, color: "#FFFFFF" };
}

const searchQuery = ref("");
const appliedQuery = ref("");
const installedCounts = computed(() => {
  const counts: Partial<Record<PluginType | "all", number>> = {};
  if (loading.value) return counts;
  if (!Object.keys(loadErrors.value).length) counts.all = filteredInstalledPlugins.value.length;
  for (const type of Object.keys(pluginTypes) as PluginType[]) {
    if (!loadErrors.value[type]) counts[type] = filteredInstalledPlugins.value.filter((plugin) => plugin.type === type).length;
  }
  return counts;
});
const visibleLoadErrors = computed(() =>
  Object.entries(loadErrors.value)
    .filter(([type]) => selectedType.value === "all" || type === selectedType.value)
    .map(([, message]) => message)
);
const visiblePlugins = computed(() => {
  return filteredInstalledPlugins.value.filter(
    (plugin) =>
      (selectedType.value === "all" || plugin.type === selectedType.value) &&
      [plugin.name, plugin.displayName, plugin.author, plugin.description].some((value) =>
        value?.toLowerCase().includes(appliedQuery.value.toLowerCase())
      )
  );
});
function canViewPlugin(plugin: Plugin) {
  return activeTab.value === "installed" && (plugin.type === "skill" || (plugin.type === "agent" && plugin.kind === "local" && canManageAgents.value))
    ? !loading.value && !pendingPlugins.value.has(plugin.key)
    : !!plugin.readme?.trim();
}

function openPlugin(plugin: Plugin) {
  if (!canViewPlugin(plugin)) return;
  if (activeTab.value === "installed" && plugin.type === "agent" && plugin.kind === "local" && canManageAgents.value) {
    selectedAgent.value = plugin;
    return;
  }
  if (activeTab.value === "installed" && plugin.type === "skill") {
    selectedSkill.value = plugin;
    return;
  }
  demoVideoFailed.value = false;
  selectedPlugin.value = plugin;
  detailsVisible.value = true;
}

function canConfigurePlugin(plugin: Plugin) {
  return plugin.type === "node" || plugin.type === "ext" ? plugin.canConfigure === true : plugin.type === "tool" && canManageTools.value;
}

function hasMissingConfig(plugin: Plugin) {
  if (!canConfigurePlugin(plugin)) return false;
  return (plugin.configRules ?? []).some((rule) => {
    const required = rule.required === true || (Array.isArray(rule.validate) && rule.validate.some((validation) =>
      validation && typeof validation === "object" && "required" in validation && validation.required === true));
    if (!required || typeof rule.field !== "string") return false;
    const config = plugin.config ?? {};
    const value = Object.hasOwn(config, rule.field) ? config[rule.field] : rule.value;
    return value == null || (typeof value === "string" && !value.trim()) || (Array.isArray(value) && !value.length);
  });
}

watch(
  () => [visible, activeTab.value, refreshKey.value],
  async (_value, _previous, onCleanup) => {
    if (!visible || activeTab.value !== "installed") return;
    const controller = new AbortController();
    onCleanup(() => controller.abort());
    loading.value = true;
    loadErrors.value = {};
    canManageTools.value = false;
    canManageAgents.value = false;
    installedPlugins.value = [];
    const results = await Promise.all(
      (Object.keys(pluginTypes) as PluginType[]).map(async (type) => {
        const category = pluginTypes[type];
        if (!category.path) return [];
        try {
          const { data } = await axios.get(`/api/${category.path}/${type === "ext" ? "list" : "get"}`, {
            signal: controller.signal,
            headers: { ...requestHeaders, "Cache-Control": "no-cache" },
          });
          const items = type === "tool" ? data.data?.tools : type === "agent" ? data.data?.agents : data.data;
          if (data.code !== 200 || !Array.isArray(items) || items.some((item) => !item || typeof item.name !== "string"))
            throw new Error(`${category.label}列表格式错误`);
          if (controller.signal.aborted) return [];
          if (type === "tool") canManageTools.value = data.data.canManage === true;
          if (type === "agent") canManageAgents.value = data.data.canManage === true;
          return items.map((item) => ({
            ...item,
            type,
            key: `${type}:${item.name}`,
            displayName: item.displayName || item.name,
            configRules: markRaw(item.configRules ?? []),
          } as Plugin));
        } catch (error) {
          if (!controller.signal.aborted) loadErrors.value[type] = errorMessage(error, `加载${category.label}失败，请重新打开列表重试`);
          return [];
        }
      })
    );
    if (controller.signal.aborted) return;
    installedPlugins.value = results.flat().sort((left, right) => (right.installedAt ?? 0) - (left.installedAt ?? 0));
    loading.value = false;
  },
  { immediate: true }
);

function applySearch() {
  appliedQuery.value = searchQuery.value.trim();
}

function errorMessage(error: unknown, fallback: string) {
  if (error instanceof Error && "status" in error && error.status === 401) return translate("账号登录已失效，请到账号与余额重新登录");
  if (axios.isAxiosError(error)) return typeof error.response?.data?.message === "string" ? error.response.data.message : fallback;
  return error instanceof Error ? error.message : fallback;
}

async function copyCard(url: string) {
  try {
    await writeClipboardText(url);
    ElMessage.success("Agent Card 地址已复制");
  } catch {
    await ElMessageBox.alert(url, "Agent Card 地址", { confirmButtonText: "关闭" }).catch(() => {});
  }
}

function canEditPlugin(plugin: Plugin) {
  return (
    activeTab.value === "installed" &&
    (plugin.type === "node" || plugin.type === "skill" || (plugin.type === "ext" && plugin.canManage === true) || (plugin.type === "tool" && canManageTools.value) || (plugin.type === "agent" && canManageAgents.value))
  );
}

async function installFile(event: Event) {
  const input = event.target as HTMLInputElement;
  const file = input.files?.[0];
  input.value = "";
  if (!file || installing.value) return;
  installing.value = true;
  try {
    const type = /\.agent\.zip$/i.test(file.name)
      ? "agent"
      : /^ext-[a-z][a-zA-Z0-9]*\.umd\.js$/.test(file.name)
      ? "ext"
      : /\.umd\.js$/i.test(file.name)
      ? "node"
      : /\.tool\.js$/i.test(file.name)
      ? "tool"
      : /\.(zip|md|tar|tar\.gz|tgz)$/i.test(file.name)
      ? "skill"
      : undefined;
    if (!type) throw new Error("不支持这个安装文件。支持的格式：文件扩展 ext-*.umd.js；Agent .agent.zip；节点 .umd.js；工具 .tool.js；技能 .zip、.md、.tar、.tar.gz、.tgz。");
    if (type === "agent" && !agentMarketEnabled) throw new Error("Agent 功能处于测试阶段，暂未开放安装");
    await installPluginFile(type, file);
    ElMessage.success(`${pluginTypes[type].label}已安装`);
  } catch (error) {
    ElMessage.error(errorMessage(error, "安装插件失败，请重试"));
  } finally {
    installing.value = false;
  }
}

async function exportPlugin(plugin: Plugin) {
  if (
    activeTab.value !== "installed" ||
    (plugin.type === "agent" && (plugin.kind !== "local" || !canManageAgents.value)) ||
    exportingPlugins.value.has(plugin.key) ||
    pendingPlugins.value.has(plugin.key) ||
    loading.value ||
    (plugin.type === "tool" && !canManageTools.value) ||
    (plugin.type === "ext" && !plugin.canManage)
  )
    return;
  exportingPlugins.value.add(plugin.key);
  try {
    const fileName = `${plugin.name}.${plugin.type === "node" || plugin.type === "ext" ? "umd.js" : plugin.type === "tool" ? "tool.js" : plugin.type === "agent" ? "agent.zip" : "zip"}`;
    await saveFile(
      () =>
        axios
          .get<Blob>("/api/plugins/export", { params: { type: plugin.type, name: plugin.name }, responseType: "blob", headers: requestHeaders })
          .then(({ data }) => data),
      fileName
    );
  } catch (error) {
    let message = errorMessage(error, "导出插件失败，请重试");
    if (axios.isAxiosError(error) && error.response?.data instanceof Blob) {
      const data = await error.response.data
        .text()
        .then(JSON.parse)
        .catch(() => null);
      if (typeof data?.message === "string") message = data.message;
    }
    ElMessage.error(message);
  } finally {
    exportingPlugins.value.delete(plugin.key);
  }
}

async function updatePlugin(plugin: Plugin, action: "setEnabled" | "uninstall", enabled?: boolean) {
  if (
    !canEditPlugin(plugin) ||
    loading.value ||
    pendingPlugins.value.has(plugin.key) ||
    exportingPlugins.value.has(plugin.key) ||
    (action === "uninstall" && plugin.builtin)
  )
    return;
  pendingPlugins.value.add(plugin.key);
  const actionLabel = action === "uninstall" ? translate("卸载插件") : translate("更新插件状态");
  try {
    const url = `/api/${pluginTypes[plugin.type].path}/${action}`;
    const { data } =
      action === "uninstall"
        ? await axios.delete(url, { data: { name: plugin.name }, headers: requestHeaders })
        : await axios.put(url, { name: plugin.name, enabled }, { headers: requestHeaders });
    if (data.code !== 200) throw new Error(data.message || `${actionLabel}失败`);
    if (action === "uninstall") {
      installedPlugins.value = installedPlugins.value.filter((item) => item.key !== plugin.key);
      if (selectedSkill.value?.key === plugin.key) selectedSkill.value = undefined;
      if (selectedAgent.value?.key === plugin.key) selectedAgent.value = undefined;
      if (selectedConfigPlugin.value?.key === plugin.key) {
        configVisible.value = false;
        selectedConfigPlugin.value = undefined;
      }
      if (selectedPlugin.value?.key === plugin.key) {
        detailsVisible.value = false;
        selectedPlugin.value = undefined;
      }
      ElMessage.success("插件已卸载");
    } else plugin.enabled = enabled;
    if (plugin.type === "node")
      window.dispatchEvent(new CustomEvent("toonflow:plugin-installed", { detail: { type: plugin.type, name: plugin.name } }));
    if (plugin.type === "ext") window.dispatchEvent(new CustomEvent("toonflow:ext-updated", { detail: { name: plugin.name } }));
  } catch (error) {
    ElMessage.error(errorMessage(error, `${actionLabel}失败，请重试`));
  } finally {
    pendingPlugins.value.delete(plugin.key);
  }
}
</script>

<style lang="scss" scoped>
.pluginMarket {
  .marketToolbar {
    position: sticky;
    top: 0;
    z-index: 1;
    display: flex;
    flex-direction: column;
    gap: 16px;
    padding-bottom: 20px;
    background: var(--el-bg-color);

    .el-button { margin-left: 0; }

    .marketHeader {
      display: flex;
      align-items: center;
      justify-content: space-between;
      flex-wrap: wrap;
      gap: 12px 24px;
      padding-bottom: 12px;
      border-bottom: 1px solid var(--el-border-color-lighter);

      .marketNav {
        display: flex;
        flex-wrap: wrap;
        gap: 8px 24px;

        .navButton {
          position: relative;
          display: flex;
          align-items: center;
          gap: 6px;
          min-height: 30px;
          padding: 0 0 6px;
          border: 0;
          background: transparent;
          color: var(--el-text-color-secondary);
          font: inherit;
          cursor: pointer;

          &[aria-pressed="true"] {
            color: var(--el-text-color-primary);
            font-weight: 600;
            &::after {
              position: absolute;
              right: 0;
              bottom: 0;
              left: 0;
              height: 2px;
              border-radius: 2px;
              background: currentColor;
              content: "";
            }
          }
          &:hover {
            color: var(--el-text-color-primary);
          }
          &:focus-visible {
            outline: 2px solid var(--el-color-primary);
            outline-offset: 3px;
          }
        }
      }

      .marketLinks {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        margin-left: auto;
      }
    }

    .marketControls {
      display: flex;
      align-items: center;
      flex-wrap: wrap;
      gap: 12px 24px;

      .marketSearch {
        display: flex;
        flex: 1 1 220px;
        min-width: 0;
        max-width: 400px;
        gap: 8px;

        .el-input { flex: 1; min-width: 0; }
      }

      .marketActions {
        display: flex;
        align-items: center;
        justify-content: flex-end;
        flex-wrap: wrap;
        max-width: 100%;
        gap: 8px;
        margin-left: auto;
      }
    }

    .marketFilters {
      display: flex;
      align-items: center;
      justify-content: space-between;
      flex-wrap: wrap;
      gap: 12px 24px;

      .typeFilters {
        display: flex;
        flex-wrap: wrap;
        gap: 6px;
      }

      .filterOptions {
        display: flex;
        align-items: center;
        flex-wrap: wrap;
        gap: 12px;
        margin-left: auto;

        .personalFilters {
          display: flex;
          gap: 6px;
        }

        .builtinFilter { margin: 0; }
      }

      .filterButton {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 5px 12px;
        border: 0;
        border-radius: var(--el-border-radius-base);
        background: transparent;
        color: var(--el-text-color-secondary);
        font: inherit;
        font-size: 12px;
        cursor: pointer;

        .filterCount {
          padding: 1px 6px;
          border-radius: 6px;
          background: var(--el-fill-color);
          font-size: 11px;
          font-weight: 500;
        }

        &:hover:not(:disabled) {
          background: var(--el-fill-color-light);
        }
        &:disabled {
          color: var(--el-text-color-disabled);
          cursor: not-allowed;
        }
        &[aria-pressed="true"] {
          background: var(--el-color-primary-light-9);
          color: var(--el-color-primary);
        }
        &:focus-visible {
          outline: 2px solid var(--el-color-primary);
          outline-offset: 2px;
        }
      }
    }
  }

  .loadError {
    margin-bottom: 12px;
  }

  .pluginList {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(min(100%, 240px), 1fr));
    gap: 16px;
    padding-bottom: 4px;

    .pluginCard {
      min-width: 0;

      .pluginCover {
        display: block;
        width: 100%;
        aspect-ratio: 16 / 9;
        margin-bottom: 12px;
        object-fit: contain;
        background: var(--el-fill-color-light);
        border-radius: var(--el-border-radius-base);
      }

      &.viewable {
        cursor: pointer;

        &:focus-visible {
          outline: 2px solid var(--el-color-primary);
          outline-offset: 2px;
        }
      }

      :deep(.el-card__body) {
        display: flex;
        flex-direction: column;
        height: 100%;
        padding: 12px;
        box-sizing: border-box;
      }

      .pluginHeader {
        display: flex;
        align-items: flex-start;
        justify-content: space-between;
        gap: 12px;

        .pluginTags {
          display: flex;
          flex-wrap: wrap;
          justify-content: flex-end;
          gap: 4px;
          flex-shrink: 0;
          max-width: 50%;

          .pluginLabel {
            max-width: 100%;
            height: auto;
            min-height: 20px;
            white-space: normal;
            overflow-wrap: anywhere;
          }
        }

        .pluginHeading {
          min-width: 0;

          .pluginName {
            display: flex;
            align-items: center;
            gap: 6px;
            min-width: 0;
            margin: 0;
            font-size: 14px;
            font-weight: 600;
            overflow-wrap: anywhere;

            .pluginTitle {
              min-width: 0;
            }

            svg {
              flex-shrink: 0;
            }
            .repoLink {
              display: inline-flex;
              flex-shrink: 0;
              color: var(--el-text-color-secondary);
              &:hover {
                color: var(--el-color-primary);
              }
              &:focus-visible {
                outline: 2px solid var(--el-color-primary);
                outline-offset: 2px;
              }
            }
          }

          .pluginId {
            display: block;
            margin-top: 6px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
            font-size: 12px;
            line-height: 1.5;
            color: var(--el-text-color-placeholder);
          }
        }
      }

      .pluginMeta {
        display: flex;
        align-items: center;
        justify-content: space-between;
        flex-wrap: wrap;
        gap: 8px 12px;
        margin-top: 12px;
        font-size: 12px;
        line-height: 1.5;
        color: var(--el-text-color-secondary);
        overflow-wrap: anywhere;

        .pluginAuthor {
          flex: 1;
          min-width: 0;
        }

        .pluginVersion {
          flex-shrink: 0;
          margin-left: auto;
        }
      }
      .pluginDescription {
        display: -webkit-box;
        -webkit-box-orient: vertical;
        -webkit-line-clamp: 3;
        overflow: hidden;
        margin: 10px 0 0;
        font-size: 13px;
        line-height: 1.6;
        color: var(--el-text-color-regular);
        overflow-wrap: anywhere;
      }

      .reviewStatus {
        display: flex;
        flex-direction: column;
        align-items: flex-start;
        gap: 8px;
        margin-top: 12px;
        text-align: left;

        &.rejected {
          padding: 10px;
          border-radius: 6px;
          background: var(--el-color-danger-light-9);
        }

        .reviewReason {
          margin: 0;
          font-size: 12px;
          line-height: 1.6;
          color: var(--el-text-color-regular);
          white-space: pre-wrap;
          overflow-wrap: anywhere;

          span {
            display: block;
            margin-bottom: 2px;
            color: var(--el-color-danger);
          }
        }
      }

      .pluginFooter {
        display: flex;
        align-items: center;
        flex-wrap: wrap;
        gap: 8px;
        margin-top: auto;
        padding-top: 12px;

        &.pluginControls {
          align-items: stretch;
          flex-direction: column;
          gap: 12px;

          &::before {
            border-top: 1px solid var(--el-border-color-lighter);
            content: "";
          }
        }

        .pluginToggle {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 12px;
          color: var(--el-text-color-secondary);
          font-size: 12px;
          cursor: pointer;

          > .el-switch {
            flex-shrink: 0;
          }
        }
        .pluginActions {
          display: flex;
          align-items: center;
          flex-wrap: wrap;
          justify-content: flex-end;
          gap: 8px;
          max-width: 100%;
          min-width: 0;
          margin-left: auto;
          .el-button {
            margin-left: 0;
          }
          .collectionIcon {
            color: var(--el-text-color-secondary);
            cursor: pointer;

            &[aria-pressed="true"] {
              color: #f5c518;
            }
            &[aria-disabled="true"] {
              opacity: 0.5;
              cursor: wait;
            }
            &:focus-visible {
              outline: 2px solid currentColor;
              outline-offset: 3px;
            }
          }
        }
      }
    }
  }

  .marketPagination {
    justify-content: center;
    margin-top: 16px;
  }

  .listStatus {
    margin: 24px 0;
    color: var(--el-text-color-secondary);
    text-align: center;
  }
}

.pluginContent {
  max-height: min(65vh, calc(100dvh - 160px));
  overflow: auto;
  overflow-wrap: anywhere;
  padding: 0 4px;
  font-size: 14px;
  line-height: 1.7;

  .detailMeta {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 8px 16px;
    margin-bottom: 16px;
    color: var(--el-text-color-secondary);
    font-size: 12px;
  }

  .detailLabels {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    margin-bottom: 16px;

    .el-tag {
      max-width: 100%;
      height: auto;
      min-height: 20px;
      white-space: normal;
      overflow-wrap: anywhere;
    }
  }

  .detailDescription {
    margin: 0 0 16px;
    white-space: pre-wrap;
  }

  .detailCover {
    display: block;
    width: 100%;
    max-height: 50vh;
    margin-bottom: 16px;
    border-radius: var(--el-border-radius-base);
    object-fit: contain;
  }

  .detailDemo {
    margin-bottom: 16px;

    h3 {
      margin: 0 0 12px;
      font-size: 14px;
    }

    .demoPlayer {
      height: auto;
      border-radius: var(--el-border-radius-base);
      overflow: hidden;
    }
  }
}
</style>
