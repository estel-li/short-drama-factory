import { Router } from "express";
import { z } from "zod";
import u from "@/utils";
import { validateFields } from "@/lib/middleware";
import { error, success } from "@/lib/responseFormat";

const router = Router();

export default router.delete("/", validateFields({ id: z.uuid() }), async (req, res) => {
  if (!u.workspace.isLocalWorkspaceRequest(req)) return res.status(403).json(error("请在桌面端或服务器本机管理 MCP", null, 403));
  await u.mcpServers.removeMcpServer(req.body.id);
  res.json(success(null, "MCP 已移除"));
});
