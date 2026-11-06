import { computed, onScopeDispose, ref, watch } from "vue";
import { ElMessage } from "element-plus";
import { translate } from "@toonflow/i18n/vue";
import { createBrowserAsr, isBrowserAsrSupported, type BrowserAsrState } from "@toonflow/asr";
import type xSender from "x-sender";

export default function useVoiceInput(options: {
  getSender: () => xSender | undefined;
  active: () => boolean;
  disabled: () => boolean;
  locked: () => boolean;
  onStart: () => void;
}) {
  const voiceSupported = isBrowserAsrSupported();
  const voiceState = ref<BrowserAsrState>("idle");
  const voiceText = ref("");
  const voiceLevel = ref(0);
  const voiceActive = computed(() => voiceState.value !== "idle");
  const voiceButtonLabel = computed(() => !voiceSupported ? "当前浏览器不支持原生语音识别" : voiceActive.value ? "取消语音输入" : "长按输入框语音输入，也可点击开始");
  let voiceAsr: ReturnType<typeof createBrowserAsr> | undefined;
  let voicePress: { pointerId: number; x: number; y: number; timer: number } | undefined;
  let voiceFinalText = "";
  let meterRun = 0;
  let meterFrame = 0;
  let meterStream: MediaStream | undefined;
  let meterContext: AudioContext | undefined;

  function stopVoiceMeter() {
    meterRun++;
    cancelAnimationFrame(meterFrame);
    meterFrame = 0;
    voiceLevel.value = 0;
    meterStream?.getTracks().forEach(track => track.stop());
    meterStream = undefined;
    const context = meterContext;
    meterContext = undefined;
    if (context && context.state !== "closed") void context.close().catch(error => console.warn("关闭麦克风音量采集失败", error));
  }

  async function startVoiceMeter(asr: ReturnType<typeof createBrowserAsr>) {
    stopVoiceMeter();
    const run = meterRun;
    try {
      if (!navigator.mediaDevices?.getUserMedia || typeof AudioContext === "undefined") throw new Error("当前环境无法读取麦克风音量");
      const context = new AudioContext();
      meterContext = context;
      const media = await navigator.mediaDevices.getUserMedia({ audio: true });
      if (run !== meterRun || voiceAsr !== asr) {
        media.getTracks().forEach(track => track.stop());
        return;
      }
      meterStream = media;
      if (context.state === "suspended") await context.resume();
      if (run !== meterRun || voiceAsr !== asr) return;
      const analyser = context.createAnalyser();
      analyser.fftSize = 512;
      context.createMediaStreamSource(media).connect(analyser);
      const samples = new Uint8Array(analyser.fftSize);
      let lastUpdate = 0;
      function updateLevel(now: number) {
        if (run !== meterRun) return;
        try {
          if (now - lastUpdate >= 1000 / 30) {
            lastUpdate = now;
            analyser.getByteTimeDomainData(samples);
            let sum = 0;
            for (const sample of samples) sum += ((sample - 128) / 128) ** 2;
            const rms = Math.sqrt(sum / samples.length);
            const level = Math.max(0, Math.min(1, (20 * Math.log10(Math.max(rms, 0.0001)) + 60) / 48));
            voiceLevel.value = Math.max(level, voiceLevel.value * 0.75);
          }
          meterFrame = requestAnimationFrame(updateLevel);
        } catch (error) {
          stopVoiceMeter();
          console.warn("无法读取麦克风音量", error);
        }
      }
      meterFrame = requestAnimationFrame(updateLevel);
    } catch (error) {
      if (run !== meterRun) return;
      stopVoiceMeter();
      console.warn("无法读取麦克风音量", error);
    }
  }

  function clearVoicePress() {
    if (voicePress) window.clearTimeout(voicePress.timer);
    voicePress = undefined;
  }

  function armVoiceInput(event: PointerEvent) {
    if (event.button !== 0 || !event.isPrimary || options.locked() || !options.active() || options.getSender()?.chatEditor.isComposition ||
      (event.target instanceof Element && event.target.closest("[data-agent-mention]"))) return;
    clearVoicePress();
    voicePress = { pointerId: event.pointerId, x: event.clientX, y: event.clientY, timer: window.setTimeout(startVoiceInput, 450) };
  }

  function moveVoicePress(event: PointerEvent) {
    if (voicePress?.pointerId === event.pointerId && !voiceActive.value && Math.hypot(event.clientX - voicePress.x, event.clientY - voicePress.y) > 8) clearVoicePress();
  }

  function stopVoiceInput() {
    clearVoicePress();
    stopVoiceMeter();
    try {
      voiceAsr?.stop();
    } catch (error) {
      cancelVoiceInput();
      ElMessage.warning(error instanceof Error ? error.message : "无法结束语音识别");
    }
  }

  function releaseVoicePress(event: PointerEvent) {
    if (voicePress?.pointerId === event.pointerId) stopVoiceInput();
  }

  function cancelVoiceInput(event?: Event) {
    if (event instanceof KeyboardEvent && event.key !== "Escape") return;
    if (event?.type === "visibilitychange" && !document.hidden) return;
    if (event instanceof KeyboardEvent && voiceActive.value) event.preventDefault();
    clearVoicePress();
    stopVoiceMeter();
    const asr = voiceAsr;
    voiceAsr = undefined;
    voiceState.value = "idle";
    voiceText.value = "";
    voiceFinalText = "";
    try {
      asr?.destroy();
    } catch (error) {
      console.warn("关闭语音识别失败", error);
    }
  }

  function startVoiceInput() {
    const instance = options.getSender();
    if (!instance || options.locked() || !options.active() || instance.chatEditor.isComposition) return;
    if (!voiceSupported) {
      clearVoicePress();
      ElMessage.warning("当前浏览器或 WebView 不支持原生语音识别，无法使用语音输入，请改用文字输入。");
      return;
    }
    try {
      let position = { ...instance.getCurrentNode() };
      const selection = window.getSelection();
      if (selection?.focusNode && instance.chatElement.richText.contains(selection.focusNode)) {
        for (const line of instance.chatEditor.NODES) for (const tag of line.children) {
          if ((tag.type !== "Write" && tag.type !== "Input") || !tag.$el.contains(selection.focusNode)) continue;
          const range = document.createRange();
          range.selectNodeContents(tag.$el);
          range.setEnd(selection.focusNode, selection.focusOffset);
          position = { node: selection.focusNode, instance: tag, offset: range.toString().length };
        }
      }
      const asr = createBrowserAsr({
        lang: "zh-CN",
        continuous: true,
        onStateChange(state) {
          if (voiceAsr !== asr || state === "destroyed") return;
          if (state === "idle") void finishVoiceInput(asr, instance, position);
          else voiceState.value = state;
        },
        onResult({ text, finalText }) {
          if (voiceAsr !== asr) return;
          voiceText.value = text;
          voiceFinalText = finalText;
        },
        onError({ code, message }) {
          if (voiceAsr !== asr) return;
          console.warn("浏览器原生语音识别失败", { code, message, userAgent: navigator.userAgent });
          const errors: Record<string, string> = {
            "not-allowed": translate("麦克风权限未获允许，请在浏览器或系统设置中开启"),
            "service-not-allowed": translate("当前浏览器或 WebView 未允许使用语音识别服务，暂时无法进行语音输入。"),
            "audio-capture": translate("无法使用麦克风，请检查设备连接和占用情况"),
            "no-speech": translate("未检测到语音，请长按后说话"),
            "network": translate("浏览器内置语音服务连接失败（network），请检查网络是否能访问该服务。"),
            "language-not-supported": translate("当前语音识别服务不支持中文"),
          };
          cancelVoiceInput();
          ElMessage.warning(errors[code] ?? `语音识别失败：${message}`);
        },
      });
      voiceAsr = asr;
      voiceText.value = "";
      voiceFinalText = "";
      options.onStart();
      asr.start();
      void startVoiceMeter(asr);
    } catch (error) {
      cancelVoiceInput();
      ElMessage.warning(error instanceof Error ? error.message : "无法启动语音识别");
    }
  }

  async function finishVoiceInput(asr: ReturnType<typeof createBrowserAsr>, instance: xSender, position: ReturnType<xSender["getCurrentNode"]>) {
    const text = voiceFinalText;
    stopVoiceMeter();
    clearVoicePress();
    voiceState.value = "stopping";
    try {
      asr.destroy();
      if (!text || options.getSender() !== instance || !options.active() || options.disabled()) return;
      instance.enable();
      if (instance.chatElement.richText.contains(position.instance.$el)) position.instance.focus(Math.min(position.offset, position.instance.$el.textContent?.length ?? 0));
      else instance.focus("last");
      await instance.setText(text);
    } catch (error) {
      ElMessage.error(error instanceof Error ? error.message : "语音文字回填失败，未能将识别结果填入输入框。");
    } finally {
      if (voiceAsr === asr) {
        voiceAsr = undefined;
        voiceText.value = "";
        voiceFinalText = "";
        voiceState.value = "idle";
      }
    }
  }

  watch([options.active, options.disabled], ([active, disabled]) => {
    if (!active || disabled) cancelVoiceInput();
  }, { flush: "sync" });
  window.addEventListener("pointermove", moveVoicePress, true);
  window.addEventListener("pointerup", releaseVoicePress, true);
  window.addEventListener("pointercancel", cancelVoiceInput, true);
  window.addEventListener("blur", cancelVoiceInput);
  window.addEventListener("keydown", cancelVoiceInput);
  document.addEventListener("visibilitychange", cancelVoiceInput);
  onScopeDispose(() => {
    cancelVoiceInput();
    window.removeEventListener("pointermove", moveVoicePress, true);
    window.removeEventListener("pointerup", releaseVoicePress, true);
    window.removeEventListener("pointercancel", cancelVoiceInput, true);
    window.removeEventListener("blur", cancelVoiceInput);
    window.removeEventListener("keydown", cancelVoiceInput);
    document.removeEventListener("visibilitychange", cancelVoiceInput);
  });

  return { voiceSupported, voiceState, voiceText, voiceActive, voiceButtonLabel, voiceLevel, armVoiceInput, startVoiceInput, stopVoiceInput, clearVoicePress, cancelVoiceInput };
}
