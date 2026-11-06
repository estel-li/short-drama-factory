import { Router } from "express";
import u from "@/utils";
import { success } from "@/lib/responseFormat";
import { localModelsConfig } from "@/utils/localModels";
const router = Router();
export default router.get("/", async (req, res) => {
  u.mcpControl.assertAppRequest(req);
  const config = localModelsConfig();
  async function inspect(base: string, path: string, factory = false) {
    try {
      const response = await fetch(new URL(path, base), { signal: AbortSignal.timeout(5000), redirect: "error" });
      if (!response.ok) return `HTTP ${response.status}`;
      const value = await response.json() as Record<string, unknown>;
      if (factory) {
        const normalize = (text: string) => text.replaceAll("\\", "/").replace(/\/$/, "");
        if (value.protocol_version !== 1 || typeof value.application_root !== "string"
          || normalize(value.application_root) !== normalize(config.applicationRoot)) return "实例目录或协议不匹配";
      } else if (!value.system || !Array.isArray(value.devices)) return "不是有效的 ComfyUI 响应";
      return "已连接";
    } catch { return "连接失败，请检查服务监听、网络或隧道"; }
  }
  const [comfy, factory] = await Promise.all([inspect(config.comfyUrl, "/system_stats"), inspect(config.factoryUrl, "/api/health", true)]);
  res.json(success({ comfy, factory }));
});
