import { Router } from "express";
import u from "@/utils";
import { success } from "@/lib/responseFormat";

export default Router().get("/", async (req, res) => {
  u.comfyEnvironment.authorize(req);
  const result = await u.comfyEnvironment.request(req, "/api/environment/local", "GET");
  res.set("Cache-Control", "no-store").json(success(result));
});
