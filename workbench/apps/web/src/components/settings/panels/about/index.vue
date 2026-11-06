<template>
  <div class="about">
    <img :src="logoUrl" alt="短剧工厂" width="64" height="64" />
    <h3>短剧工厂</h3>
    <p>DeepSeek × MiniMax H3</p>
    <p>在画布上编写分镜、组织素材，通过在线 API 或 ComfyUI 生成图片与视频，续跑并交付成片。</p>
    <el-text type="info">本地创作工作台 · v{{ version }}</el-text>
  </div>
</template>
<script setup lang="ts">
import logoUrl from "@toonflow/assets/logo.svg";
const version = import.meta.env.appVersion;
</script>
<style scoped lang="scss">
.about { display: grid; gap: 16px; align-content: start; h3, p { margin: 0; } p { line-height: 1.7; } }
</style>
