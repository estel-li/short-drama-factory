import { Router } from "express";
import { z } from "zod";
import u from "@/utils";
import { validateFields } from "@/lib/middleware";
import { error, success } from "@/lib/responseFormat";

const router = Router();

export default router.post("/", validateFields({ source: z.string().min(1).max(1024 * 1024) }), (req, res) => {
  if (!u.workspace.isLocalWorkspaceRequest(req)) return res.status(403).json(error("请在桌面端或服务器本机管理 MCP", null, 403));
  res.json(success({ servers: u.mcpServers.importMcpServers(req.body.source) }, "MCP 配置已导入"));
});
