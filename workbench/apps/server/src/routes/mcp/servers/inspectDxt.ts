import { Router } from "express";
import { z } from "zod";
import u from "@/utils";
import { validateFields } from "@/lib/middleware";
import { error, success } from "@/lib/responseFormat";

const router = Router();

export default router.post("/", validateFields({
  fileName: z.string().min(1).max(128),
  content: z.string().min(1).max(Math.ceil(u.mcpDxt.maxDxtBytes / 3) * 4).base64(),
}), (req, res) => {
  if (!u.workspace.isLocalWorkspaceRequest(req)) return res.status(403).json(error("请在桌面端或服务器本机导入 MCP", null, 403));
  res.json(success(u.mcpDxt.inspectDxt(req.body.fileName, req.body.content)));
});
