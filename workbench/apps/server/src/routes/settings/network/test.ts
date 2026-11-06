import u from "@/utils";
import { Router } from "express";
import { validateFields } from "@/lib/middleware";
import { success } from "@/lib/responseFormat";

const router = Router();

export default router.post("/", validateFields({ network: u.network.networkSchema }), async (req, res) => {
  u.mcpControl.assertAppRequest(req);
  const controller = new AbortController();
  const abort = () => controller.abort();
  res.once("close", abort);
  try { res.json(success(await u.network.testNetwork(req.body.network, controller.signal))); }
  finally { res.off("close", abort); }
});
