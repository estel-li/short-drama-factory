import { Router } from "express";
import { z } from "zod";
import { validateFields } from "@/lib/middleware";
import { success } from "@/lib/responseFormat";
import u from "@/utils";

const inputSchema = z.object({
  directory: z.string().min(1).max(4096),
  sessionFile: z.string().regex(/^[\w-]+\.jsonl$/),
  runId: z.uuid(),
  messageId: z.uuid(),
});

export default Router().post("/", validateFields(inputSchema.shape), async (req, res) => {
  const { directory, sessionFile, runId, messageId } = req.body as z.infer<typeof inputSchema>;
  const { path } = await u.workspaceFile.resolveWorkspaceFile(req, directory, `.agent/sessions/${sessionFile}`);
  res.set("Cache-Control", "no-store").json(success(u.agent.steerAgentQueuedMessage(path, runId, messageId)));
});
