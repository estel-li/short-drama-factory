import { Router } from "express";
import u from "@/utils";
import { success } from "@/lib/responseFormat";
import { getRuntimePlatform } from "@/lib/platform";

const router = Router();

export default router.get("/", (req, res) => {
  const canManage = u.workspace.isLocalWorkspaceRequest(req);
  const servers = u.mcpServers.listMcpServers();
  res.json(success({
    servers: canManage ? servers : servers.map(({ id, name, transport, enabled, status, toolCount }) => ({ id, name, transport, enabled, status, toolCount })),
    canManage,
    localSupported: !getRuntimePlatform().mobile,
  }));
});
