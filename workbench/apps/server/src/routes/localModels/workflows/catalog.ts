import { Router } from "express";
import u from "@/utils";
import { success } from "@/lib/responseFormat";
export default Router().post("/", async (req, res) => {
  u.mcpControl.assertAppRequest(req);
  u.multiTenant.requireDirectModelAccess();
  const body = u.comfyWorkflows.catalogSchema.parse(req.body);
  res.json(success(await u.comfyWorkflows.catalog(body.url, body.mediaType)));
});
