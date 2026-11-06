import { Router } from "express";
import { z } from "zod";
import { factoryRequest } from "@toonflow/node-h3-factory/contracts";
import { validateFields } from "@/lib/middleware";
import { success, error } from "@/lib/responseFormat";
import { isLocalWorkspaceRequest, resolveWorkspace } from "@/utils/workspace";
import { executeFactory } from "@/utils/h3Factory";

export default Router().post("/", validateFields({
  directory: z.string().min(1).max(4096),
  nodeId: z.string().regex(/^[a-zA-Z0-9_-]{1,100}$/),
  request: factoryRequest,
}), async (req, res) => {
  if (!isLocalWorkspaceRequest(req)) throw Object.assign(new Error("本地 H3 接入仅允许本机工作区请求"), { status: 403 });
  const directory = await resolveWorkspace(req, req.body.directory);
  try {
    const value = await executeFactory(directory, req.body.nodeId, factoryRequest.parse(req.body.request));
    res.set("Cache-Control", "no-store").json(success(value));
  } catch (cause) {
    const problem = cause as Error & { status?: number; factoryError?: unknown };
    if (!problem.factoryError) throw cause;
    res.status(problem.status ?? 502).json(error(problem.message, problem.factoryError, problem.status ?? 502));
  }
});
