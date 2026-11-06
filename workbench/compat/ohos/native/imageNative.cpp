#include "imageNative.h"

#include <algorithm>
#include <cstring>
#include <limits>
#include <stdexcept>
#include <string_view>

#include <multimedia/image_framework/image/image_packer_native.h>
#include <multimedia/image_framework/image/image_source_native.h>

namespace {

struct ImageResources {
  OH_ImageSourceNative* source = nullptr;
  OH_ImageSource_Info* sourceInfo = nullptr;
  OH_DecodingOptions* decoding = nullptr;
  OH_PixelmapNative* pixelmap = nullptr;
  OH_Pixelmap_ImageInfo* pixelInfo = nullptr;
  OH_PackingOptions* packing = nullptr;
  OH_ImagePackerNative* packer = nullptr;

  ~ImageResources() {
    if (packer) OH_ImagePackerNative_Release(packer);
    if (packing) OH_PackingOptions_Release(packing);
    if (pixelInfo) OH_PixelmapImageInfo_Release(pixelInfo);
    if (pixelmap) OH_PixelmapNative_Release(pixelmap);
    if (decoding) OH_DecodingOptions_Release(decoding);
    if (sourceInfo) OH_ImageSourceInfo_Release(sourceInfo);
    if (source) OH_ImageSourceNative_Release(source);
  }
};

void requireImageSuccess(Image_ErrorCode code, const char* operation) {
  if (code != IMAGE_SUCCESS) throw std::runtime_error(std::string(operation) + "失败，ImageKit 错误码 " + std::to_string(code));
}

std::string imageFormat(const uint8_t* bytes, size_t size) {
  const auto startsWith = [&](std::string_view magic, size_t offset = 0) {
    return offset <= size && magic.size() <= size - offset && std::memcmp(bytes + offset, magic.data(), magic.size()) == 0;
  };
  // ACT: API 17 没有源 MIME 查询；这里只读标准文件头，图像有效性与尺寸仍由 ImageKit 校验。
  if (startsWith(std::string_view("\x89PNG\r\n\x1a\n", 8))) return "png";
  if (startsWith(std::string_view("\xff\xd8\xff", 3))) return "jpeg";
  if (startsWith("RIFF") && startsWith("WEBP", 8)) return "webp";
  if (startsWith("GIF87a") || startsWith("GIF89a")) return "gif";
  if (startsWith("BM")) return "bmp";
  if (startsWith(std::string_view("II\x2a\0", 4)) || startsWith(std::string_view("MM\0\x2a", 4))) return "tiff";
  if (startsWith(std::string_view("\0\0\x01\0", 4))) return "ico";
  if (size >= 16 && startsWith("ftyp", 4)) {
    const uint32_t boxSize = (uint32_t(bytes[0]) << 24) | (uint32_t(bytes[1]) << 16) | (uint32_t(bytes[2]) << 8) | bytes[3];
    const size_t end = std::min(size, size_t(boxSize));
    bool heif = false;
    for (size_t offset = 8; offset + 4 <= end; offset += 4) {
      if (offset == 12) continue;
      if (startsWith("avif", offset) || startsWith("avis", offset)) return "avif";
      heif = heif || startsWith("heic", offset) || startsWith("heix", offset) || startsWith("hevc", offset)
        || startsWith("hevx", offset) || startsWith("mif1", offset) || startsWith("msf1", offset);
    }
    if (heif) return "heif";
  }
  if (std::string_view(reinterpret_cast<const char*>(bytes), std::min(size, size_t(4096))).find("<svg") != std::string_view::npos) return "svg";
  return "unknown";
}

void validateDimensions(uint32_t width, uint32_t height) {
  if (!width || !height || width > uint32_t(std::numeric_limits<int32_t>::max()) || height > uint32_t(std::numeric_limits<int32_t>::max())) {
    throw std::invalid_argument("图片宽高必须是有效的正整数");
  }
}

} // namespace

bool processNativeImage(const uint8_t* bytes, size_t size, const ImageNativeOptions& options,
  ImageNativeResult& result, std::string& error) noexcept {
  result = {};
  error.clear();
  try {
    if (!bytes || !size) throw std::invalid_argument("图片内容不能为空");
    if ((options.width == 0) != (options.height == 0)) throw std::invalid_argument("图片缩放须同时指定宽度和高度");
    if (options.quality > 100) throw std::invalid_argument("图片编码质量必须介于 0 和 100 之间");
    if (!options.format.empty() && options.format != "png" && options.format != "jpeg" && options.format != "webp") {
      throw std::invalid_argument("图片编码格式仅支持 png、jpeg、webp");
    }

    ImageResources image;
    requireImageSuccess(OH_ImageSourceNative_CreateFromData(const_cast<uint8_t*>(bytes), size, &image.source), "读取图片");
    requireImageSuccess(OH_ImageSourceInfo_Create(&image.sourceInfo), "创建图片信息");
    requireImageSuccess(OH_ImageSourceNative_GetImageInfo(image.source, 0, image.sourceInfo), "读取图片信息");
    requireImageSuccess(OH_ImageSourceInfo_GetWidth(image.sourceInfo, &result.width), "读取图片宽度");
    requireImageSuccess(OH_ImageSourceInfo_GetHeight(image.sourceInfo, &result.height), "读取图片高度");
    validateDimensions(result.width, result.height);
    result.format = imageFormat(bytes, size);
    if (options.format.empty()) return true;

    const uint32_t width = options.width ? options.width : result.width;
    const uint32_t height = options.height ? options.height : result.height;
    validateDimensions(width, height);
    const uint64_t pixels = uint64_t(width) * height;
    // ImageKit 对单张解码位图限制为 2 GiB；先检查 RGBA 字节数，避免尺寸乘法溢出。
    if (pixels > uint64_t(std::numeric_limits<int32_t>::max()) / 4) throw std::length_error("图片解码尺寸超过 ImageKit 的 2 GiB 限制");
    if (pixels > (std::numeric_limits<size_t>::max() - 65536) / 8) throw std::length_error("图片编码缓冲区尺寸溢出");

    requireImageSuccess(OH_DecodingOptions_Create(&image.decoding), "创建图片解码选项");
    requireImageSuccess(OH_DecodingOptions_SetPixelFormat(image.decoding, PIXEL_FORMAT_RGBA_8888), "设置图片像素格式");
    requireImageSuccess(OH_DecodingOptions_SetDesiredDynamicRange(image.decoding, IMAGE_DYNAMIC_RANGE_SDR), "设置图片动态范围");
    Image_Size desiredSize{width, height};
    requireImageSuccess(OH_DecodingOptions_SetDesiredSize(image.decoding, &desiredSize), "设置图片尺寸");
    requireImageSuccess(OH_ImageSourceNative_CreatePixelmap(image.source, image.decoding, &image.pixelmap), "解码图片");
    requireImageSuccess(OH_PixelmapImageInfo_Create(&image.pixelInfo), "创建像素信息");
    requireImageSuccess(OH_PixelmapNative_GetImageInfo(image.pixelmap, image.pixelInfo), "读取像素信息");
    requireImageSuccess(OH_PixelmapImageInfo_GetWidth(image.pixelInfo, &result.width), "读取输出宽度");
    requireImageSuccess(OH_PixelmapImageInfo_GetHeight(image.pixelInfo, &result.height), "读取输出高度");
    if (result.width != width || result.height != height) throw std::runtime_error("ImageKit 输出尺寸与指定尺寸不一致");

    requireImageSuccess(OH_PackingOptions_Create(&image.packing), "创建图片编码选项");
    std::string mime = "image/" + options.format;
    Image_MimeType mimeType{mime.data(), mime.size()};
    requireImageSuccess(OH_PackingOptions_SetMimeType(image.packing, &mimeType), "设置图片编码格式");
    requireImageSuccess(OH_PackingOptions_SetQuality(image.packing, options.quality), "设置图片编码质量");
    requireImageSuccess(OH_PackingOptions_SetDesiredDynamicRange(image.packing, IMAGE_PACKER_DYNAMIC_RANGE_SDR), "设置编码动态范围");
    requireImageSuccess(OH_ImagePackerNative_Create(&image.packer), "创建图片编码器");

    // ACT: API 12 不能预查询编码长度；为 RGBA 输出预留双倍原始字节与头部空间，失败原样报错。
    result.bytes.resize(size_t(pixels * 8 + 65536));
    size_t outputSize = result.bytes.size();
    requireImageSuccess(OH_ImagePackerNative_PackToDataFromPixelmap(image.packer, image.packing, image.pixelmap, result.bytes.data(), &outputSize), "编码图片");
    if (!outputSize || outputSize > result.bytes.size()) throw std::runtime_error("ImageKit 返回了无效的编码长度");
    result.bytes.resize(outputSize);
    result.format = options.format;
    return true;
  } catch (const std::exception& failure) {
    result = {};
    error = failure.what();
    return false;
  } catch (...) {
    result = {};
    error = "ImageKit 处理图片失败";
    return false;
  }
}
