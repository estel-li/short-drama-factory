import { Router } from "express";
import { z } from "zod";
import { validateFields } from "@/lib/middleware";
import { success } from "@/lib/responseFormat";
import u from "@/utils";
import { providerHeadersSchema, providerUrlSchema, providerSchema } from "@/utils/ai/provider";

const router = Router();

export default router.post("/", validateFields({
  apiUrl: providerUrlSchema,
  protocol: providerSchema.shape.protocol,
  apiKey: z.string().max(8192),
  headers: providerHeadersSchema.optional(),
}), async (req, res) => {
  u.mcpControl.assertAppRequest(req);
  const { apiUrl, protocol, apiKey, headers } = req.body as { apiUrl: string; protocol: string; apiKey: string; headers?: Record<string, string> };
  res.json(success(await u.ai.fetchProviderModels({ apiUrl, protocol, apiKey, headers })));
});
