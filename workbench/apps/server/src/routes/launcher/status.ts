import { dirname } from "node:path";
import { Router } from "express";
import u from "@/utils";
import { success } from "@/lib/responseFormat";

const router = Router();
export default router.get("/", (req, res) => {
  u.comfyEnvironment.authorize(req);
  const connection = u.h3Factory.connection();
  res.set("Cache-Control", "no-store").json(success({
    application: "shortDramaFactoryWorkbench",
    workbenchRoot: req.app.locals.workbenchRoot ?? null,
    dataDirectory: dirname(u.conf.path),
    applicationRoot: connection.applicationRoot,
    factoryUrl: connection.baseUrl,
  }));
});
