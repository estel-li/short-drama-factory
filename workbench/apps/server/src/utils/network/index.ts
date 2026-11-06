import { isIP } from "node:net";
import { z } from "zod";
import conf from "@/utils/conf";
import { t } from "@/lib/i18n";
import { readSystemProxy } from "./system";
import { configureNetwork, requestNetwork } from "./transport";

const initialEnvironment = {
  httpProxy: process.env.http_proxy || process.env.HTTP_PROXY || process.env.all_proxy || process.env.ALL_PROXY || "",
  httpsProxy: process.env.https_proxy || process.env.HTTPS_PROXY || process.env.all_proxy || process.env.ALL_PROXY || "",
  noProxy: process.env.no_proxy || process.env.NO_PROXY || "",
};

function validHost(value: string) {
  if (!value || value !== value.trim() || /[\s/@?#\\%]/.test(value)) return false;
  if (isIP(value.replace(/^\[|\]$/g, ""))) return true;
  if (/[:\[\]]/.test(value)) return false;
  try { return Boolean(new URL(`http://${value}`).hostname); }
  catch { return false; }
}

export const networkSchema = z.object({
  mode: z.enum(["none", "system", "custom"]),
  protocol: z.enum(["http", "https"]),
  host: z.string().max(253),
  port: z.number().int().min(1).max(65535),
  username: z.string().max(1024),
  password: z.string().max(1024),
}).refine(value => value.mode !== "custom" || validHost(value.host), {
  path: ["host"], message: "请输入有效的代理服务器 IP 或域名，不包含协议和路径",
});

export async function prepareNetwork(value: unknown) {
  if (value === undefined) return {};
  const network = networkSchema.parse(value);
  if (!process.versions.bun) throw Object.assign(new Error("当前运行环境暂不支持应用内代理设置"), { status: 400 });
  if (network.mode === "none") return {};
  if (network.mode === "system") {
    if (process.platform !== "win32" && process.platform !== "darwin") return initialEnvironment;
    return readSystemProxy();
  }
  const host = network.host.replace(/^\[|\]$/g, "");
  const url = new URL(`${network.protocol}://${isIP(host) === 6 ? `[${host}]` : host}:${network.port}`);
  url.username = network.username;
  url.password = network.password;
  return { httpProxy: url.href, httpsProxy: url.href };
}

export { configureNetwork };

export async function initializeNetwork() {
  if (!process.versions.bun) return;
  try { configureNetwork(await prepareNetwork(conf.get("settings", {}).network)); }
  catch {
    // 系统代理失效时仍允许打开本机设置修复；外网请求明确报错，不擅自直连。
    const failure = new Error("网络设置无法应用，请在网络设置中重新配置或选择不使用代理");
    configureNetwork({}, failure);
    console.warn(failure.message);
  }
}

export async function testNetwork(value: unknown, signal: AbortSignal) {
  const profile = await prepareNetwork(value);
  const startedAt = performance.now();
  let status: number;
  try {
    const response = await requestNetwork("https://www.baidu.com/robots.txt", {
      signal: AbortSignal.any([signal, AbortSignal.timeout(10000)]), redirect: "error",
    }, profile);
    status = response.status;
    await response.body?.cancel();
  } catch {
    if (signal.aborted) throw signal.reason;
    // 不返回底层代理 URL 或认证信息。
    throw Object.assign(new Error("连接测试失败，请检查代理地址、端口、认证信息及网络连接"), { status: 502 });
  }
  if (status !== 200) throw Object.assign(new Error(t`测试地址返回 HTTP ${status}`), { status: 502 });
  return { latency: Math.round(performance.now() - startedAt) };
}
