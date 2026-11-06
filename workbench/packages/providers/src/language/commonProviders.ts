const presets = [
  { id: "openDesign", label: "Open-Design", apiUrl: "https://amr-link.open-design.ai/v1", protocol: "openai-completions" },
  { id: "openai", label: "OpenAI", apiUrl: "https://api.openai.com/v1", protocol: "openai-responses" },
  { id: "anthropic", label: "Anthropic / Claude", apiUrl: "https://api.anthropic.com", protocol: "anthropic-messages" },
  { id: "qwen", label: "通义千问 / 阿里云百炼", apiUrl: "https://dashscope.aliyuncs.com/compatible-mode/v1", protocol: "openai-completions" },
  { id: "siliconFlow", label: "硅基流动", apiUrl: "https://api.siliconflow.cn/v1", protocol: "openai-completions" },
  { id: "openRouter", label: "OpenRouter", apiUrl: "https://openrouter.ai/api/v1", protocol: "openai-completions" },
] as const;

export default presets.map(preset => ({
  ...preset,
  icon: "",
  version: "1.0.0",
  readme: "填写此供应商的 API Key 后读取并选择文本模型，也可手动填写模型 ID。地址和协议可按账户实际配置修改。",
  rules: [{ type: "input", field: "apiKey", title: "API Key", value: "", props: { type: "password", showPassword: true, autocomplete: "off" } }],
  models: [],
} satisfies ProviderDefinition));
