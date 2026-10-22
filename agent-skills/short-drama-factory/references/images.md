# 图片与项目参考图

新图片、输入图与项目素材优先通过 `sdf image create/input`、`asset upload` 使用版本化提交回执；查询和已有图片的管理仍复用 `/api/images`。先查询 `/api/images/models` 和目标 `/api/images/environment/plan`，依据实际支持的模型、输入模式、透明通道、采样器与资源状态执行。

当前 AI 已经编写提示词时默认 `optimize:false`。用户选择工厂文字优化时才设 true；该值在旧服务端默认 true，不能省略后假定没有文字调用。`image_model` 指生图模型，`provider/model` 指文字优化服务。

## 独立图片

通过 `sdf.py image create --json image-request.json --wait 45` 提交：

```json
{
  "request": {
    "prompt": "雨后小巷，暖色灯光映在石板路上，没有人物",
    "optimize": false,
    "purpose": "scene",
    "ratio": "16:9",
    "resolution": "auto",
    "variant": "auto"
  },
  "optimize_only": false
}
```

省略 image_model 继承当前实例图片默认设置；选择具体模型时填查询返回的 ID。返回 image id 与 job_id 后精确跟踪。版本化创建接口 `/api/v2/images` 默认 internal_text=forbid、optimize=false，禁止隐式下载；需要文字优化时同时明确 optimize=true 和 `--allow-internal-text`。响应丢失通过 operation get/retry 恢复同一次提交。

| 操作 | 接口与行为 |
| --- | --- |
| 查看 | GET `/api/images/{id}`；status=complete、busy=false、file_available=true 才有落盘成果 |
| 获取图 | GET `/api/images/{id}/file`；下载后实际查看，不把成功状态当作画面验收 |
| 只优化 | 创建请求 optimize_only=true；会调用文字模型，得到 ready，不产生图片 |
| 继续已优化图片 | POST `/{id}/generate`，可传 `{"request":{"optimized_prompt":"最终文本"}}`；非空已定稿文本不再优化 |
| 续跑 | POST `/{id}/resume`，`{}`；继续同一图片／任务，核对原引擎提交 |
| 新版本 | POST `/{id}/regenerate`；新图片记录、换种子，旧图保留，可覆盖 request |
| 停止 | POST `/{id}/stop`；仅停止该图片拥有的任务 |
| 删除 | POST `/{id}/delete`；仅在用户要求删除时执行，项目内已复制素材仍保留 |

以上管理短路径基于 `/api/images`，属于 legacy 操作，不具备 v2 创建请求的幂等契约；它们的超时先查原图与原任务，不盲目重发。已提交到引擎后不能修改生成参数；先等待或停止，再明确创建新版本。GET `/api/images` 最近记录不代表所有历史，优先保留精确 ID。

## 原图与多图输入

1. `sdf image input --file 角色.png`，或 POST `/api/v2/image-inputs` 加幂等头，请求 `{"name":"角色.png","data":"纯base64"}`，使用返回的真实 id。支持 PNG/JPEG/WebP，每张上限 8MB；方向和尺寸可能规范化。
2. 在 request.reference_images 中按顺序填写 ID。允许张数、reference_mode 与透明通道由所选模型能力决定，不盲套 Qwen 的上限到其他模型。
3. Qwen 的 `reference` 是多图语义参考创作；`edit` 使用第一张原图比例。其他已支持架构常为单张原图 VAE 重绘，不能声称多图语义融合。
4. Qwen 提示词以 `<image1>`、`<image2>` 对应顺序；其他架构按其能力描述最终画面，不照搬专用标签。

```json
{"request":{"prompt":"保留 <image1> 的角色身份，将衣服改为红色，其余保持","reference_images":["替换为上传返回的真实ID"],"reference_mode":"edit","optimize":false}}
```

本例 ID 必须替换后才能提交。GET `/api/image-inputs/{id}` 查看规范化输入；POST `/api/images/{id}/use-as-reference` 将成图复制成可复用输入。原图片删除不会删除该独立输入。

任务保存自己的 reference_inputs 快照。文字优化仅获得文字与参考数量，不会看到参考像素；远程 ComfyUI 会收到实际图片，按用户已选择的服务执行。

采样参数使用 request.sampling；字段与可选范围查实例 Schema 和 model_plan.sampling_support，实际值看 effective_sampling。denoise<1 是原图 VAE 重绘强度，需要 edit 与真实原图，不是人物相似度保证。提高步数／CFG 不保证质量或身份一致。

## 项目参考图

先完成分镜，GET `/api/projects/{pid}/image-references` 读取 candidates[].key，不猜 target。可按单项显式生成：

```text
POST /api/projects/{pid}/image-references/{target}/generate
{"request":{"prompt":"当前AI编写的完整参考图提示词","optimize":false}}
```

完成后检查 selected_asset、history 与最新 story 是否采用了正确素材，不能只看到 PNG 就认定绑定成功。换参考图可能清空相关旧 prompt；当前 AI 补齐后再建 render 计划。

将用户原图作为生成依据：先用 `sdf asset upload --project PID --file 原图.png --kind image` 上传项目素材，再 POST `/api/projects/{pid}/image-references/{target}/sources`，请求 asset_ids 与 reference_mode；这些是该项目真实图片 ID，不是独立图片输入 ID。返回的候选包含配置。采用历史用 `/{target}/adopt`，请求 `{"image_id":"该目标已有历史ID"}`。

人物图 character 只标真实人物；场景／道具图不赋人物身份。普通人物参考用于 Ref2VA；首帧用于 I2VA，二者不同。实际末帧接续始终使用紧邻上一镜的视频，不用新角色图替代。

视频项目 reference_images.enabled 默认关闭；严格 render 即使已有项目开启它也跳过自动图片准备，仅采用现有绑定。允许内部创作的 plan 阶段启用该项时可能生成图片、优化文字并改写分镜，计划会说明。自动参考图的 optimize 也应按用户是否选择内部文字优化明确设置。

## 准备与恢复

模型缺项按 [资源准备](workflow-models.md) 先计划再执行；保留原 confirmation_token 与所选参数。来源 token 不是用户授权本身，已有授权也不需要重复索要。

环境进度用 `/api/images/environment/progress` 并核对 job_id；图片进度用精确图片 ID 和任务 ID。环境 stop 与图片 stop 是不同操作。远程缺模型必须在远端准备，本机下载不会修复远端。

获取 `/api/config` 的 image_generation 查看默认设置。单个请求优先覆盖 request，不顺带改变全局提供商、模型或环境。模型许可读取实际模型说明，项目许可证不覆盖权重。
