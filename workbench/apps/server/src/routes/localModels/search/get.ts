import { Router } from "express";
import u from "@/utils";
import { success } from "@/lib/responseFormat";
export default Router().get("/", (req, res) => {
  u.comfyEnvironment.authorize(req);
  res.set("Cache-Control", "no-store").json(success(u.modelSearch.get()));
});
