#include <node.h>
#include "imageNative.h"

#include <cerrno>
#include <cstdlib>
#include <cstring>
#include <fcntl.h>
#include <memory>
#include <mutex>
#include <stdexcept>
#include <string>
#include <sys/syscall.h>
#include <unistd.h>
#include <vector>

namespace {
using HostCallback = void (*)(void *, int, const char *);

struct HostState {
  std::string nativeDir, programDir, dataDir, cacheDir;
  HostCallback callback = nullptr;
  void *callbackData = nullptr;
  std::mutex mutex;
  node::Environment *environment = nullptr;
  bool stopRequested = false;
  bool exitRequested = false;
  int exitCode = 0;
};

std::mutex initializationMutex;
bool initializationAttempted = false;
std::shared_ptr<node::InitializationResult> initialization;
std::string initializationError;

void notify(HostState &state, int event, const std::string &message) {
  if (state.callback) state.callback(state.callbackData, event, message.c_str());
}

void setEnvironment(const char *name, const std::string &value) {
  if (setenv(name, value.c_str(), 1) != 0) throw std::runtime_error(std::string("无法设置 ") + name + "：" + std::strerror(errno));
}

node::MultiIsolatePlatform *initializeProcess(HostState &state) {
  std::lock_guard<std::mutex> lock(initializationMutex);
  if (!initializationAttempted) {
    initializationAttempted = true;
    try {
      setEnvironment("UV_USE_IO_URING", "0");
      initialization = node::InitializeOncePerProcess({"toonflow", "--jitless", "--experimental-vm-modules", "--stack-trace-limit=50"}, {
        node::ProcessInitializationFlags::kNoStdioInitialization,
        node::ProcessInitializationFlags::kNoDefaultSignalHandling,
        node::ProcessInitializationFlags::kNoAdjustResourceLimits,
        node::ProcessInitializationFlags::kNoUseLargePages,
        node::ProcessInitializationFlags::kNoParseGlobalDebugVariables,
        node::ProcessInitializationFlags::kDisableNodeOptionsEnv,
      });
      for (const auto &error : initialization->errors()) notify(state, 0, error);
      if (initialization->early_return() || !initialization->platform()) initializationError = "Node 运行时初始化失败";
    } catch (const std::exception &error) {
      initializationError = error.what();
    }
  }
  if (!initializationError.empty()) throw std::runtime_error(initializationError);
  return initialization->platform();
}

void ready(const v8::FunctionCallbackInfo<v8::Value> &info) {
  auto isolate = info.GetIsolate();
  if (info.Length() != 1 || !info[0]->IsString()) {
    isolate->ThrowException(v8::Exception::TypeError(v8::String::NewFromUtf8Literal(isolate, "ready requires a URL string")));
    return;
  }
  v8::String::Utf8Value value(isolate, info[0]);
  if (!*value) return;
  auto state = static_cast<HostState *>(info.Data().As<v8::External>()->Value());
  notify(*state, 1, std::string(*value, value.length()));
}

void log(const v8::FunctionCallbackInfo<v8::Value> &info) {
  auto isolate = info.GetIsolate();
  if (info.Length() != 1 || !info[0]->IsString()) {
    isolate->ThrowException(v8::Exception::TypeError(v8::String::NewFromUtf8Literal(isolate, "log requires a string")));
    return;
  }
  v8::String::Utf8Value value(isolate, info[0]);
  if (!*value) return;
  auto state = static_cast<HostState *>(info.Data().As<v8::External>()->Value());
  notify(*state, 0, std::string(*value, value.length()));
}

void renameExclusive(const v8::FunctionCallbackInfo<v8::Value> &info) {
  auto isolate = info.GetIsolate();
  if (info.Length() != 2 || !info[0]->IsString() || !info[1]->IsString()) {
    isolate->ThrowException(v8::Exception::TypeError(v8::String::NewFromUtf8Literal(isolate, "renameExclusive requires two paths")));
    return;
  }
  v8::String::Utf8Value source(isolate, info[0]), target(isolate, info[1]);
  if (!*source || !*target) return;
  if (std::memchr(*source, '\0', source.length()) || std::memchr(*target, '\0', target.length())) {
    auto error = v8::Exception::TypeError(v8::String::NewFromUtf8Literal(isolate, "Paths must not contain null bytes"));
    if (!error.As<v8::Object>()->Set(isolate->GetCurrentContext(), v8::String::NewFromUtf8Literal(isolate, "code"),
      v8::String::NewFromUtf8Literal(isolate, "ERR_INVALID_ARG_VALUE")).FromMaybe(false)) return;
    isolate->ThrowException(error);
    return;
  }
  // RENAME_NOREPLACE 保留 file 包的原子不覆盖约定。
  if (syscall(SYS_renameat2, AT_FDCWD, *source, AT_FDCWD, *target, 1) != 0) {
    const auto error = errno;
    isolate->ThrowException(node::UVException(isolate, -error, "renameat2", nullptr, *source, *target));
  }
}

void processImage(const v8::FunctionCallbackInfo<v8::Value> &info) {
  auto isolate = info.GetIsolate();
  auto context = isolate->GetCurrentContext();
  if (info.Length() != 5 || !info[0]->IsUint8Array() || !info[1]->IsUint32() || !info[2]->IsUint32() ||
    !info[3]->IsString() || !info[4]->IsUint32()) {
    isolate->ThrowException(v8::Exception::TypeError(v8::String::NewFromUtf8Literal(isolate, "processImage requires bytes, width, height, format and quality")));
    return;
  }
  auto bytes = info[0].As<v8::Uint8Array>();
  auto buffer = bytes->Buffer();
  auto backing = buffer->GetBackingStore();
  ImageNativeOptions options;
  options.width = info[1].As<v8::Uint32>()->Value();
  options.height = info[2].As<v8::Uint32>()->Value();
  options.quality = info[4].As<v8::Uint32>()->Value();
  if (backing->IsShared() || buffer->WasDetached() || !bytes->ByteLength() || options.width > INT32_MAX ||
    options.height > INT32_MAX || options.quality < 1 || options.quality > 100) {
    isolate->ThrowException(v8::Exception::RangeError(v8::String::NewFromUtf8Literal(isolate, "Invalid image bytes, dimensions or quality")));
    return;
  }
  v8::String::Utf8Value format(isolate, info[3]);
  if (!*format) return;
  options.format.assign(*format, format.length());
  ImageNativeResult result;
  std::string message;
  if (!processNativeImage(static_cast<const uint8_t *>(backing->Data()) + bytes->ByteOffset(), bytes->ByteLength(), options, result, message)) {
    v8::Local<v8::String> text;
    if (!v8::String::NewFromUtf8(isolate, message.c_str()).ToLocal(&text)) return;
    auto error = v8::Exception::Error(text);
    if (!error.As<v8::Object>()->Set(context, v8::String::NewFromUtf8Literal(isolate, "code"),
      v8::String::NewFromUtf8Literal(isolate, "ERR_IMAGE_PROCESSING")).FromMaybe(false)) return;
    isolate->ThrowException(error);
    return;
  }
  auto output = v8::ArrayBuffer::New(isolate, result.bytes.size());
  if (!result.bytes.empty()) std::memcpy(output->Data(), result.bytes.data(), result.bytes.size());
  auto value = v8::Object::New(isolate);
  v8::Local<v8::String> outputFormat;
  if (!v8::String::NewFromUtf8(isolate, result.format.c_str()).ToLocal(&outputFormat)) return;
  if (!value->Set(context, v8::String::NewFromUtf8Literal(isolate, "width"), v8::Integer::NewFromUnsigned(isolate, result.width)).FromMaybe(false) ||
    !value->Set(context, v8::String::NewFromUtf8Literal(isolate, "height"), v8::Integer::NewFromUnsigned(isolate, result.height)).FromMaybe(false) ||
    !value->Set(context, v8::String::NewFromUtf8Literal(isolate, "format"), outputFormat).FromMaybe(false) ||
    !value->Set(context, v8::String::NewFromUtf8Literal(isolate, "bytes"), v8::Uint8Array::New(output, 0, result.bytes.size())).FromMaybe(false)) return;
  info.GetReturnValue().Set(value);
}

void initializeBinding(v8::Local<v8::Object> exports, v8::Local<v8::Value>, v8::Local<v8::Context> context, void *data) {
  auto isolate = context->GetIsolate();
  auto state = v8::External::New(isolate, data);
  const std::pair<const char *, v8::FunctionCallback> functions[] = {{"ready", ready}, {"log", log}, {"renameExclusive", renameExclusive}, {"processImage", processImage}};
  for (const auto &[name, callback] : functions) {
    v8::Local<v8::Function> function;
    v8::Local<v8::String> key;
    if (!v8::Function::New(context, callback, state).ToLocal(&function) || !v8::String::NewFromUtf8(isolate, name).ToLocal(&key)) return;
    if (!exports->Set(context, key, function).FromMaybe(false)) return;
  }
}

bool isStopping(HostState &state) {
  std::lock_guard<std::mutex> lock(state.mutex);
  return state.stopRequested;
}

void clearEnvironment(HostState *state) {
  std::lock_guard<std::mutex> lock(state->mutex);
  state->environment = nullptr;
}

bool installLogging(node::Environment *environment, v8::Local<v8::Value> process, v8::Local<v8::Value> require, HostState &state) {
  auto context = node::GetMainContext(environment);
  auto isolate = context->GetIsolate();
  v8::TryCatch tryCatch(isolate);
  const auto source = v8::String::NewFromUtf8Literal(isolate, R"js((function(process, require, nativeLog) {
    Error.stackTraceLimit = 50;
    for (const name of ['fetch', 'Headers', 'Response', 'Request', 'FormData', 'WebSocket', 'CloseEvent', 'MessageEvent', 'EventSource', 'ErrorEvent']) {
      if (!Reflect.deleteProperty(globalThis, name)) throw new Error('Cannot replace Node web global: ' + name);
    }
    const format = require('util').format;
    const Buffer = require('buffer').Buffer;
    const emit = (...values) => nativeLog(format(...values));
    for (const name of ['log', 'info', 'warn', 'error', 'debug']) console[name] = emit;
    process.on('uncaughtExceptionMonitor', (error, origin) => emit(origin, error && error.stack || error));
    const write = (chunk, encoding, callback) => {
      if (typeof encoding === 'function') { callback = encoding; encoding = undefined; }
      if (typeof chunk !== 'string' && !ArrayBuffer.isView(chunk)) throw new TypeError('Output must be a string or byte array');
      const bytes = typeof chunk === 'string' ? Buffer.from(chunk, encoding || 'utf8')
        : Buffer.from(chunk.buffer, chunk.byteOffset, chunk.byteLength);
      nativeLog(bytes.toString('utf8'));
      if (typeof callback === 'function') process.nextTick(callback);
      return true;
    };
    process.stderr.write = write;
    process.stdout.write = write;
  }))js");
  v8::Local<v8::Script> script;
  v8::Local<v8::Value> installer, result;
  v8::Local<v8::Function> callback;
  if (v8::Script::Compile(context, source).ToLocal(&script) && script->Run(context).ToLocal(&installer) &&
    v8::Function::New(context, log, v8::External::New(isolate, &state)).ToLocal(&callback)) {
    v8::Local<v8::Value> arguments[] = {process, require, callback};
    if (installer.As<v8::Function>()->Call(context, v8::Undefined(isolate), 3, arguments).ToLocal(&result)) return true;
  }
  std::string message = "无法初始化 Node 启动日志";
  v8::Local<v8::Value> detail;
  if (tryCatch.StackTrace(context).ToLocal(&detail) || !(detail = tryCatch.Exception()).IsEmpty()) {
    v8::String::Utf8Value text(isolate, detail);
    if (*text) message += "\n" + std::string(*text, text.length());
  }
  notify(state, 2, message);
  return false;
}
}

extern "C" __attribute__((visibility("default"))) void *createNodeHost(const char *nativeDir, const char *programDir,
  const char *dataDir, const char *cacheDir, HostCallback callback, void *callbackData) {
  try {
    auto state = std::make_unique<HostState>();
    state->nativeDir = nativeDir;
    state->programDir = programDir;
    state->dataDir = dataDir;
    state->cacheDir = cacheDir;
    state->callback = callback;
    state->callbackData = callbackData;
    return state.release();
  } catch (...) {
    return nullptr;
  }
}

extern "C" __attribute__((visibility("default"))) void stopNodeHost(void *handle) {
  auto &state = *static_cast<HostState *>(handle);
  std::lock_guard<std::mutex> lock(state.mutex);
  state.stopRequested = true;
  if (state.environment) node::Stop(state.environment);
}

extern "C" __attribute__((visibility("default"))) void runNodeHost(void *handle) {
  auto &state = *static_cast<HostState *>(handle);
  try {
    if (!isStopping(state)) {
      setEnvironment("TOONFLOW_NATIVE_DIR", state.nativeDir);
      setEnvironment("TOONFLOW_PLATFORM", "ohos");
      setEnvironment("TOONFLOW_MOBILE_DATA_DIR", state.dataDir);
      setEnvironment("TOONFLOW_MOBILE_DEVICE_NAME", "Toonflow HarmonyOS");
      setEnvironment("TMPDIR", state.cacheDir);
      setEnvironment("HOME", state.dataDir.substr(0, state.dataDir.find_last_of('/')));
      notify(state, 0, "正在初始化 Node 进程平台");
      auto platform = initializeProcess(state);
      const std::vector<std::string> arguments = {"toonflow", state.programDir + "/bootstrap.cjs", state.programDir + "/server.js"};
      std::vector<std::string> errors;
      const auto flags = static_cast<node::EnvironmentFlags::Flags>(node::EnvironmentFlags::kTrackUnmanagedFds |
        node::EnvironmentFlags::kNoGlobalSearchPaths | node::EnvironmentFlags::kNoCreateInspector |
        node::EnvironmentFlags::kNoStartDebugSignalHandler | node::EnvironmentFlags::kNoWaitForInspectorFrontend);
      auto setup = node::CommonEnvironmentSetup::Create(platform, &errors, arguments, initialization->exec_args(), flags);
      if (!setup) {
        std::string message = "无法创建 Node 运行环境";
        for (const auto &error : errors) message += "\n" + error;
        throw std::runtime_error(message);
      }
      notify(state, 0, "Node 运行环境已创建");
      // 包括异常退出在内，必须在 setup 销毁环境前清除其他线程可见的指针。
      std::unique_ptr<HostState, decltype(&clearEnvironment)> environmentGuard(&state, clearEnvironment);
      auto isolate = setup->isolate();
      auto environment = setup->env();
      v8::Locker locker(isolate);
      v8::Isolate::Scope isolateScope(isolate);
      v8::HandleScope handleScope(isolate);
      v8::Context::Scope contextScope(setup->context());
      v8::TryCatch tryCatch(isolate);
      node::SetProcessExitHandler(environment, [&state](node::Environment *current, int exitCode) {
        state.exitRequested = true;
        state.exitCode = exitCode;
        notify(state, 0, "Node 请求退出，退出码 " + std::to_string(exitCode));
        node::Stop(current);
      });
      node::AddLinkedBinding(environment, "toonflowNative", initializeBinding, &state);
      if (!isStopping(state)) {
        auto loaded = node::LoadEnvironment(environment, node::StartExecutionCallback{}, [&state, environment](node::Environment *current,
          v8::Local<v8::Value> process, v8::Local<v8::Value> require) {
          if (current != environment) return;
          {
            std::lock_guard<std::mutex> lock(state.mutex);
            state.environment = current;
            if (state.stopRequested) node::Stop(current);
          }
          if (isStopping(state)) return;
          notify(state, 0, "Node 已进入启动预加载");
          if (!installLogging(current, process, require, state)) {
            state.exitCode = 1;
            node::Stop(current);
            return;
          }
          notify(state, 0, "Node 启动日志已连接，开始执行 bootstrap.cjs");
        });
        if (!loaded.IsEmpty()) {
          const auto exitCode = node::SpinEventLoop(environment);
          if (!exitCode.IsNothing()) state.exitCode = exitCode.FromJust();
        } else if (!isStopping(state) && !state.exitRequested) {
          std::string message = "Node 启动脚本执行失败";
          v8::Local<v8::Value> detail;
          if (tryCatch.StackTrace(setup->context()).ToLocal(&detail) || !(detail = tryCatch.Exception()).IsEmpty()) {
            v8::String::Utf8Value text(isolate, detail);
            if (*text) message += "\n" + std::string(*text, text.length());
          }
          notify(state, 2, message);
          state.exitCode = 1;
        }
      }
    }
  } catch (const std::exception &error) {
    state.exitCode = 1;
    notify(state, 2, error.what());
  } catch (...) {
    state.exitCode = 1;
    notify(state, 2, "Node 运行环境发生未知错误");
  }
  notify(state, 3, std::to_string(state.exitCode));
}

extern "C" __attribute__((visibility("default"))) void destroyNodeHost(void *handle) {
  delete static_cast<HostState *>(handle);
}
