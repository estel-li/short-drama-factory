# 选择模型与工作流（3.2.0）

选择方案之前先读 [完整工作流选择指南](workflow-selection.md)。以下保留各方案的接口与详细契约；3.5 的预检会检查源帧数、模式及接续上限。

3.3 新增的五类 H3 媒体工作流、源素材槽、原声／原画面锁定和接续时长规则见 [H3 高级媒体工作流](h3-advanced.md)。本页保留 3.2 的多模型与三条视频基础方案说明。

先读取运行实例的 `GET /api/config`、`GET /api/images/models`。使用返回的实际 ID 和参数，不把文件名相似当成兼容，也不把候选清单当作生成已经完成。已生成任务保留模型、工作流和 prompt_id，超时先查询原任务。

## 图片

`image_model` 是生图模型 ID；`provider`、`model` 仍是文字优化提供商和文字模型。省略 `image_model` 时，新任务继承图片默认设置；旧任务缺少该字段时按 Qwen 恢复，避免新版默认值改变旧图的模型。

1. 从 `/api/images/models` 的 `models` 选择模型，读取 `sampling`、`reference_modes`、`max_reference_images`、`transparent_support`。Qwen 支持多图语义参考，其他内置架构使用单张原图重绘。不可向不支持的架构传入多图或透明通道要求。
2. `POST /api/images/environment/plan` 传入 `{"image_model":"sdxl-base","variant":"auto","models":null}`。`models` 可指定与该架构兼容的本地文件；整合模型使用 `checkpoints`，Qwen/Z-Image 使用各自分体文件。
3. 需要下载时核对真实大小与目录。用户已授权下载模型时可继续，否则先征求确认。`POST /api/images/environment/prepare` 使用同一份参数，并附上原计划的 `download_confirmation:confirmation_token`，保存返回的 `job_id`，查询 `/api/images/environment/progress`。本地待校验不等于缺少模型。
4. 创建图片的请求体有一层 `request`：

```json
{
  "request": {
    "image_model": "sdxl-base",
    "prompt": "A sunlit bookstore with wooden shelves and a red book on a desk.",
    "optimize": false,
    "resolution": "1024",
    "sampling": {"steps":28,"cfg":7,"sampler":"dpmpp_2m","scheduler":"karras"}
  },
  "optimize_only": false
}
```

发往 `POST /api/images`。想让文字模型优化则使用 `optimize:true`，并选择用户授权的文字提供商；例子关闭优化以便直接复现 GPU 测试。需要下载确认时另在外层加入 `download_confirmation`。

单张重绘使用 `reference_images:[输入图片ID]`、`reference_mode:"edit"` 和小于 1 的 `sampling.denoise`，后端会从原图 VAE 编码开始。强度为 1 会充分重绘，不能承诺保留身份。Qwen 的多图语义参考与这种重绘不同。具体上传、删除、继续原任务和项目参考图接口见 [图片说明](images.md)。项目自动参考图的模型放在 `options.reference_images.image_model`。

## 视频

视频方案继续通过项目的 `options.profile` 选择。从 `/api/config` 的 `profiles` 读取 ID、`workflow`、分辨率与步数。新增内置方案为 `lightx2v-8`、`pdd-8`、`pdd-upscale`；用户另存的方案会得到 `custom-*` ID。

- `lightx2v-8` 使用专用 8 步 LoRA，保持 8 步；用于文字、首帧、尾帧和首尾帧。多参考模式使用 PDD 或原生方案。
- `pdd-8` 同时应用 LoRA 和 PDD 头，使用 Euler、SigmaShift 12/3 与对应训练网格，不能只当普通 LoRA 加载。支持 4、6、8 步，不叠加原 Turbo LoRA。
- `pdd-upscale` 首遍 PDD 8 步后，使用独立 3D 神经网络放大，再以一个训练块轻精修。默认倍数 1.25、精修强度 0.125；强度 0 跳过精修。最终尺寸按 32 像素网格对齐，帧数不变，保留首遍音频。

先 `GET /api/video/workflows/plan?profile=pdd-upscale`，检查节点、文件和目标目录。使用 `POST /api/video/workflows/prepare`，传入 `profile` 和匹配计划的 `download_confirmation`；查询 `/api/video/workflows/progress`，停止准备调用 `/api/video/workflows/stop`。准备任务独立于视频项目，不等于已渲染镜头。

缺失节点从固定 GitHub 提交下载并验证 SHA256；模型从固定 Hugging Face 版本获取。已有只读模型目录可直接复用，校验收据保存在应用数据目录。新增节点需要重启时，只会重启本应用可确认归属、且队列空闲的服务；自行启动或远程服务交给其所有者处理。

需要新参数组合时，可调用 `POST /api/video/workflows/profiles`：`{"base_profile":"pdd-8","label":"我的 PDD 草稿","changes":{"megapixels":0.4,"steps":4}}`，获得新 ID 后保存到项目设置。不要修改其他项目的参数。生成与完整验收仍按主 Skill 的预检、排队、解码和音画检查流程执行。
