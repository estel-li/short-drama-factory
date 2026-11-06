// 本地发行版保留调用兼容，不收集或上报使用数据。
export default {
  track(_event: string) {},
  startAgent() { return (_outcome: string) => {}; },
  observeCanvas(_read: () => unknown) { return () => {}; },
};
export function registerAnonymousData() { return () => {}; }
