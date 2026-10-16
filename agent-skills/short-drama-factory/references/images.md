# 图片与项目参考图（3.0.1）

先读 `/api/health` 核对实例及版本，再读 `/api/images/environment`。该接口检测目标 ComfyUI 的节点、模型、显存、下载清单与许可；`ready:true` 才表示当前方案可以生成。`/api/images/environment/progress` 返回准备状态。Qwen-Image 2.1 为非商用研究许可，商业用途需要模型方授权；应用 MIT 不覆盖模型权重。

## 独立图片

将请求保存为 UTF-8 JSON 文件，用现有客户端 `post /api/images --json image-request.json` 提交一次：

```json
{
  "request": {
    "prompt": "雨后小巷，暖色灯光映在石板路上，没有人物",
    "optimize": true,
    "purpose": "scene",
    "ratio": "16:9",
    "resolution": "auto",
    "variant": "auto"
  },
  "optimize_only": false
}
```

- 返回 `id` 和 `job_id`。记录它们；每次通过 `GET /api/images/{id}` 观察原任务，不因超时重复创建。
- `optimize_only:true` 只优化，结果为 `optimized_prompt`，状态为 `ready`；没有图片文件。
- 优化完成后用 `POST /api/images/{id}/generate`，传 `{"request":{"optimized_prompt":"用户编辑后的结果"}}`，继续原图片及任务 ID。可覆盖尚未采样的其他请求字段；`optimize_only:true` 可在原记录重新优化。必须等 `busy:false`；已提交到 ComfyUI 的任务只能原样恢复，不能悄悄改参数。
- `request.optimized_prompt` 可以传用户编辑后的最终提示词，非空时不再调用文字模型；`optimize:false` 且未填该字段时直接使用原描述。
- `provider`、`model`、`skill` 可覆盖图片默认设置；Skill 阶段为 `image_prompt`。`purpose` 可选 `general/character/scene/prop`。尺寸档为 `auto/512/768/1024/1536/2048`；`seed` 可留空或为 0～9007199254740991 的整数。
- `status:complete`、`busy:false`、`file_available:true` 才表示图片已落盘；还需实际查看图片是否满足用户要求。通过 `download /api/images/IMAGE_ID/file --output result.png` 下载，不覆盖同名文件。
- `POST /api/images/{id}/resume`，请求体 `{}`，继续同一任务并核对原 ComfyUI 提交；结果未知时不会自动重生成。
- `POST /api/images/{id}/regenerate`，请求体 `{}`，新建图片记录并更换种子；可传 `{"request":{"prompt":"新的描述"}}` 覆盖参数。旧图保留。
- `POST /api/images/{id}/stop`，请求体 `{}`，停止该图片自己的任务；旧图的停止操作不应取消同项目其他任务。
- `POST /api/images/{id}/delete`，请求体 `{}`，在用户要求删除时移除图片库中的原图、工作流与记录；任务和所属项目必须空闲，仍在 ComfyUI 执行的图片先停止。项目已有素材副本与历史引用保留。
- `request.models` 可选对象，字段为 `diffusion_models`、`text_encoders`、`vae`，值须取自环境计划的 `available_models`。省略对象继承全局选择，字段留空使用推荐文件；文件须为 Qwen-Image 2.1 兼容组合，不接受绝对路径。

`GET /api/images` 返回最近 200 条记录，不代表全部历史。任务 `error/paused` 要先看 `message`；`complete` 记录缺失文件时应恢复文件或明确重新生成。

## 图生图与多图参考（3.1.0）

按用户指定的图片服务处理参考图：本地服务在本机处理，远程 ComfyUI 会收到图片。文字优化服务只收到文字、参考张数和模式，不会收到参考图片像素。

1. `POST /api/image-inputs`，JSON 为 `{"name":"角色.png","data":"图片文件的纯 base64"}`。支持 PNG/JPEG/WebP，每张最多 8MB。返回 `id`、`url`、`width`、`height`；不接受本地绝对路径或任意 URL。程序纠正方向并规范化为 PNG，可能缩小过大图片。
2. 把返回的真实 ID 按顺序写入 `request.reference_images`，最多 10 张、不重复。不要将文件名当 ID。16GB 显存先用 1～3 张、512 或 768 档。
3. `request.reference_mode:"reference"` 按所选 `ratio` 创作新图；`"edit"` 沿用第一张原图比例，第一张比例需在 1:4 至 4:1 之间。编辑必须有参考图。没有参考图时用 `reference`，即普通文生图。描述中用 `<image1>`、`<image2>` 指定人物、服装、场景或风格；保留用户指定的编辑范围。

示例（替换为上传返回的真实 ID）：

```json
{"request":{"prompt":"保留 <image1> 的角色身份，将衣服改为红色，其余保持","reference_images":["上传返回的ID"],"reference_mode":"edit","optimize":false,"resolution":"512"}}
```

`GET /api/image-inputs/{id}` 读取输入信息；`/{id}/file` 读取规范化图片。`POST /api/images/{image_id}/use-as-reference`，请求 `{}`，将已完成成图复制为可复用输入，返回同样的输入结构。图片库原图后来删除时，该输入仍保留。

任务保存自己的参考图快照，`GET /api/images/{id}` 的 `reference_inputs` 含编号顺序、校验值和可读取的 `url`（`/api/images/{id}/references/{index}`，index 从 1 开始）。优化完成后继续 `/{id}/generate` 时保留 `reference_images` 与 `reference_mode`；更换输入会清除旧优化结果。续跑已提交任务保持原参数，先核对原 prompt_id，不因参考图上传超时重新创建任务。`/{id}/regenerate` 沿用输入，可按用户要求覆盖为新的输入 ID。

这里使用 Qwen-Image 2.1 原生参考条件，没有额外“相似度／重绘强度”参数。实际身份、风格和编辑区域遵循程度需要看图验收，不能仅凭 API 完成就宣称一致。

## 项目参考图

创建项目的 `options` 或保存项目完整 `settings` 时，可配置：

```json
"reference_images": {
  "enabled": true,
  "characters": true,
  "scenes": true,
  "props": false,
  "optimize": true,
  "resolution": "auto",
  "variant": "auto",
  "provider": "",
  "model": ""
}
```

先完成分镜，再读 `GET /api/projects/{pid}/image-references`，使用返回的 `candidates[].key`，不要猜测 target。`POST /api/projects/{pid}/image-references/generate` 可传 `{}` 自动补齐，或 `{"targets":["实际 key"]}` 明确重新生成指定项。

单项生成：`POST /api/projects/{pid}/image-references/{target}/generate`，请求体 `{}` 或 `{"request":{"prompt":"修改后的描述"}}`。完成后自动采用；仍须读取候选的 `selected_asset`、`history` 和项目分镜，确认引用成功，不能只看到 PNG 就声称已绑定。

自定义角色／场景生成依据（3.1.0）：先用 `/api/projects/{pid}/assets` 上传图片，JSON 为 `{"type":"image","name":"角色原照","data":"纯base64","character":""}`，或选该项目已有图片素材。然后 `POST /api/projects/{pid}/image-references/{target}/sources`，传 `{"asset_ids":["项目素材ID"],"reference_mode":"reference"}`；最多 10 张，顺序决定图片编号。接口只接受本项目存在的图片素材，项目需空闲、相关镜头需解锁。`asset_ids:[]` 且模式 `reference` 可清除依据，不删除素材。候选的 `source_assets` 与 `reference_mode` 用于核对保存结果。

该配置供单项、批量及自动补齐使用，并随项目迁移保留。参考源是输入依据；生成并采用的新版本才进入分镜绑定。已有手动角色素材在未配置自定义生成依据时仍优先保留。修改参考源后，自动补齐会更新对应输出版本。

采用历史：`POST /api/projects/{pid}/image-references/{target}/adopt`，请求体 `{"image_id":"该目标已有历史 ID"}`。项目必须空闲，受影响的锁定镜头需先按用户意图解锁。换图会清理受影响的旧提示词；手写 H3 提示词需按实际新绑定补齐。

角色图只绑定出场角色；场景图、道具图不得赋人物身份。已有手动角色素材会保留。视频应选自动或 Ref2VA 才使用这些参考；明确 T2VA 不使用参考图，首帧接续仍使用前镜实际末帧。

项目迁移包含参考素材与历史映射，导入 3.0.0+ 后仍可采用历史版本；独立图片库不随单项目迁移。

## 环境准备

遵照用户的安装和下载授权。先 `POST /api/images/environment/plan`，请求体 `{"variant":"auto","models":null}`，读取文件、下载大小、目标目录、`requires_confirmation` 与 `confirmation_token`。缺模型时应向用户展示实际清单并确认是否下载；不要把读取到 token 当作用户已同意。

确认后将原计划的 `confirmation_token` 作为 `download_confirmation` 传入 `/api/images`、`/{id}/generate`、`/{id}/resume`、`/{id}/regenerate` 或项目参考图生成接口。也可 `POST /api/images/environment/prepare`，传原 `variant`、`models` 和 `download_confirmation` 仅准备环境。模型／位置变化时重新读取并确认，不能复用过期确认。旧 `auto_download:true` 不绕过检查。取消后不会下载；未确认的后台任务会暂停并保留记录。

环境进度读取 `/api/images/environment/progress`，核对 `job_id`，并结合 `/api/jobs` 的排队状态；图片任务准备进度在 `GET /api/images/{id}`。`progress` 含 `file`、`bytes`、`total`，任务信息包含当前阶段。暂停环境用 `/api/images/environment/stop`，暂停图片用对应图片的 `/stop`；恢复时确认当前清单后继续。远程缺模型要在远端安装，本机下载不会修复远端。

全局设置用 `GET /api/config` 的 `image_generation` 获取，保留未知字段，仅改必要项，再 `POST /api/images/settings` 保存完整设置。不要为单个请求覆盖全局提供商或环境。模型选项、授权与硬件说明见项目 `docs/image-studio.md`。
