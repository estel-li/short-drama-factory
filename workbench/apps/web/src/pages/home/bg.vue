<template>
  <canvas ref="fogCanvas" class="pixelFog" aria-hidden="true" />
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from "vue";
import logoUrl from "@toonflow/assets/logo.svg";

type FogPoint = { x: number; y: number; nx: number; ny: number; ink: number; halo: number; variation: number; pixelIndex: number };
type LogoMask = { pixels: Uint8ClampedArray; halo: Uint8ClampedArray };

const props = defineProps<{ scrollTop: number }>();
const fogCanvas = ref<HTMLCanvasElement>();
const events = new AbortController();
const maskSize = 320;
const fogPixelSize = 2;
const step = 6;
const pointer = { x: -1000, y: -1000, targetX: -1000, targetY: -1000, strength: 0, targetStrength: 0 };
let context: CanvasRenderingContext2D | null = null;
let fogLayer: HTMLCanvasElement;
let fogContext: CanvasRenderingContext2D | null = null;
let fogPixels: ImageData;
let image: HTMLImageElement;
let logo: LogoMask | undefined;
let points: FogPoint[] = [];
let resizeObserver: ResizeObserver;
let themeObserver: MutationObserver;
let reducedMotion: MediaQueryList;
let animationFrame = 0;
let elapsed = 9;
let lastFrame = 0;
let width = 0;
let height = 0;
let pixelRatio = 1;
let inkColor = "";

function sampleLogo(): LogoMask | undefined {
  const mask = document.createElement("canvas");
  mask.width = mask.height = maskSize;
  const maskContext = mask.getContext("2d", { willReadFrequently: true });
  if (!maskContext) return;
  maskContext.drawImage(image, 0, 0, maskSize, maskSize);
  let pixels = maskContext.getImageData(0, 0, maskSize, maskSize).data;
  let left = maskSize;
  let top = maskSize;
  let right = 0;
  let bottom = 0;
  for (let y = 0; y < maskSize; y++) {
    for (let x = 0; x < maskSize; x++) {
      if (pixels[(y * maskSize + x) * 4 + 3]! < 96) continue;
      left = Math.min(left, x);
      top = Math.min(top, y);
      right = Math.max(right, x);
      bottom = Math.max(bottom, y);
    }
  }
  if (right < left || bottom < top) return;
  const scale = Math.min((maskSize - 44) / (right - left + 1), (maskSize - 44) / (bottom - top + 1));
  const logoWidth = (right - left + 1) * scale;
  const logoHeight = (bottom - top + 1) * scale;
  maskContext.clearRect(0, 0, maskSize, maskSize);
  maskContext.drawImage(image, left / maskSize * image.naturalWidth, top / maskSize * image.naturalHeight,
    (right - left + 1) / maskSize * image.naturalWidth, (bottom - top + 1) / maskSize * image.naturalHeight,
    (maskSize - logoWidth) / 2, (maskSize - logoHeight) / 2, logoWidth, logoHeight);
  pixels = maskContext.getImageData(0, 0, maskSize, maskSize).data;
  const blurred = document.createElement("canvas");
  blurred.width = blurred.height = maskSize;
  const blurredContext = blurred.getContext("2d");
  if (!blurredContext) return;
  blurredContext.filter = "blur(7px)";
  blurredContext.drawImage(mask, 0, 0);
  return { pixels, halo: blurredContext.getImageData(0, 0, maskSize, maskSize).data };
}

function resize() {
  const canvas = fogCanvas.value;
  if (!canvas || !context || !logo) return;
  width = canvas.clientWidth;
  height = canvas.clientHeight;
  if (!width || !height) return syncAnimation();
  pixelRatio = Math.min(window.devicePixelRatio || 1, 1.5);
  canvas.width = Math.round(width * pixelRatio);
  canvas.height = Math.round(height * pixelRatio);
  context.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0);
  context.imageSmoothingEnabled = false;
  fogLayer.width = Math.ceil(width / fogPixelSize);
  fogLayer.height = Math.ceil(height / fogPixelSize);
  fogPixels = fogContext!.createImageData(fogLayer.width, fogLayer.height);
  // ACT: 颗粒和点距都按 CSS 像素固定，点数随可视面积变化，避免窗口大小改变疏密。
  points = [];
  for (let x = step / 2; x < width; x += step) {
    for (let y = step / 2; y < height; y += step) {
      const seed = Math.sin(x * 18.23 + y * 73.17) * 43758.55;
      points.push({ x, y, nx: x / width, ny: y / height, ink: 0,
        halo: 0, variation: 0.82 + (seed - Math.floor(seed)) * 0.18,
        pixelIndex: (Math.floor(y / fogPixelSize) * fogLayer.width + Math.floor(x / fogPixelSize)) * 4 + 3 });
    }
  }
  updateScrollPoints();
  syncAnimation();
}

function updateScrollPoints() {
  if (!logo || !width || !height) return;
  const logoSize = Math.min(height * 0.86, width * 0.82, 560);
  const logoX = width * (width < 600 ? 0.53 : 0.76);
  const logoY = height * 0.45;
  for (const point of points) {
    const contentY = point.y + props.scrollTop;
    point.ny = contentY / height;
    const maskX = Math.floor((point.x - logoX) / logoSize * maskSize + maskSize / 2);
    const maskY = Math.floor((contentY - logoY) / logoSize * maskSize + maskSize / 2);
    const index = (maskY * maskSize + maskX) * 4 + 3;
    const inMask = maskX >= 0 && maskX < maskSize && maskY >= 0 && maskY < maskSize;
    point.ink = inMask ? logo.pixels[index]! / 255 : 0;
    point.halo = inMask ? logo.halo[index]! / 255 : 0;
  }
}

watch(() => props.scrollTop, () => {
  updateScrollPoints();
  draw();
});

function draw() {
  if (!context || !fogContext || !fogPixels || !width || !height) return;
  context.clearRect(0, 0, width, height);
  const time = elapsed * 0.7;
  const radius = width < 600 ? 78 : 112;
  let columnX = -1;
  let waveA = 0;
  let waveB = 0;
  let waveC = 0;
  let bandWidth = 0;
  let modulation = 0;
  for (const { x, y, nx, ny, ink, halo, variation, pixelIndex } of points) {
    if (ink > 0.65) {
      fogPixels.data[pixelIndex] = ink * 0.32 * 255;
      continue;
    }
    if (x !== columnX) {
      columnX = x;
      const flowX = 0.7 - nx;
      const amplitude = 0.08 + Math.abs(flowX) * 0.09;
      waveA = 0.46 + Math.sin(nx * 7.5 - time) * amplitude + Math.sin(nx * 15 + time * 0.7) * 0.018;
      waveB = 0.61 + Math.sin(nx * 6.3 - time * 0.79 + 1.7) * amplitude;
      waveC = 0.24 + Math.sin(nx * 8.1 + time * 0.63 + 3.1) * amplitude;
      bandWidth = 0.036 + Math.max(0, flowX) * 0.032;
      modulation = 0.65 + Math.sin(nx * 15 - time * 1.3) * 0.35;
    }
    const fog = ny < 1 ? Math.exp(-(((ny - waveA) / bandWidth) ** 2)) * 0.77
      + Math.exp(-(((ny - waveB) / bandWidth) ** 2)) * 0.53
      + Math.exp(-(((ny - waveC) / (bandWidth * 0.8)) ** 2)) * 0.42 : 0;
    const haloStrength = Math.min(1, halo * 2.4) * (0.77 + Math.sin(elapsed * 0.34 * 1.9 + nx * 10 - ny * 6) * 0.12);
    const hover = pointer.strength > 0.001 ? Math.max(0, 1 - Math.hypot(x - pointer.x, y - pointer.y) / radius) ** 2 * pointer.strength : 0;
    const mist = Math.min(1, fog * modulation);
    const size = Math.min(fogPixelSize, (0.55 + step * (mist * 0.49 + haloStrength * 0.75 + hover * 0.47)) * variation);
    fogPixels.data[pixelIndex] = Math.min(0.95, (ny < 1 ? 0.08 : 0) + mist * 0.3 + haloStrength * 1.1 + hover * 0.2)
      * (1 - ink) * Math.min(1, (size / fogPixelSize) ** 2) * 255;
  }
  // ACT: 点阵统一写入离屏掩膜后批量绘制，避免逐点调用 Canvas fillRect。
  fogContext.putImageData(fogPixels, 0, 0);
  context.drawImage(fogLayer, 0, 0, fogLayer.width * fogPixelSize, fogLayer.height * fogPixelSize);
  context.globalCompositeOperation = "source-in";
  context.fillStyle = inkColor;
  context.fillRect(0, 0, width, height);
  context.globalCompositeOperation = "source-over";
}

function tick(timestamp: number) {
  animationFrame = 0;
  if (events.signal.aborted || document.hidden || reducedMotion.matches || !width || !height) return;
  if (!lastFrame || timestamp - lastFrame >= 1000 / 30) {
    elapsed += lastFrame ? Math.min((timestamp - lastFrame) / 1000, 0.07) : 0;
    lastFrame = timestamp;
    pointer.x += (pointer.targetX - pointer.x) * 0.22;
    pointer.y += (pointer.targetY - pointer.y) * 0.22;
    pointer.strength += (pointer.targetStrength - pointer.strength) * 0.18;
    draw();
  }
  animationFrame = requestAnimationFrame(tick);
}

function syncAnimation() {
  cancelAnimationFrame(animationFrame);
  animationFrame = 0;
  lastFrame = 0;
  draw();
  if (logo && width && height && !document.hidden && !reducedMotion.matches && !events.signal.aborted) {
    animationFrame = requestAnimationFrame(tick);
  }
}

function updateColor() {
  const color = getComputedStyle(fogCanvas.value!).color;
  if (color === inkColor) return;
  inkColor = color;
  draw();
}

onMounted(() => {
  const canvas = fogCanvas.value!;
  context = canvas.getContext("2d");
  if (!context) return;
  fogLayer = document.createElement("canvas");
  fogContext = fogLayer.getContext("2d");
  if (!fogContext) return;
  reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
  const options = { passive: true, signal: events.signal };
  updateColor();
  image = new Image();
  image.onload = () => {
    if (events.signal.aborted) return;
    logo = sampleLogo();
    resize();
  };
  image.src = logoUrl;
  resizeObserver = new ResizeObserver(resize);
  resizeObserver.observe(canvas);
  themeObserver = new MutationObserver(updateColor);
  themeObserver.observe(document.documentElement, { attributes: true, attributeFilter: ["class", "style"] });
  canvas.parentElement!.addEventListener("pointermove", (event) => {
    if (event.pointerType === "touch" || reducedMotion.matches) return;
    const bounds = canvas.getBoundingClientRect();
    pointer.targetX = event.clientX - bounds.left;
    pointer.targetY = event.clientY - bounds.top;
    pointer.targetStrength = +(pointer.targetX >= 0 && pointer.targetX <= bounds.width && pointer.targetY >= 0 && pointer.targetY <= bounds.height);
    if (pointer.strength < 0.01) { pointer.x = pointer.targetX; pointer.y = pointer.targetY; }
  }, options);
  canvas.parentElement!.addEventListener("pointerleave", () => { pointer.targetStrength = 0; }, options);
  window.addEventListener("blur", () => { pointer.targetStrength = 0; }, options);
  document.addEventListener("visibilitychange", syncAnimation, options);
  reducedMotion.addEventListener("change", () => {
    pointer.strength = pointer.targetStrength = 0;
    syncAnimation();
  }, options);
});

onBeforeUnmount(() => {
  events.abort();
  cancelAnimationFrame(animationFrame);
  resizeObserver?.disconnect();
  themeObserver?.disconnect();
  if (image) image.onload = null;
});
</script>

<style lang="scss" scoped>
.pixelFog {
  display: block;
  width: 100%;
  height: 100%;
  pointer-events: none;
  color: var(--el-text-color-primary);
  opacity: 0.6;
}
</style>
