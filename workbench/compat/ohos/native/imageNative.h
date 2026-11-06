#pragma once

#include <cstddef>
#include <cstdint>
#include <string>
#include <vector>

struct ImageNativeOptions {
  uint32_t width = 0;
  uint32_t height = 0;
  std::string format;
  uint32_t quality = 92;
};

struct ImageNativeResult {
  uint32_t width = 0;
  uint32_t height = 0;
  std::string format;
  std::vector<uint8_t> bytes;
};

// 空 format 只读取原图元数据；编码时 width/height 同为 0 表示保留原尺寸。
bool processNativeImage(const uint8_t* bytes, size_t size, const ImageNativeOptions& options,
  ImageNativeResult& result, std::string& error) noexcept;
