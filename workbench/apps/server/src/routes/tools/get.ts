import { Router } from "express";
import u from "@/utils";
import { success } from "@/lib/responseFormat";

const router = Router();

export default router.get("/", async (req, res) => {
  const canManage = u.workspace.isLocalWorkspaceRequest(req);
  const tools = (await u.plugins.listTools()).map(tool => ({ ...tool, builtin: req.app.locals.builtinPlugins.tool.has(tool.name) }));
  res.json(success({ tools: canManage ? tools : tools.map(tool => ({ ...tool, config: {} })), canManage }));
});
