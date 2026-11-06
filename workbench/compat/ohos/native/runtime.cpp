#include <napi/native_api.h>
#include <hilog/log.h>

#include <chrono>
#include <condition_variable>
#include <cstring>
#include <dlfcn.h>
#include <memory>
#include <mutex>
#include <pthread.h>
#include <regex>
#include <stdexcept>
#include <string>
#include <unistd.h>
#include <vector>

namespace {
using HostCallback = void (*)(void *, int, const char *);

struct NodeLibrary {
  void *handle = nullptr;
  std::string directory;
  void *(*create)(const char *, const char *, const char *, const char *, HostCallback, void *) = nullptr;
  void (*run)(void *) = nullptr;
  void (*stop)(void *) = nullptr;
  void (*destroy)(void *) = nullptr;
};

struct RuntimeState {
  napi_async_work work = nullptr;
  napi_deferred deferred = nullptr;
  std::string programDir, dataDir, cacheDir;
  std::string url, error, outputTail, exitCode;
  std::mutex mutex;
  std::condition_variable condition;
  NodeLibrary *library = nullptr;
  void *host = nullptr;
  bool stopRequested = false;
  bool exited = false;
};

// ACT: 一个应用只运行一个 Node 环境；重启等待旧环境彻底释放，多实例需改为独立宿主。
std::mutex runtimeMutex, nodeRunMutex;
std::shared_ptr<RuntimeState> activeRuntime;
std::string lastRuntimeError;

std::string redact(const std::string &message) {
  static const std::regex tokenPattern("token=[^\\s&]+");
  auto result = std::regex_replace(message, tokenPattern, "token=[redacted]");
  if (result.size() > 8192) result.erase(0, result.size() - 8192);
  return result;
}

void releaseRuntime(const std::shared_ptr<RuntimeState> &state) {
  std::lock_guard<std::mutex> runtimeLock(runtimeMutex);
  if (activeRuntime != state) return;
  std::lock_guard<std::mutex> stateLock(state->mutex);
  if (!state->stopRequested && !state->error.empty()) {
    lastRuntimeError = state->error.substr(0, 8192);
    if (!state->outputTail.empty() && lastRuntimeError.size() < 8190) {
      const auto limit = 8190 - lastRuntimeError.size();
      lastRuntimeError += "\n\n" + state->outputTail.substr(state->outputTail.size() > limit ? state->outputTail.size() - limit : 0);
    }
  }
  activeRuntime.reset();
}

void stopRuntime(void *) {
  std::lock_guard<std::mutex> runtimeLock(runtimeMutex);
  lastRuntimeError.clear();
  if (!activeRuntime) return;
  std::lock_guard<std::mutex> stateLock(activeRuntime->mutex);
  activeRuntime->stopRequested = true;
  if (activeRuntime->host) activeRuntime->library->stop(activeRuntime->host);
  activeRuntime->condition.notify_all();
}

NodeLibrary &loadNodeLibrary() {
  static std::mutex mutex;
  static NodeLibrary library;
  std::lock_guard<std::mutex> lock(mutex);
  if (library.handle) return library;
  Dl_info location{};
  if (!dladdr(reinterpret_cast<void *>(&loadNodeLibrary), &location) || !location.dli_fname) throw std::runtime_error("无法定位应用原生库目录");
  const std::string path = location.dli_fname;
  library.directory = path.substr(0, path.find_last_of('/'));
  library.handle = dlopen((library.directory + "/libtoonflowNodeHost.so").c_str(), RTLD_NOW | RTLD_LOCAL);
  if (!library.handle) {
    const auto error = dlerror();
    throw std::runtime_error("无法加载 Node 运行时：" + std::string(error ? error : "未知动态链接错误"));
  }
  library.create = reinterpret_cast<decltype(library.create)>(dlsym(library.handle, "createNodeHost"));
  library.run = reinterpret_cast<decltype(library.run)>(dlsym(library.handle, "runNodeHost"));
  library.stop = reinterpret_cast<decltype(library.stop)>(dlsym(library.handle, "stopNodeHost"));
  library.destroy = reinterpret_cast<decltype(library.destroy)>(dlsym(library.handle, "destroyNodeHost"));
  if (!library.create || !library.run || !library.stop || !library.destroy) {
    dlclose(library.handle);
    library.handle = nullptr;
    throw std::runtime_error("Node 运行时缺少嵌入接口");
  }
  // Node 进程平台的生命周期长于单个环境，重启时不能卸载共享库。
  return library;
}

void hostEvent(void *data, int event, const char *message) {
  auto &state = *static_cast<RuntimeState *>(data);
  std::lock_guard<std::mutex> lock(state.mutex);
  try {
    if (event == 0) {
      state.outputTail += redact(message) + "\n";
      if (state.outputTail.size() > 8192) state.outputTail.erase(0, state.outputTail.size() - 8192);
    } else if (event == 1 && !state.stopRequested && state.url.empty()) {
      std::smatch match;
      const std::string url = message;
      static const std::regex urlPattern("^http://127[.]0[.]0[.]1:([0-9]{1,5})/[?]token=[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$");
      if (!std::regex_match(url, match, urlPattern) || std::stoi(match[1].str()) < 1 || std::stoi(match[1].str()) > 65535) {
        state.error = "Node 返回了无效的本地服务地址";
        state.library->stop(state.host);
      } else {
        state.url = url;
      }
    } else if (event == 2 && state.error.empty()) {
      state.error = redact(message);
    } else if (event == 3) {
      state.exitCode = message;
    }
  } catch (...) {
    state.error = "读取 Node 运行时事件失败";
    if (state.host) state.library->stop(state.host);
  }
  state.condition.notify_all();
}

void *runHost(void *data) {
  std::unique_ptr<std::shared_ptr<RuntimeState>> reference(static_cast<std::shared_ptr<RuntimeState> *>(data));
  auto state = *reference;
  {
    std::lock_guard<std::mutex> runLock(nodeRunMutex);
    state->library->run(state->host);
    void *host;
    {
      std::lock_guard<std::mutex> lock(state->mutex);
      host = state->host;
      state->host = nullptr;
    }
    state->library->destroy(host);
  }
  {
    std::lock_guard<std::mutex> lock(state->mutex);
    state->exited = true;
    if (!state->stopRequested && state->error.empty()) state->error = "本地 Node 服务已退出（退出码 " + state->exitCode + "）";
    if (!state->stopRequested) OH_LOG_Print(LOG_APP, LOG_ERROR, 0, "ToonflowRuntime", "%{public}s\n%{public}s", state->error.c_str(), state->outputTail.c_str());
    state->condition.notify_all();
  }
  releaseRuntime(state);
  return nullptr;
}

void executeStart(napi_env, void *data) {
  auto state = *static_cast<std::shared_ptr<RuntimeState> *>(data);
  bool running = false;
  try {
    if (access((state->programDir + "/bootstrap.cjs").c_str(), R_OK) != 0 || access((state->programDir + "/server.js").c_str(), R_OK) != 0) {
      throw std::runtime_error("安装包中缺少 Node 启动脚本");
    }
    auto &library = loadNodeLibrary();
    {
      std::lock_guard<std::mutex> lock(state->mutex);
      if (state->stopRequested) throw std::runtime_error("本地 Node 服务已停止");
      state->library = &library;
      state->host = library.create(library.directory.c_str(), state->programDir.c_str(), state->dataDir.c_str(), state->cacheDir.c_str(), hostEvent, state.get());
      if (!state->host) throw std::runtime_error("无法分配 Node 运行环境");
    }
    auto reference = std::make_unique<std::shared_ptr<RuntimeState>>(state);
    pthread_attr_t attributes;
    auto result = pthread_attr_init(&attributes);
    if (result != 0) throw std::runtime_error(std::strerror(result));
    result = pthread_attr_setstacksize(&attributes, 32 * 1024 * 1024);
    if (result == 0) result = pthread_attr_setdetachstate(&attributes, PTHREAD_CREATE_DETACHED);
    pthread_t thread;
    if (result == 0) result = pthread_create(&thread, &attributes, runHost, reference.get());
    pthread_attr_destroy(&attributes);
    if (result != 0) throw std::runtime_error("无法创建 Node 线程：" + std::string(std::strerror(result)));
    reference.release();
    running = true;
    std::unique_lock<std::mutex> lock(state->mutex);
    if (!state->condition.wait_for(lock, std::chrono::seconds(60), [&] { return !state->url.empty() || !state->error.empty() || state->stopRequested || state->exited; })) {
      state->error = "本地 Node 服务启动超时（60 秒）";
      if (state->host) library.stop(state->host);
    }
    if (state->stopRequested && state->error.empty()) state->error = "本地 Node 服务已停止";
  } catch (const std::exception &error) {
    std::lock_guard<std::mutex> lock(state->mutex);
    state->error = redact(error.what());
    if (state->host) state->library->stop(state->host);
  }
  if (!running) {
    {
      std::lock_guard<std::mutex> lock(state->mutex);
      if (state->host) state->library->destroy(state->host);
      state->host = nullptr;
      state->exited = true;
      state->condition.notify_all();
    }
    releaseRuntime(state);
  }
}

void completeStart(napi_env env, napi_status status, void *data) {
  std::unique_ptr<std::shared_ptr<RuntimeState>> reference(static_cast<std::shared_ptr<RuntimeState> *>(data));
  auto state = *reference;
  std::lock_guard<std::mutex> lock(state->mutex);
  if (status != napi_ok && state->error.empty()) {
    state->error = "本地 Node 启动任务被取消";
    if (state->host) state->library->stop(state->host);
  }
  napi_value value;
  if (!state->error.empty() || state->url.empty() || state->stopRequested || state->exited) {
    const auto message = (state->error.empty() ? "本地 Node 服务未启动" : state->error) +
      (state->outputTail.empty() ? "" : "\n\n" + state->outputTail);
    napi_create_string_utf8(env, message.c_str(), message.size(), &value);
    napi_value error;
    napi_create_error(env, nullptr, value, &error);
    napi_reject_deferred(env, state->deferred, error);
  } else {
    napi_create_string_utf8(env, state->url.c_str(), state->url.size(), &value);
    napi_resolve_deferred(env, state->deferred, value);
  }
  if (state->work) napi_delete_async_work(env, state->work);
}

napi_value start(napi_env env, napi_callback_info info) {
  auto state = std::make_shared<RuntimeState>();
  napi_value promise;
  napi_create_promise(env, &state->deferred, &promise);
  size_t count = 4;
  napi_value arguments[4];
  napi_get_cb_info(env, info, &count, arguments, nullptr, nullptr);
  std::string *paths[] = {&state->programDir, &state->dataDir, &state->cacheDir};
  for (size_t index = 0; index < count && index < 3; index++) {
    size_t length = 0;
    if (napi_get_value_string_utf8(env, arguments[index], nullptr, 0, &length) != napi_ok || length == 0 || length > 4096) break;
    std::vector<char> buffer(length + 1);
    napi_get_value_string_utf8(env, arguments[index], buffer.data(), buffer.size(), &length);
    paths[index]->assign(buffer.data(), length);
  }
  for (auto path : paths) {
    if (path->empty() || path->front() != '/' || path->find('\0') != std::string::npos) state->error = "Node 启动参数必须是三个有效绝对路径";
  }
  if (count != 3) state->error = "Node 启动参数必须是三个有效绝对路径";
  {
    std::lock_guard<std::mutex> lock(runtimeMutex);
    if (activeRuntime) {
      std::lock_guard<std::mutex> stateLock(activeRuntime->mutex);
      if (!activeRuntime->stopRequested) state->error = "本地 Node 服务正在启动或运行，请先停止";
    }
    if (state->error.empty()) {
      lastRuntimeError.clear();
      activeRuntime = state;
    }
  }
  auto reference = new std::shared_ptr<RuntimeState>(state);
  napi_value name;
  napi_create_string_utf8(env, "startNode", NAPI_AUTO_LENGTH, &name);
  if (!state->error.empty()) {
    completeStart(env, napi_ok, reference);
    return promise;
  }
  if (napi_create_async_work(env, nullptr, name, executeStart, completeStart, reference, &state->work) != napi_ok || napi_queue_async_work(env, state->work) != napi_ok) {
    state->error = "无法创建本地 Node 启动任务";
    state->exited = true;
    releaseRuntime(state);
    completeStart(env, napi_generic_failure, reference);
  }
  return promise;
}

napi_value stop(napi_env env, napi_callback_info) {
  stopRuntime(nullptr);
  napi_value value;
  napi_get_undefined(env, &value);
  return value;
}

napi_value getError(napi_env env, napi_callback_info) {
  std::lock_guard<std::mutex> lock(runtimeMutex);
  napi_value value;
  napi_create_string_utf8(env, lastRuntimeError.c_str(), lastRuntimeError.size(), &value);
  return value;
}

napi_value initialize(napi_env env, napi_value exports) {
  napi_property_descriptor properties[] = {
    {"start", nullptr, start, nullptr, nullptr, nullptr, napi_default, nullptr},
    {"stop", nullptr, stop, nullptr, nullptr, nullptr, napi_default, nullptr},
    {"getError", nullptr, getError, nullptr, nullptr, nullptr, napi_default, nullptr},
  };
  napi_define_properties(env, exports, sizeof(properties) / sizeof(properties[0]), properties);
  napi_add_env_cleanup_hook(env, stopRuntime, nullptr);
  return exports;
}
}

static napi_module runtimeModule = {1, 0, nullptr, initialize, "toonflowRuntime", nullptr, {0}};

extern "C" __attribute__((constructor)) void registerRuntime() {
  napi_module_register(&runtimeModule);
}
