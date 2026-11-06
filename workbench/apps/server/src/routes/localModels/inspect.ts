import { Router } from "express";
import u from "@/utils";
import { validateFields } from "@/lib/middleware";
import { success } from "@/lib/responseFormat";
import { comfyAddress } from "@/utils/localModels";

export default Router().post("/", validateFields({ url: comfyAddress }), async (req, res) => {
  u.mcpControl.assertAppRequest(req);
  const base = comfyAddress.parse(req.body.url);
  const read = async (path: string) => {
    const response = await fetch(new URL(path, base), { signal: AbortSignal.timeout(8000), redirect: "error" });
    if (!response.ok) throw Object.assign(new Error(`ComfyUI 连接失败（HTTP ${response.status}）`), { status: 502 });
    return response.json() as Promise<Record<string, any>>;
  };
  const state = await read("/system_stats");
  if (!state.system || !Array.isArray(state.devices)) throw Object.assign(new Error("不是有效的 ComfyUI 服务"), { status: 502 });
  const info = await read("/object_info/CheckpointLoaderSimple");
  const values = info.CheckpointLoaderSimple?.input?.required?.ckpt_name?.[0];
  const checkpoints = Array.isArray(values) ? values.filter((name: unknown) => typeof name === "string") : [];
  res.json(success({ connected: true, checkpoints }));
});
