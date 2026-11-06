import { Router } from "express";
import u from "@/utils";
import { error, success } from "@/lib/responseFormat";
import { getRuntimePlatform } from "@/lib/platform";

const router = Router();

export default router.post("/", async (req, res) => {
  const native = getRuntimePlatform().nativeDevelopment && u.workspace.isLocalHostRequest(req);
  res.set("Cache-Control", "no-store");
  if (!native) return res.json(success({ native: false, directory: null }));

  if (!u.workspace.isLocalWorkspaceRequest(req)) {
    return res.status(403).json(error("仅允许本机开发页面选择目录", null, 403));
  }

  const directory = await u.directoryPicker.selectDirectory();
  res.json(success({ native: true, directory }));
});
