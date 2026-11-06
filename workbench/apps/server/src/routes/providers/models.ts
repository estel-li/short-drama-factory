import { Router } from "express";
import { z } from "zod";
import { validateFields } from "@/lib/middleware";
import { success } from "@/lib/responseFormat";
import u from "@/utils";
import { providerHeadersSchema } from "@/utils/ai/provider";

const router = Router();

export default router.post("/", validateFields({
  apiUrl: z.literal("https://api.deepseek.com").refine(value => {
    const url = new URL(value);
    return ["http:", "https:"].includes(url.protocol) && !url.username && !url.password && !url.search && !url.hash;
  }, "请填写不含查询参数的 HTTP API 基础地址"),
  protocol: z.literal("openai-completions"),
  apiKey: z.string().max(8192),
  headers: providerHeadersSchema.optional(),
}), async (req, res) => {
  u.mcpControl.assertAppRequest(req);
  const { apiUrl, protocol, apiKey, headers } = req.body as { apiUrl: string; protocol: string; apiKey: string; headers?: Record<string, string> };
  res.json(success(await u.ai.fetchProviderModels({ apiUrl, protocol, apiKey, headers })));
});
