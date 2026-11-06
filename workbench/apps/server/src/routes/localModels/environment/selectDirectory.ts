import { Router } from "express";
import u from "@/utils";
import { success } from "@/lib/responseFormat";

export default Router().post("/", async (req, res) => {
  u.comfyEnvironment.authorize(req);
  const directory = await u.directoryPicker.selectDirectory();
  res.json(success({ directory }));
});
