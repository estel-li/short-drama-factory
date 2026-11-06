import { Router } from "express";
import u from "@/utils";
import { success } from "@/lib/responseFormat";

export default Router().post("/", async (req, res) => {
  u.comfyEnvironment.authorize(req);
  const result = await u.comfyEnvironment.request(req, "/api/environment/start", "POST");
  res.set("Cache-Control", "no-store").json(success(result));
});
