<template>
  <el-dialog v-model="visible" class="homeAssetLibraryDialog" title="素材库" width="min(1440px, 88vw)" alignCenter appendToBody destroyOnClose>
    <assetLibrary v-model="visible" expanded />
  </el-dialog>
</template>

<script setup lang="ts">
import assetLibrary from "@/pages/workspace/panels/canvas/components/assetLibrary.vue";

const visible = defineModel<boolean>({ default: false });
</script>

<style lang="scss">
.homeAssetLibraryDialog.el-dialog {
  display: flex;
  flex-direction: column;
  height: 84dvh;
  max-height: calc(100dvh - 32px);
  overflow: hidden;
  .el-dialog__header { flex-shrink: 0; }

  .el-dialog__body { display: flex; flex: 1; min-width: 0; min-height: 0; padding: 0; overflow: hidden; }

  @media (max-width: 700px) {
    width: calc(100vw - 24px);
    height: calc(100dvh - 32px);
  }
}
</style>
