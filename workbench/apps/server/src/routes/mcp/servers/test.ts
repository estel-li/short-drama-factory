import { Router } from "express";
import u from "@/utils";
import { validateFields } from "@/lib/middleware";
import { error, success } from "@/lib/responseFormat";

const router = Router();

export default router.post("/", validateFields({ server: u.mcpServers.mcpServerSchema }), async (req, res) => {
  if (!u.workspace.isLocalWorkspaceRequest(req)) return res.status(403).json(error("请在桌面端或服务器本机测试 MCP", null, 403));
  res.json(success(await u.mcpServers.testMcpServer(req.body.server), "MCP 连接成功"));
});
