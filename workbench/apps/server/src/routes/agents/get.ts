import { Router } from "express";
import u from "@/utils";
import { success } from "@/lib/responseFormat";

export default Router().get("/", async (req, res) => {
  const settings = u.a2aSettings.getA2aSettings();
  const base = u.a2aSettings.getA2aUrl(req);
  const agents = (await u.teams.listTeams()).map(team => ({
    ...team,
    builtin: team.kind === "local" && req.app.locals.builtinPlugins.agent.has(team.name),
    ...(team.kind === "local" && team.enabled && settings.enabled ? { cardUrl: `${base}/${team.name}/.well-known/agent-card.json` } : {}),
  }));
  res.json(success({ agents, canManage: u.workspace.isLocalWorkspaceRequest(req) }));
});
