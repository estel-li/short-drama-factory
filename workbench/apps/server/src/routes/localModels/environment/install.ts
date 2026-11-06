import { Router } from "express";
import { z } from "zod";
import u from "@/utils";
import { success } from "@/lib/responseFormat";

const schema = u.comfyEnvironment.installSchema.extend({ download_confirmation: z.string().min(1).max(128) });
export default Router().post("/", async (req, res) => {
  u.comfyEnvironment.authorize(req);
  const body = schema.parse(req.body);
  const result = await u.comfyEnvironment.request(req, "/api/environment/install", "POST", body);
  res.set("Cache-Control", "no-store").json(success(result));
});
