import { execFile } from "node:child_process";
import { isIP } from "node:net";
import { promisify } from "node:util";

const execFileAsync = promisify(execFile);

function proxyUrl(value: string) {
  try {
    const url = new URL(value.includes("://") ? value : `http://${value}`);
    if (!["http:", "https:"].includes(url.protocol) || !url.hostname || url.pathname !== "/" || url.search || url.hash) throw new Error();
    return url.href;
  } catch {
    throw new Error("系统代理地址无效，请改用自定义 HTTP/HTTPS 代理");
  }
}

export async function readSystemProxy(): Promise<{ httpProxy?: string; httpsProxy?: string; noProxy?: string }> {
  try { return await readProxy(); }
  catch (error) {
    if (error instanceof Error && !("cmd" in error)) throw error;
    throw new Error("无法读取系统代理设置，请改用自定义代理或不使用代理");
  }
}

async function readProxy(): Promise<{ httpProxy?: string; httpsProxy?: string; noProxy?: string }> {
  if (process.platform === "win32") {
    const key = "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Internet Settings";
    const { stdout } = await execFileAsync("reg.exe", ["query", key], { windowsHide: true, timeout: 5000 });
    const values = Object.fromEntries([...stdout.matchAll(/^\s+(\w+)\s+REG_\w+\s+(.+)$/gm)].map(match => [match[1]!, match[2]!.trim()]));
    if (Number(values.ProxyEnable) !== 1) {
      const { stdout: connections } = await execFileAsync("reg.exe", ["query", `${key}\\Connections`, "/v", "DefaultConnectionSettings"], { windowsHide: true, timeout: 5000 }).catch((error: { code?: number }) => {
        if (error.code === 1) return { stdout: "" };
        throw error;
      });
      const flags = Number.parseInt(connections.match(/REG_BINARY\s+[\da-f]{16}([\da-f]{2})/i)?.[1] ?? "0", 16);
      if (values.AutoConfigURL || Number(values.AutoDetect) === 1 || (flags & 12) !== 0) {
        throw new Error("系统使用 PAC 或自动发现代理，暂不支持，请改用自定义 HTTP/HTTPS 代理");
      }
      return {};
    }
    const server = values.ProxyServer?.trim();
    if (!server) throw new Error("系统代理已启用但未设置服务器，请检查系统代理设置");
    const mapped = server.includes("=") ? Object.fromEntries(server.split(";").map(item => item.trim().split(/=(.*)/s).slice(0, 2))) : { http: server, https: server };
    if (!mapped.http && !mapped.https) throw new Error("系统代理仅支持 HTTP/HTTPS，请改用自定义代理");
    return {
      httpProxy: mapped.http ? proxyUrl(mapped.http) : undefined,
      httpsProxy: mapped.https ? proxyUrl(mapped.https) : undefined,
      noProxy: values.ProxyOverride?.split(";").map(value => value.trim()).filter(Boolean).join(","),
    };
  }
  if (process.platform === "darwin") {
    const { stdout } = await execFileAsync("/usr/sbin/scutil", ["--proxy"], { timeout: 5000 });
    const values = Object.fromEntries([...stdout.matchAll(/^\s+(\w+)\s*:\s*([^\r\n<{]+)$/gm)].map(match => [match[1]!, match[2]!.trim()]));
    const getProxy = (protocol: string) => {
      if (values[`${protocol}Enable`] !== "1") return undefined;
      const host = values[`${protocol}Proxy`] ?? "";
      return proxyUrl(`${isIP(host) === 6 ? `[${host}]` : host}:${values[`${protocol}Port`]}`);
    };
    const httpProxy = getProxy("HTTP");
    const httpsProxy = getProxy("HTTPS");
    if (!httpProxy && !httpsProxy && (values.ProxyAutoConfigEnable === "1" || values.ProxyAutoDiscoveryEnable === "1")) {
      throw new Error("系统使用 PAC 或自动发现代理，暂不支持，请改用自定义 HTTP/HTTPS 代理");
    }
    if (!httpProxy && !httpsProxy && values.SOCKSEnable === "1") throw new Error("系统代理仅支持 HTTP/HTTPS，请改用自定义代理");
    const exceptions = stdout.match(/ExceptionsList\s*:\s*<array>\s*\{([^}]+)\}/)?.[1] ?? "";
    return { httpProxy, httpsProxy, noProxy: [...exceptions.matchAll(/^\s*\d+\s*:\s*(.+)$/gm)].map(match => match[1]!.trim()).join(",") };
  }
  return {};
}
