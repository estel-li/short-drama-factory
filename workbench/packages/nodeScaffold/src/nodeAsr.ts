import { onScopeDispose } from "vue";
import { isBrowserAudioAsrSupported, transcribeBrowserAudio, type BrowserAudioAsrOptions } from "@toonflow/asr";
import { useNodeFiles } from "./workspaceFiles";

export { createBrowserAsr, isBrowserAsrSupported, isBrowserAudioAsrSupported } from "@toonflow/asr";
export type { BrowserAsrState, BrowserAsrResult, BrowserAsrError, BrowserAsrOptions, BrowserAudioAsrOptions } from "@toonflow/asr";

export function useNodeAsr() {
  const files = useNodeFiles();
  const lifetime = new AbortController();
  onScopeDispose(() => lifetime.abort());

  return {
    async transcribe(path: string, options: BrowserAudioAsrOptions = {}) {
      const signal = options.signal ? AbortSignal.any([lifetime.signal, options.signal]) : lifetime.signal;
      signal.throwIfAborted();
      if (!isBrowserAudioAsrSupported()) throw new DOMException("当前浏览器暂不支持音频转文本，可以换个浏览器再试。", "NotSupportedError");
      const content = await files.getWorkspaceFiles().read(path);
      signal.throwIfAborted();
      if (!content.byteLength || content.byteLength > 100 * 1024 * 1024) throw new Error("音频不能为空且不能超过 100 MB");
      const url = URL.createObjectURL(new Blob([content]));
      try {
        return await transcribeBrowserAudio(url, { ...options, signal });
      } finally {
        URL.revokeObjectURL(url);
      }
    },
  };
}
