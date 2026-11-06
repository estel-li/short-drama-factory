import { Router } from "express";
import u from "@/utils";
import { success } from "@/lib/responseFormat";
export default Router().post("/", async (req, res) => {
  u.comfyEnvironment.authorize(req);
  const body = u.modelSearch.attachSchema.parse(req.body);
  const state = await u.comfyEnvironment.request(req, "/api/environment/local") as { environment: { comfy_dir: string } };
  res.json(success(await u.modelSearch.attach(body, state.environment.comfy_dir)));
});
