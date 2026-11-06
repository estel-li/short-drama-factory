<template>
  <div ref="menu" class="referenceMenu nodrag nopan nowheel" :style="menuStyle" role="dialog" aria-label="引用素材" :aria-busy="busy" @pointerdown.stop @mousedown.stop @keydown="handleKeydown">
    <label class="searchBox">
      <icon-search :size="16" aria-hidden="true" />
      <input v-model="search" type="search" placeholder="搜索" aria-label="搜索参考和素材" :disabled="busy" @focus="activeKey = ''" />
    </label>
    <div class="menuBody" @scroll="updatePosition">
      <section v-if="!search.trim() || matchingReferences.length" class="referenceSection" aria-label="参考引用">
        <button v-for="item in matchingReferences" :key="item.id" type="button" class="menuItem" :class="{ active: activeKey === `reference:${item.id}` }" :data-key="`reference:${item.id}`" :title="item.label || item.name" :disabled="busy" @mousedown.prevent @mouseenter="activeGroup = undefined; activeKey = `reference:${item.id}`" @focus="activeGroup = undefined; activeKey = `reference:${item.id}`" @click="emit('select', item.id)">
          <promptReferenceThumbnail :dataType="item.dataType" :avatar="item.avatar" />
          <span class="itemName">{{ item.label || item.name }}</span>
        </button>
      </section>
      <section v-if="!search.trim()" class="materialSection" aria-label="素材引用">
        <button v-for="group in groups" :key="group.type" type="button" class="menuItem categoryItem" :class="{ active: activeGroup === group.type || activeKey === `group:${group.type}` }" :data-key="`group:${group.type}`" :disabled="busy || !group.items.length" aria-haspopup="true" :aria-expanded="activeGroup === group.type" @mousedown.prevent @mouseenter="openGroup(group.type)" @focus="openGroup(group.type)" @click="openGroup(group.type)">
          <component :is="group.icon" class="itemIcon" :size="18" aria-hidden="true" />
          <span class="itemName">{{ group.label }}</span>
          <icon-chevron-right :size="14" aria-hidden="true" />
        </button>
      </section>
      <template v-else>
        <section v-for="group in matchingGroups" :key="group.type" class="materialSection" :aria-label="group.label">
          <h2 class="sectionTitle">{{ group.label }}</h2>
          <button v-for="item in group.items" :key="item.id" type="button" class="menuItem" :class="{ active: activeKey === `material:${item.id}` }" :data-key="`material:${item.id}`" :title="item.name" :disabled="busy || item.disabled" @mousedown.prevent @mouseenter="activeKey = `material:${item.id}`" @focus="activeKey = `material:${item.id}`" @click="emit('selectMaterial', item.id)">
            <promptReferenceThumbnail :dataType="item.dataType" :media="item.media" />
            <span class="itemName">{{ item.name }}</span>
          </button>
        </section>
      </template>
    </div>
    <button v-if="hasAssetLibrary" type="button" class="menuItem libraryItem" :class="{ active: activeKey === 'library' }" data-key="library" :disabled="busy" @mousedown.prevent @mouseenter="activeGroup = undefined; activeKey = 'library'" @focus="activeGroup = undefined; activeKey = 'library'" @click="emit('selectAsset')">
      <icon-folder class="itemIcon" :size="18" aria-hidden="true" />
      <span class="itemName">全局素材库</span>
    </button>
    <div v-if="activeGroup && !search.trim()" ref="submenu" class="materialPopup" :style="submenuStyle" :aria-label="activeCategory?.label">
      <button v-for="item in activeCategory?.items" :key="item.id" type="button" class="menuItem" :class="{ active: activeKey === `material:${item.id}` }" :data-key="`material:${item.id}`" :title="item.name" :disabled="busy || item.disabled" @mousedown.prevent @mouseenter="activeKey = `material:${item.id}`" @focus="activeKey = `material:${item.id}`" @click="emit('selectMaterial', item.id)">
        <promptReferenceThumbnail :dataType="item.dataType" :media="item.media" />
        <span class="itemName">{{ item.name }}</span>
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { IconChevronRight, IconFileText, IconFolder, IconMusic, IconPhoto, IconSearch, IconVideo } from "@tabler/icons-vue";
import type { MaterialMention, ReferenceMention } from "../useNodeReferences";
import promptReferenceThumbnail from "./promptReferenceThumbnail.vue";

const props = defineProps<{
  references: ReferenceMention[];
  materials: MaterialMention[];
  query: string;
  anchor: { left: number; top: number; bottom: number };
  zIndex: number;
  busy?: boolean;
  hasAssetLibrary: boolean;
}>();
const emit = defineEmits<{ select: [id: string]; selectMaterial: [id: string]; selectAsset: []; close: [] }>();
const menu = ref<HTMLElement>();
const submenu = ref<HTMLElement>();
const search = ref(props.query);
const activeGroup = ref<MaterialMention["dataType"]>();
const activeKey = ref("");
const menuPosition = ref({ left: "0px", top: "0px" });
const submenuStyle = ref({ left: "0px", top: "0px" });
const menuStyle = computed(() => ({ ...menuPosition.value, zIndex: props.zIndex }));
const categories = [
  { type: "IMAGE", label: "图片", icon: IconPhoto },
  { type: "VIDEO", label: "视频", icon: IconVideo },
  { type: "AUDIO", label: "音频", icon: IconMusic },
  { type: "STRING", label: "文本", icon: IconFileText },
] as const;
const groups = computed(() => categories.map(group => ({ ...group, items: props.materials.filter(item => item.dataType === group.type) })));
const matches = (name: string) => name.toLocaleLowerCase().includes(search.value.trim().toLocaleLowerCase());
const matchingReferences = computed(() => props.references.filter(item => matches(item.label || item.name)));
const matchingGroups = computed(() => groups.value.map(group => ({ ...group, items: group.items.filter(item => matches(item.name)) })).filter(group => group.items.length));
const activeCategory = computed(() => groups.value.find(group => group.type === activeGroup.value));

watch(() => props.query, value => { search.value = value; });
watch(search, () => { activeGroup.value = undefined; activeKey.value = ""; });
watch([() => props.anchor, activeGroup, matchingReferences, matchingGroups], () => { void nextTick(updatePosition); }, { deep: true });

function updatePosition() {
  const element = menu.value;
  if (!element) return;
  const width = window.innerWidth;
  const height = window.innerHeight;
  const left = Math.max(8, Math.min(props.anchor.left, width - element.offsetWidth - 8));
  const below = props.anchor.bottom + 6;
  const top = Math.max(8, Math.min(below + element.offsetHeight <= height - 8 ? below : props.anchor.top - element.offsetHeight - 6, height - element.offsetHeight - 8));
  menuPosition.value = { left: `${left}px`, top: `${top}px` };
  const panel = submenu.value;
  if (!panel) return;
  const button = Array.from(element.querySelectorAll<HTMLElement>(".categoryItem")).find(item => item.dataset.key === `group:${activeGroup.value}`);
  const panelLeft = left + element.offsetWidth + 6;
  submenuStyle.value = {
    left: `${Math.max(8, Math.min(panelLeft + panel.offsetWidth <= width - 8 ? panelLeft : left - panel.offsetWidth - 6, width - panel.offsetWidth - 8))}px`,
    top: `${Math.max(8, Math.min(button?.getBoundingClientRect().top ?? top, height - panel.offsetHeight - 8))}px`,
  };
}

function openGroup(type: MaterialMention["dataType"]) {
  if (props.busy || !groups.value.find(group => group.type === type)?.items.length) return;
  activeGroup.value = type;
  activeKey.value = `group:${type}`;
}

function getButtons(inSubmenu = false) {
  return Array.from((inSubmenu ? submenu.value : menu.value)?.querySelectorAll<HTMLButtonElement>("button[data-key]:not(:disabled)") ?? [])
    .filter(button => inSubmenu || !submenu.value?.contains(button));
}

function handleKeydown(event: KeyboardEvent) {
  if (event.isComposing || !["ArrowDown", "ArrowUp", "ArrowRight", "ArrowLeft", "Enter", "Escape"].includes(event.key)) return false;
  const inSubmenu = !!activeGroup.value && activeKey.value.startsWith("material:");
  if (event.key === "ArrowLeft" && !inSubmenu || event.key === "ArrowRight" && !activeKey.value.startsWith("group:")) return false;
  event.preventDefault();
  event.stopPropagation();
  if (event.key === "Escape") { emit("close"); return true; }
  if (props.busy) return true;
  if (event.key === "ArrowLeft") {
    activeKey.value = `group:${activeGroup.value}`;
    activeGroup.value = undefined;
    return true;
  }
  const buttons = getButtons(inSubmenu);
  const index = buttons.findIndex(button => button.dataset.key === activeKey.value);
  if (event.key === "ArrowRight" || event.key === "Enter" && activeKey.value.startsWith("group:")) {
    const category = groups.value.find(group => `group:${group.type}` === activeKey.value);
    if (category) {
      openGroup(category.type);
      void nextTick(() => { activeKey.value = getButtons(true)[0]?.dataset.key || activeKey.value; });
    }
    return true;
  }
  if (event.key === "Enter") { buttons[Math.max(0, index)]?.click(); return true; }
  const next = index < 0 ? event.key === "ArrowDown" ? 0 : buttons.length - 1 : (index + (event.key === "ArrowDown" ? 1 : -1) + buttons.length) % buttons.length;
  const button = buttons[next];
  if (button) {
    activeKey.value = button.dataset.key || "";
    if (!inSubmenu) activeGroup.value = undefined;
    button.scrollIntoView({ block: "nearest" });
  }
  return true;
}

let resizeObserver: ResizeObserver | undefined;
onMounted(() => {
  updatePosition();
  resizeObserver = new ResizeObserver(updatePosition);
  if (menu.value) resizeObserver.observe(menu.value);
  window.addEventListener("resize", updatePosition);
});
onBeforeUnmount(() => {
  resizeObserver?.disconnect();
  window.removeEventListener("resize", updatePosition);
});
defineExpose({ handleKeydown, contains: (target: Node) => !!menu.value?.contains(target) });
</script>

<style scoped lang="scss">
.referenceMenu {
  position: fixed;
  display: flex;
  flex-direction: column;
  box-sizing: border-box;
  width: 220px;
  max-width: calc(100vw - 16px);
  max-height: min(440px, calc(100vh - 16px));
  padding: 4px;
  border: 1px solid var(--el-border-color-light);
  border-radius: var(--ui-radius-large, var(--el-border-radius-base));
  background: var(--el-bg-color-overlay);
  box-shadow: var(--el-box-shadow-light);
  color: var(--el-text-color-regular);
  font-size: var(--el-font-size-base);
  line-height: 22px;
  pointer-events: auto;

  .searchBox {
    display: flex;
    align-items: center;
    flex-shrink: 0;
    gap: 6px;
    margin-bottom: 4px;
    padding: 4px 8px;
    border: 1px solid var(--el-border-color);
    border-radius: var(--el-border-radius-base);
    color: var(--el-text-color-secondary);

    &:focus-within { border-color: var(--el-color-primary); }

    input {
      width: 100%;
      min-width: 0;
      padding: 0;
      border: 0;
      outline: none;
      background: transparent;
      color: var(--el-text-color-primary);
      font: inherit;

      &::placeholder { color: var(--el-text-color-placeholder); }
    }
  }

  .menuBody {
    min-height: 0;
    overflow-y: auto;
    overscroll-behavior: contain;

    .materialSection {
      .sectionTitle {
        margin: 6px 8px 2px;
        color: var(--el-text-color-secondary);
        font-size: 11px;
        font-weight: 400;
        line-height: 18px;
      }
    }
  }

  .menuItem {
    display: flex;
    align-items: center;
    gap: 6px;
    box-sizing: border-box;
    width: 100%;
    min-height: 32px;
    padding: 4px 8px;
    border: 0;
    border-radius: var(--el-border-radius-small);
    background: transparent;
    color: inherit;
    font: inherit;
    text-align: left;
    cursor: pointer;

    &:hover:not(:disabled),
    &.active:not(:disabled) {
      background: var(--el-color-primary-light-9);
      color: var(--el-color-primary);
    }
    &:focus-visible { outline: 1px solid var(--el-color-primary); outline-offset: -1px; }
    &:disabled { color: var(--el-text-color-disabled); cursor: not-allowed; }

    .itemIcon { flex-shrink: 0; width: 22px; }

    .itemName {
      flex: 1;
      min-width: 0;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
  }

  .libraryItem {
    flex-shrink: 0;
  }

  .materialPopup {
    position: fixed;
    box-sizing: border-box;
    width: 220px;
    max-width: calc(100vw - 16px);
    max-height: min(360px, calc(100vh - 16px));
    overflow-y: auto;
    overscroll-behavior: contain;
    padding: 4px;
    border: 1px solid var(--el-border-color-light);
    border-radius: var(--ui-radius-large, var(--el-border-radius-base));
    background: var(--el-bg-color-overlay);
    box-shadow: var(--el-box-shadow-light);
  }
}
</style>
