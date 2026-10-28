# 资源准备与自定义方案

能力选择只维护在 [工作流选择](workflow-selection.md)；具体模型文件、参数及兼容模式从当前实例查询。执行计划不授权隐式下载，已有本地文件待校验也不等于需要重新下载。

## 查询与准备

| 能力 | 先查询 | 显式准备入口 |
| --- | --- | --- |
| 基础视频环境 | `/api/environment/plan`、`/api/environment/catalog` | `/api/environment/install`，请求字段查当前安装计划 |
| 某视频工作流附加资源 | GET `/api/video/workflows/plan?profile=ID` | POST `/api/video/workflows/prepare` |
| 图片模型 | POST `/api/images/environment/plan` | POST `/api/images/environment/prepare` |

视频准备传 `profile` 和当前计划的 `download_confirmation`；图片准备传相同 `image_model`、`variant`、`models` 和 `download_confirmation`。后者的值来自计划 `confirmation_token`，不能自造或沿用已变更资源的旧 token。精确字段以实例返回为准。

先说明新增下载量、文件及位置；已有授权覆盖时直接执行，否则只对新增资源请求一次决定。下载量为零时不询问“下载 0GB”。准备任务返回 job_id 后跟踪该任务；准备完成不表示视频已生成。资源或配置变更后回原项目重新计算执行计划。

CPU 语音检测用于后期音区间分析，可能也有缺失模型。`SPEECH_MODEL_MISSING` 是资源准备问题；不退化成“已识别台词”，也不重新生成已完成视频。运行 `sdf environment speech-plan`，已有授权覆盖时将返回的 confirmation_token 传给 `sdf environment speech-prepare --confirmation TOKEN`。这是独立下载任务；跟踪完成后回原项目重新计划。

`/api/environment/verify` 是创建测试项目并实际渲染的生成测试，不能作为只读 doctor 使用。

## 参数与环境配置

获取 `/api/config` 的实际 profiles。需要新组合时通过 `POST /api/video/workflows/profiles` 另存，例如：

```json
{"base_profile":"pdd-8","label":"四步构图试镜","changes":{"megapixels":0.4,"steps":4}}
```

只有实例声明支持该方案和步数时才使用。取得新 ID 后，通过版本化项目更新修改 `settings.profile`，再计划本次执行；不改变其他项目。PDD 训练网格、LightX2V 固定步数、Turbo v4 的 6/8 步、高级工作流控制区间等约束交给能力目录与服务端校验，不在多个文档重复维护参数表。快速生成默认使用 `larry-turbo`；需要 6 步时以上面的方式另存，不能直接改成 4 步。显存不足时可另存 `low_vram:true`（合并 LoRA，量化底模画质略软），不要自行改动节点或底模量化方式。

图片整合模型文件使用其模型契约要求的槽位，如 `models.checkpoints`；文件名相似不能证明兼容。原图重绘、透明通道、多参考能力见 [图片接口](images.md)。

使用 `sdf config get/patch` 做授权范围内的无界面配置，凭证走 `credential set` 的环境变量／标准输入，详见 [CLI](cli.md)。只读诊断不启动引擎；真正渲染会按配置启动或复用引擎。不能杀掉不明进程、公开本机接口或将远程模型准备假装成本地安装。
