import { Router } from "express";
import { z } from "zod";
import u from "@/utils";
import { validateFields } from "@/lib/middleware";
import { error, success } from "@/lib/responseFormat";

const router = Router();

export default router.post("/", validateFields({ id: z.uuid(), enabled: z.boolean() }), async (req, res) => {
  if (!u.workspace.isLocalWorkspaceRequest(req)) return res.status(403).json(error("请在桌面端或服务器本机管理 MCP", null, 403));
  res.json(success(await u.mcpServers.setMcpServerEnabled(req.body.id, req.body.enabled)));
});
