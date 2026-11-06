import { Router } from "express";
import u from "@/utils";
import { success } from "@/lib/responseFormat";
export default Router().post("/", async (req, res) => {
  u.comfyEnvironment.authorize(req);
  const body = u.modelSearch.startSchema.parse(req.body);
  res.json(success(await u.modelSearch.start(body.directories)));
});
