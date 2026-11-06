export function installBrowserCompatibility() {
  if (typeof Map.groupBy !== "function") {
    Object.defineProperty(Map, "groupBy", {
      configurable: true,
      writable: true,
      enumerable: false,
      value: {
        groupBy(items: Iterable<unknown>, callback: (value: unknown, index: number) => unknown) {
          if (items == null || typeof callback !== "function") throw new TypeError("Map.groupBy requires an iterable and a callback");
          const groups = new Map<unknown, unknown[]>();
          let index = 0;
          for (const value of items) {
            if (index >= Number.MAX_SAFE_INTEGER) throw new TypeError("Map.groupBy input is too large");
            const key = callback(value, index++);
            const group = groups.get(key);
            if (group) group.push(value);
            else groups.set(key, [value]);
          }
          return groups;
        },
      }.groupBy,
    });
  }

  if (typeof URL.canParse !== "function") {
    Object.defineProperty(URL, "canParse", {
      configurable: true,
      writable: true,
      enumerable: true,
      value: {
        canParse(input: unknown, base: unknown = undefined) {
          if (!arguments.length) throw new TypeError("URL.canParse requires a URL");
          // Web IDL 的字符串转换错误必须抛出；只有 URL 解析失败返回 false。
          const url = `${input}`;
          const baseUrl = base === undefined ? undefined : `${base}`;
          try { new URL(url, baseUrl); return true; }
          catch { return false; }
        },
      }.canParse,
    });
  }

  if (typeof Promise.withResolvers !== "function") {
    Object.defineProperty(Promise, "withResolvers", {
      configurable: true,
      writable: true,
      enumerable: false,
      value: {
        withResolvers(this: new (executor: (resolve: unknown, reject: unknown) => void) => unknown) {
          let resolve: unknown, reject: unknown;
          const promise = new this((resolveValue, rejectValue) => {
            if (resolve !== undefined || reject !== undefined) throw new TypeError("Promise executor was called more than once");
            resolve = resolveValue;
            reject = rejectValue;
          });
          if (typeof resolve !== "function" || typeof reject !== "function") throw new TypeError("Promise constructor did not provide resolver functions");
          return { promise, resolve, reject };
        },
      }.withResolvers,
    });
  }

  if (typeof AbortSignal.any !== "function") {
    const aborted = Object.getOwnPropertyDescriptor(AbortSignal.prototype, "aborted")!.get!;
    const reason = Object.getOwnPropertyDescriptor(AbortSignal.prototype, "reason")!.get!;
    const addListener = EventTarget.prototype.addEventListener;
    const removeListener = EventTarget.prototype.removeEventListener;
    const followers = new WeakMap<AbortSignal, Request>();
    const states = new WeakMap<AbortSignal, { controller: AbortController; sources: AbortSignal[] }>();
    type Listener = { source: WeakRef<AbortSignal>; callback: () => void };
    function removeListeners(listeners: Listener[]) {
      for (const { source, callback } of listeners) {
        const signal = source.deref();
        if (signal) removeListener.call(signal, "abort", callback);
      }
      listeners.length = 0;
    }
    const finalizer = new FinalizationRegistry(removeListeners);
    function createListener(source: WeakRef<AbortSignal>, target: WeakRef<AbortSignal>, listeners: Listener[], token: object) {
      // 单独的闭包只保存弱引用，不能从长期存活的源信号反向保留结果控制器。
      return () => {
        const signal = source.deref();
        if (!signal || !aborted.call(signal)) return;
        const result = target.deref();
        const state = result && states.get(result);
        removeListeners(listeners);
        finalizer.unregister(token);
        if (state && result) {
          states.delete(result);
          state.controller.abort(reason.call(signal));
        }
      };
    }
    Object.defineProperty(AbortSignal, "any", {
      configurable: true,
      writable: true,
      enumerable: true,
      value: {
        any(input: Iterable<AbortSignal>) {
          if (input === null || (typeof input !== "object" && typeof input !== "function")) {
            throw new TypeError("AbortSignal.any requires a sequence of AbortSignal objects");
          }
          const sources: AbortSignal[] = [];
          for (const signal of input) {
            aborted.call(signal);
            sources.push(signal);
          }
          const controller = new AbortController();
          for (const signal of sources) {
            if (!aborted.call(signal)) continue;
            controller.abort(reason.call(signal));
            return controller.signal;
          }
          if (!sources.length) return controller.signal;
          const result = controller.signal;
          const target = new WeakRef(result);
          const listeners: Listener[] = [];
          const token = {};
          states.set(result, { controller, sources });
          try {
            for (const signal of new Set(sources)) {
              let request = followers.get(signal);
              if (!request) {
                // 仅创建 Request，不发请求；原生 Follow 不受伪造 abort 或源监听器阻止传播影响。
                // ACT: Chromium 112 的组合 abort 事件顺序与现代原生 any 不完全相同；升级内核后使用原生实现。
                request = new Request("http://127.0.0.1/", { signal });
                followers.set(signal, request);
              }
              const source = new WeakRef(request.signal);
              const callback = createListener(source, target, listeners, token);
              listeners.push({ source, callback });
              addListener.call(request.signal, "abort", callback);
            }
            finalizer.register(result, listeners, token);
          } catch (error) {
            removeListeners(listeners);
            states.delete(result);
            throw error;
          }
          return result;
        },
      }.any,
    });
  }
}
