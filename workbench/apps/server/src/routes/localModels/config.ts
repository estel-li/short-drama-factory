import { Router } from "express";
import u from "@/utils";
import { success } from "@/lib/responseFormat";
import { localModelsConfig } from "@/utils/localModels";
const router = Router();
export default router.get("/", (req, res) => {
  u.mcpControl.assertAppRequest(req);
  res.set("Cache-Control", "no-store").json(success(localModelsConfig()));
});
