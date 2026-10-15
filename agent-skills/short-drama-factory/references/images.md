# 图片与项目参考图（3.0.0+）

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
- `request.optimized_prompt` 可以传用户编辑后的最终提示词，非空时不再调用文字模型；`optimize:false` 且未填该字段时直接使用原描述。
- `provider`、`model`、`skill` 可覆盖图片默认设置；Skill 阶段为 `image_prompt`。`purpose` 可选 `general/character/scene/prop`。尺寸档为 `auto/512/768/1024/1536/2048`；`seed` 可留空或为 0～9007199254740991 的整数。
- `status:complete`、`busy:false`、`file_available:true` 才表示图片已落盘；还需实际查看图片是否满足用户要求。通过 `download /api/images/IMAGE_ID/file --output result.png` 下载，不覆盖同名文件。
- `POST /api/images/{id}/resume`，请求体 `{}`，继续同一任务并核对原 ComfyUI 提交；结果未知时不会自动重生成。
- `POST /api/images/{id}/regenerate`，请求体 `{}`，新建图片记录并更换种子；可传 `{"request":{"prompt":"新的描述"}}` 覆盖参数。旧图保留。
- `POST /api/images/{id}/stop`，请求体 `{}`，停止该图片自己的任务；旧图的停止操作不应取消同项目其他任务。

`GET /api/images` 返回最近 200 条记录，不代表全部历史。任务 `error/paused` 要先看 `message`；`complete` 记录缺失文件时应恢复文件或明确重新生成。

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

采用历史：`POST /api/projects/{pid}/image-references/{target}/adopt`，请求体 `{"image_id":"该目标已有历史 ID"}`。项目必须空闲，受影响的锁定镜头需先按用户意图解锁。换图会清理受影响的旧提示词；手写 H3 提示词需按实际新绑定补齐。

角色图只绑定出场角色；场景图、道具图不得赋人物身份。已有手动角色素材会保留。视频应选自动或 Ref2VA 才使用这些参考；明确 T2VA 不使用参考图，首帧接续仍使用前镜实际末帧。

项目迁移包含参考素材与历史映射，导入 3.0.0+ 后仍可采用历史版本；独立图片库不随单项目迁移。

## 环境准备

遵照用户的安装和下载授权。自动下载默认开启，生成前必须查看实际清单；首次可能下载大型模型及独立运行时。需要准备时 `POST /api/images/environment/prepare`，请求体 `{"variant":"auto"}`；暂停用 `/api/images/environment/stop`。远程缺模型要在远端安装，本机下载不会修复远端。

全局设置用 `GET /api/config` 的 `image_generation` 获取，保留未知字段，仅改必要项，再 `POST /api/images/settings` 保存完整设置。不要为单个请求覆盖全局提供商或环境。模型选项、授权与硬件说明见项目 `docs/image-studio.md`。
