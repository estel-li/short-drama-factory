import { Router } from "express";
import { z } from "zod";
import u from "@/utils";
import { success } from "@/lib/responseFormat";
export default Router().post("/", (req, res) => {
  u.comfyEnvironment.authorize(req);
  const body = z.object({ id: z.uuid() }).strict().parse(req.body);
  res.json(success(u.modelSearch.stop(body.id)));
});
