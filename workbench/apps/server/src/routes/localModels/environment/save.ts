import { Router } from "express";
import u from "@/utils";
import { success } from "@/lib/responseFormat";

const schema = u.comfyEnvironment.configSchema;
export default Router().post("/", async (req, res) => {
  u.comfyEnvironment.authorize(req);
  const body = schema.parse(req.body);
  const result = await u.comfyEnvironment.request(req, "/api/environment/configure", "POST", body);
  res.set("Cache-Control", "no-store").json(success(result));
});
