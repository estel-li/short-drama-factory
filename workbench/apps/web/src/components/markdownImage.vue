<template>
  <span class="markdownImage" :class="{ imagePending: pendingSize }" @load.capture="handleLoad" @error.capture="handleError">
    <figure v-if="pendingSize" class="imagePlaceholder" aria-hidden="true">
      <span class="imageDimensions" :style="{ width: `${pendingSize.width}px`, aspectRatio: `${pendingSize.width} / ${pendingSize.height}` }" />
      <figcaption v-if="caption" class="imageCaption">{{ caption }}</figcaption>
    </figure>
    <component v-if="error" :is="UI.ErrorComponent" variant="image" :message="error" />
    <component v-else :is="COMPONENT_RENDERERS.image" :key="imageKey" class="imageRenderer" v-bind="image" :node="resolvedNode" />
  </span>
</template>

<script lang="ts">
type ImageSize = { width: number; height: number };
// ACT: 仅保留最近 512 张图片的自然尺寸；淘汰后首次显示仍由图片加载确定高度，不保留 Blob。
const imageSizes = new Map<string, ImageSize>();
</script>

<script setup lang="ts">
import { computed, ref, watch } from "vue";
import axios from "axios";
import { COMPONENT_RENDERERS, UI, useContext, type ImageNodeRendererProps } from "vue-stream-markdown";
import useWorkspaceFiles from "@/lib/workspaceFiles";

const props = defineProps<{ image: ImageNodeRendererProps; directory: string }>();
const imageUrl = ref("");
const loading = ref(false);
const error = ref("");
const imageLoaded = ref(false);
const imageSize = ref<ImageSize>();
const imageKey = computed(() => JSON.stringify([props.directory, props.image.node.url]));
const remoteImage = computed(() => /^(?:https?:)?\/\//i.test(props.image.node.url));
const workspaceImage = computed(() => remoteImage.value || (!!props.image.node.url && !/^(?:[a-z][a-z\d+.-]*:|[\\/]|#)/i.test(props.image.node.url)));
const resolvedNode = computed(() => workspaceImage.value
  ? { ...props.image.node, url: imageUrl.value, loading: !!props.image.node.loading || loading.value }
  : props.image.node);
const { parsedNodes, provideContext, imageOptions } = useContext();
const pendingSize = computed(() => !imageLoaded.value && !error.value && !props.image.node.loading ? imageSize.value : undefined);
const caption = computed(() => imageOptions.value?.caption === false ? "" : String(props.image.node.title ?? props.image.node.alt ?? ""));
// ACT: 落盘图片按单张预览；多图切换需集中维护解析后的地址，避免重新请求原网址或相对路径。
provideContext({ parsedNodes: computed(() => workspaceImage.value ? [resolvedNode.value] : parsedNodes.value) });

function handleLoad(event: Event) {
  const image = event.target;
  if (!(image instanceof HTMLImageElement) || image.dataset.streamMarkdown !== "image" || image.getAttribute("src") !== resolvedNode.value.url) return;
  imageLoaded.value = true;
  if (!workspaceImage.value || !image.naturalWidth || !image.naturalHeight) return;
  imageSizes.delete(imageKey.value);
  imageSizes.set(imageKey.value, { width: image.naturalWidth, height: image.naturalHeight });
  if (imageSizes.size > 512) imageSizes.delete(imageSizes.keys().next().value!);
}

function handleError(event: Event) {
  const image = event.target;
  if (!(image instanceof HTMLImageElement) || image.dataset.streamMarkdown !== "image" || image.getAttribute("src") !== resolvedNode.value.url) return;
  imageSize.value = undefined;
  imageSizes.delete(imageKey.value);
}

watch([() => props.directory, () => props.image.node.url, () => !!props.image.node.loading] as const, async ([directory, url, streaming], _previous, onCleanup) => {
  imageUrl.value = "";
  loading.value = false;
  error.value = "";
  imageLoaded.value = false;
  imageSize.value = imageSizes.get(imageKey.value);
  if (!workspaceImage.value || streaming) return;
  loading.value = true;
  let cancelled = false;
  let release = () => {};
  onCleanup(() => { cancelled = true; release(); });
  try {
    const files = useWorkspaceFiles(directory);
    const saved = remoteImage.value ? await files.importImage(url.startsWith("//") ? `https:${url}` : url) : undefined;
    if (cancelled) return;
    const path = saved?.path ?? decodeURIComponent(url.split(/[?#]/, 1)[0]!);
    const preview = files.acquireUrl(path, saved?.mimeType);
    release = preview.release;
    const resolvedUrl = await preview.url;
    if (!cancelled) imageUrl.value = resolvedUrl;
  } catch (cause) {
    if (!cancelled) {
      imageSize.value = undefined;
      imageSizes.delete(imageKey.value);
      error.value = axios.isAxiosError<{ message?: string }>(cause)
        ? cause.response?.data?.message || "图片保存或读取失败"
        : cause instanceof Error ? cause.message : "图片保存或读取失败";
    }
  } finally {
    if (!cancelled) loading.value = false;
  }
}, { immediate: true });
</script>

<style scoped lang="scss">
.markdownImage {
  display: contents;

  &.imagePending {
    position: relative;
    display: inline-block;
    max-width: 100%;

    :deep(> .imageRenderer) {
      position: absolute;
      inset: 0;
    }
  }

  .imagePlaceholder {
    display: block;
    max-width: 100%;
    visibility: hidden;

    .imageDimensions {
      display: block;
      max-width: 100%;
    }

    .imageCaption {
      font-size: 0.875rem;
      line-height: 1.25rem;
      font-style: italic;
      text-align: center;
    }
  }
}
</style>
