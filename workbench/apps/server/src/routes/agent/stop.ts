import { Router } from "express";
import { z } from "zod";
import { validateFields } from "@/lib/middleware";
import { success } from "@/lib/responseFormat";
import u from "@/utils";

const inputSchema = z.object({
  directory: z.string().min(1).max(4096),
  runIds: z.array(z.uuid()).max(1000),
});

export default Router().post("/", validateFields(inputSchema.shape), async (req, res) => {
  const { directory, runIds } = req.body as z.infer<typeof inputSchema>;
  const cwd = await u.workspace.resolveWorkspace(req, directory);
  await u.agent.stopAgentRuns(cwd, runIds);
  res.json(success());
});
