// Bun 的同名内置兼容模块仍走原生 fetch，显式使用已安装包的入口。
import * as undici from "undici/index.js";
import { BlockList, isIP } from "node:net";

export type NetworkProfile = { httpProxy?: string; httpsProxy?: string; noProxy?: string };

const nativeFetch = globalThis.fetch;
const localAddresses = new BlockList();
localAddresses.addSubnet("127.0.0.0", 8, "ipv4");
localAddresses.addAddress("::1", "ipv6");

function localHost(hostname: string) {
  const host = hostname.replace(/^\[|\]$/g, "").toLowerCase();
  const family = isIP(host);
  return host === "localhost" || host.endsWith(".localhost") || (family !== 0 && localAddresses.check(host, family === 4 ? "ipv4" : "ipv6"));
}

function bypassProxy(url: URL, noProxy = "") {
  const host = url.hostname.replace(/^\[|\]$/g, "").toLowerCase();
  const port = url.port || (url.protocol === "https:" ? "443" : "80");
  // ACT: 逐项匹配系统和环境的绕过规则；超长列表时可改为预编译匹配器。
  return noProxy.split(/[,;\s]+/).some(value => {
    if (!value) return false;
    if (value === "*") return true;
    if (value.toLowerCase() === "<local>") return !host.includes(".") && !isIP(host);
    const subnet = value.match(/^(.+)\/(\d+)$/);
    if (subnet && isIP(subnet[1]!)) {
      if (!isIP(host)) return false;
      const addresses = new BlockList();
      const family = isIP(subnet[1]!) === 4 ? "ipv4" : "ipv6";
      try { addresses.addSubnet(subnet[1]!, Number(subnet[2]), family); } catch { return false; }
      return addresses.check(host, isIP(host) === 6 ? "ipv6" : "ipv4");
    }
    const withPort = value.match(/^(\[[^\]]+\]|[^:]+):(\d+)$/);
    if (withPort && withPort[2] !== port) return false;
    const name = (withPort?.[1] ?? value).replace(/^\[|\]$/g, "").replace(/^\*?\./, "").toLowerCase();
    if (name.includes("*")) return new RegExp(`^${name.split("*").map(part => part.replace(/[.+?^${}()|[\]\\]/g, "\\$&")).join(".*")}$`).test(host);
    return host === name || host.endsWith(`.${name}`);
  });
}

function proxyPool(origin: string | URL, options: undici.Pool.Options) {
  const connect = options.connect;
  if (typeof connect !== "function") return new undici.Pool(origin, options);
  return new undici.Pool(origin, {
    ...options,
    connect(options, callback) {
      // IP 不能作为 TLS SNI；仍由连接的 hostname 校验 IP 证书，兼容代理的 CONNECT 和 forward。
      const servername = isIP((options.servername ?? "").replace(/^\[|\]$/g, "")) ? undefined : options.servername;
      connect({ ...options, servername }, callback);
    },
  });
}

function createTransport(profile: NetworkProfile, failure?: Error) {
  // 与模型 SDK 的 dispatcher 保持一致；H2 会忽略单请求的 Connection: close，无法隔离失效连接。
  const options = { allowH2: false, headersTimeout: 0, bodyTimeout: 0 };
  const direct = new undici.Agent(options);
  const proxies = new Map<string, undici.ProxyAgent>();
  const close = () => Promise.all([direct.close(), ...[...proxies.values()].map(proxy => proxy.close())]);
  try {
    for (const address of [profile.httpProxy, profile.httpsProxy]) {
      if (address && !proxies.has(address)) proxies.set(address, new undici.ProxyAgent({ ...options, uri: address, clientFactory: proxyPool, factory: proxyPool }));
    }
  } catch {
    void close().catch(() => {});
    throw new Error("代理配置无效，请检查代理地址、端口和认证信息");
  }
  const dispatcher = direct.compose(dispatch => (options, handler) => {
    const url = new URL(options.origin!);
    if (localHost(url.hostname)) return dispatch(options, handler);
    if (failure) throw failure;
    const address = url.protocol === "https:" ? profile.httpsProxy : profile.httpProxy;
    const proxy = address && !bypassProxy(url, profile.noProxy) ? proxies.get(address) : undefined;
    return proxy ? proxy.dispatch(options, handler) : dispatch(options, handler);
  });
  return { dispatcher, failure, close };
}

let activeTransport: ReturnType<typeof createTransport> | undefined;

function responseMetadata(response: Response, source: { url: string; redirected: boolean; type: string }): Response {
  const clone = response.clone.bind(response);
  Object.defineProperties(response, {
    url: { value: source.url },
    redirected: { value: source.redirected },
    type: { value: source.type },
    clone: { value: () => responseMetadata(clone() as Response, source) },
  });
  return response;
}

export async function requestNetwork(input: Parameters<typeof fetch>[0], init?: Parameters<typeof fetch>[1], profile?: NetworkProfile): Promise<Response> {
  const request = input instanceof Request || input instanceof undici.Request ? input : undefined;
  const url = request?.url ?? String(input);
  if (!/^https?:/.test(url)) return nativeFetch(input, init);
  const transport = profile ? createTransport(profile) : activeTransport;
  if (!transport) return nativeFetch(input, init);
  try {
    // ACT: Bun Request 只能通过公开 body 流转换；不全量缓冲上传。需重放正文的调用方使用 URL + body 或 Undici Request。
    const nativeRequest = input instanceof Request ? input : undefined;
    if (nativeRequest && init?.body == null && (nativeRequest.bodyUsed || nativeRequest.body?.locked)) {
      throw new TypeError("Request body has already been used");
    }
    const requestOptions = {
      ...(nativeRequest ? {
        method: nativeRequest.method,
        body: nativeRequest.body,
        headers: nativeRequest.headers,
        signal: nativeRequest.signal,
        redirect: nativeRequest.redirect,
        credentials: nativeRequest.credentials,
        cache: nativeRequest.cache,
        integrity: nativeRequest.integrity,
        referrer: nativeRequest.referrer,
        referrerPolicy: nativeRequest.referrerPolicy,
      } : {}),
      ...Object.fromEntries(Object.entries(init ?? {}).filter(([, value]) => value !== undefined)),
    };
    if (nativeRequest && init?.body == null) requestOptions.body = nativeRequest.body;
    let body = requestOptions.body as undici.RequestInit["body"];
    if (body instanceof FormData) {
      const data = new undici.FormData();
      for (const [name, value] of body.entries()) data.append(String(name), value);
      body = data;
    }
    const response = await undici.fetch(input instanceof undici.Request ? input : url, {
      ...requestOptions,
      headers: requestOptions.headers ? [...new Headers(requestOptions.headers as ConstructorParameters<typeof Headers>[0])] : undefined,
      body,
      duplex: "half",
      dispatcher: transport.dispatcher,
    } as undici.RequestInit);
    return responseMetadata(new Response(response.body as ReadableStream<Uint8Array> | null, {
      status: response.status,
      statusText: response.statusText,
      headers: [...response.headers],
    }), response);
  } catch (error) {
    if (transport.failure && error instanceof Error && error.cause === transport.failure) throw transport.failure;
    throw error;
  } finally {
    // close 等待在途响应读完；检测请求不占用当前设置的连接池。
    if (profile) void transport.close().catch(() => {});
  }
}

export function configureNetwork(profile: NetworkProfile, failure?: Error, commit?: () => void) {
  const next = createTransport(profile, failure);
  try { commit?.(); }
  catch (error) { void next.close().catch(() => {}); throw error; }
  const previous = activeTransport;
  activeTransport = next;
  // ACT: 旧 Bun 缓存启动代理，预连接不能调用原生 fetch.preconnect 绕过当前设置。
  globalThis.fetch = Object.assign(requestNetwork, { preconnect() {} }) as typeof fetch;
  if (previous) void previous.close().catch(() => {});
}
