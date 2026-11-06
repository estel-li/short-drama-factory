<template>
  <teleport to="body">
    <div v-if="visible" class="loadingPage" role="status" aria-label="正在加载项目">
      <img class="factoryLogo" :src="logoUrl" alt="" aria-hidden="true" />
    </div>
  </teleport>
</template>
<script setup lang="ts">
import { watch } from "vue";
import logoUrl from "@toonflow/assets/logo.svg";
const props = defineProps<{ active: boolean }>();
const visible = defineModel<boolean>("visible", { default: false });
const drawn = defineModel<boolean>("drawn", { default: false });
// 导航不依赖 SVG 路径数量或动画事件，后台标签页也能完成项目加载。
watch(() => props.active, active => {
  visible.value = active;
  drawn.value = active;
}, { immediate: true, flush: "post" });
</script>
<style lang="scss" scoped>
.loadingPage {
  position: fixed;
  inset: 0;
  z-index: 1100;
  display: grid;
  place-items: center;
  background: var(--el-bg-color);
  .factoryLogo { width: 96px; height: 96px; animation: factoryPulse 0.9s ease-in-out infinite; }
  @media (prefers-reduced-motion: reduce) { .factoryLogo { animation: none; } }
}
@keyframes factoryPulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }
</style>
