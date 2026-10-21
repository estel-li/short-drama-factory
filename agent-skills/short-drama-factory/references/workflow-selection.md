# 工作流选择与执行（3.6.0）

先读取 `/api/video/workflows` 与 `/api/images/models`，使用当前实例的 ID、支持模式、必需槽位和推荐参数。自定义方案通常为 `custom-*`，按 `workflow` 判断能力，不按名称猜测。详细媒体参数见 [H3 媒体契约](h3-advanced.md)，资源准备见 [模型与工作流接口](workflow-models.md)。

## 按目标选择

用户已指定工作流时尊重其选择，检查输入条件。未指定时，先判断必须保留什么：

1. **已有配音，必须用原声** → `h3-audio-drive`。有人物图则绑定首帧；普通音频参考不能代替原声锁定。
2. **画面必须保留，仅换声音** → `h3-foley`。它不用于修改人物、动作、画风或口型。
3. **从前段末尾继续动作及声音** → `h3-motion-context`。只需要上一镜最后一张图时，可用原生 I2VA + `use_previous_last_frame`，开销通常更低。
4. **按视频的轮廓动作换画风** → `h3-canny-control`。轮廓约束不锁定人物身份，可用适用的首帧辅助。
5. **片段中间要经过指定构图** → `h3-keyframe-guide`。只有首帧／尾帧要求时，普通 I2VA／L2VA／FL2VA 即可。
6. **常规生成，先确认剧情构图** → 已就绪的 `draft` 或 `pdd-8`；PDD 可另存为 4 步。动作试镜且无需 Ref2VA 可选 `lightx2v-8`。
7. **构图验收后，提高新镜头清晰度** → `pdd-upscale`。它会从头生成再放大，不是对现成 MP4 的通用放大工具。
8. **常规对白或质量优先** → 原生 `dialogue`；短镜验证资源充足后再考虑 `detail`。提高步数不保证质量提升。

说明选择理由、实际输入和一个关键限制即可。缺素材时先准备可完成的分镜与参数，再询问缺项；不要偷偷换成 T2VA、重复末帧或用静音冒充指定原声。环境失败也不能成为改变创作要求的理由。

## 全部内置视频方案

**模式**决定文字、关键帧或多模态输入；**工作流**决定加速、锁音、锁画面、接续或控制。二者是不同设置。

| profile（workflow） | 用途 | 支持模式 | 必需素材与默认参数 |
| --- | --- | --- | --- |
| `draft`（`native`） | 快速预览 | 五种模式 | 0.4MP、4 步、原 Turbo；素材由模式决定 |
| `dialogue`（`native`） | 常规对白与动作 | 五种模式 | 0.4MP、12 步、无 Turbo |
| `detail`（`native`） | 更高分辨率短镜 | 五种模式 | 0.6MP、20 步、无 Turbo |
| `lightx2v-8` | 动作与关键帧试镜 | T2VA / I2VA / L2VA / FL2VA | 0.4MP、固定 8 步、专用 LoRA、res_multistep |
| `pdd-8` | 加速及多模态参考 | 五种模式 | 0.4MP、默认 8 步，可选 4/6/8；Euler、专用 PDD 头，关闭旧 Turbo |
| `pdd-upscale` | 生成后神经放大 | 五种模式 | 0.4MP、首遍 8 步、1.25 倍；精修 0 或 0.125，保留首遍音频 |
| `h3-audio-drive` | 原声驱动画面 | 五种模式 | `source_audio`；0.4MP、12 步；可加首帧，源起点 0 秒 |
| `h3-foley` | 保留画面重做拟音 | **T2VA** | `source_video`；0.4MP、12 步；无独立首尾帧 |
| `h3-keyframe-guide` | 中途画面引导 | 五种模式 | `guide_image`；0.4MP、12 步；位置 0.5，可加首尾帧 |
| `h3-motion-context` | 延续动作与声音 | **T2VA / Ref2VA** | `source_video`；0.4MP、12 步；画面上下文 22 帧、声音 18 帧，无独立首尾帧 |
| `h3-canny-control` | 按轮廓重绘风格 | T2VA / I2VA / L2VA / FL2VA | `source_video`；0.4MP、12 步；阈值 0.2/0.5、强度 0.7、区间 0～0.9 |

五种模式为 T2VA、I2VA、L2VA、FL2VA、Ref2VA，提示词结构与标签见 [H3 契约](story-and-h3.md)。

`options.profile` 是**项目级**设置，不能给每个镜头随意加不同 profile 并期待生效。高级工作流的每个镜头都需满足素材条件。混合需求先按相同工作流分组制作并分别交付，或与用户约定组合方式，不用同一全局设置覆盖不兼容镜头。

LightX2V、拟音与轮廓控制不支持 Ref2VA；有人物且使用自动模式时，先关闭 `auto_reference` 或明确指定合适的文字／关键帧模式，避免后续自动提取的人物图改变模式。显式上传的多模态素材与所选方案冲突时，预检会提示修正。

## 参数、性能与时长

- 16GB 显存从 0.4MP、每镜 4～8 秒起步，一次只运行一个图片／视频 GPU 任务。应用会释放空闲引擎中的模型；忙碌服务需要等待。外置显卡传输、冷加载与卸载影响总耗时，不能仅凭步数承诺运行秒数。
- 五种高级媒体方案使用完整原生采样，不叠加旧 Turbo，不把 denoise 改成局部重绘。PDD 使用训练网格与专用头，不能任意写 5 步或换采样器。
- 视频为 24fps，帧数对齐到 `17k+5`。4 秒请求需要 107 帧（约 4.458 秒）；4 秒／96 帧的源片不够用于该镜长的拟音或轮廓控制。先读 `/api/duration-plan` 和项目 preflight。
- 原声按对齐后的时长裁剪，短音轨补静音，起点超出音轨会拒绝。不要把补静音后的文件说成完整配音。
- 多帧接续取末尾 5/22/39/56 帧，采样后剪去重叠头部。实际开销包括上下文：`目标帧数 + ceil(context_frames/17)*17 <= 362`。15 秒目标叠加上下文会超限，需要缩短。
- 神经放大按 32 像素网格对齐。1.25 倍约增加 56% 像素，实际有取整误差。精修 0 只跳过第二次采样，仍执行放大。
- 3.5 源视频节点只保留需要的目标尺寸帧，降低整段高分辨率解码的内存占用；它不消除模型本身的显存需求。

另存方案示例，发送到 `POST /api/video/workflows/profiles`：

```json
{"base_profile":"h3-canny-control","label":"轮廓控制 · 柔和风格","changes":{"control_strength":0.5,"canny_low":0.2,"canny_high":0.5}}
```

取得新 `id` 后，读完整项目 settings，只替换 `profile`，再 `POST /api/projects/{id}/settings`。不修改其他项目。反向控制区间、低阈值大于高阈值、非法步数会拒绝。

## 实际输入与执行

1. 素材从 `/api/projects/{id}/assets` 上传，用返回的真实 ID。`source_video`、`source_audio`、`guide_image` 都是**单个 ID 字符串**，不是数组、路径或 URL。上传视频会规范为 24fps；文件格式和 8MB／15 秒限制见 [API 表](api.md)。
2. 读完整 story 再保存绑定。拟音用 `{"source_video":"实际视频ID"}`、`mode:"T2VA"`；人物原声驱动可用 `{"source_audio":"实际音频ID","first_frame":"实际人物图片ID"}`、`mode:"I2VA"`。`POST /api/story` 接收 `{"id":"…","story":完整对象}`，不能只交一个镜头。
3. 专用素材槽不产生 `<Picture N>/<Video N>/<Audio N>`。Ref2VA 普通 `images/videos/audios` 才产生多模态标签；首尾帧按各自契约编写。高级方案关闭旧 `use_previous_last_frame`。
4. `GET /api/video/workflows/plan?profile=ID` 检查附加资源，基础 H3 环境仍需检查。`verify` 表示本地文件待校验；`download_bytes` 才是下载量。远端资源在远端准备。
5. 已获下载授权时，用相同 profile 和计划的 `confirmation_token`（字段名 `download_confirmation`）调用 `/api/video/workflows/prepare`。保存 `job_id`，通过 `/api/video/workflows/progress?job_id=...` 跟踪。排队／运行继续等待，暂停／错误处理原因，完成后再读 plan。零下载但未就绪时直接校验／启动，不要询问“下载 0GB”。
6. 3.5 的项目 `/preflight` 检查素材、模式、对齐帧数、源起点及接续上限，错误带镜头 UID。`ready:false` 先修复；静音补尾和高开销提示是 warning，需要说明实际影响。
7. 按主 Skill 排队、追踪原任务并验收。POST 超时先查原任务，不重复创建。准备暂停保留断点；切换方案／素材影响后续缓存，不能承诺直接复用旧采样结果。

## 图片模型选择

接口与参考图管理见 [图片说明](images.md)。优先选择适合目标且已就绪的模型，用 `/api/images/models` 的推荐参数。`image_model` 指生图模型；`provider/model` 指文字优化服务。

| image_model | 优先用途 | 内置起步参数 |
| --- | --- | --- |
| `qwen-image-2.1` | 多图语义参考、指令编辑、原生透明通道 | 自动精度；Turbo 8 步／标准 40 步，CFG 1 |
| `sdxl-base` | 通用写实、可调采样 | 1024 档、28 步、CFG 7、dpmpp_2m / karras |
| `animagine-xl-4` | 动漫人物、标签式描述 | 1024 档、28 步、CFG 6、euler_ancestral / normal |
| `dreamshaper-8` | 轻量插画和构图草稿 | 512 档、24 步、CFG 7、dpmpp_2m / karras |
| `dreamshaper-xl-turbo` | 快速风格图 | 1024 档、6 步、CFG 2、dpmpp_sde / karras |
| `flux-schnell` | 构图及完整画面描述 | 1024 档、4 步、CFG 1、euler / simple |
| `z-image-turbo` | 中文提示与写实草稿 | 1024 档、9 步、CFG 1、euler / simple |

除 Qwen 外，当前都是单张原图 VAE 重绘：`reference_mode:"edit"`，一张 `reference_images`。保留原图可先试 denoise 0.4～0.6，但不能承诺低强度一定完成局部修改。多图身份融合优先 Qwen，不自动丢弃多余参考图。透明背景也只用声明支持的模型。切换架构需重新优化提示词，不沿用另一模型的图片编号与专用指令。商用需求应读取实际模型许可，项目 MIT 不覆盖权重。

## 选择示例与验收

| 需求 | 方案 | 重点检查 |
| --- | --- | --- |
| “用这段配音让人物说话” | audio-drive + 人物首帧 | 原声、静音尾部、口型；不承诺逐字精确 |
| “画面不动，补脚步和关门声” | foley + T2VA | 画面顺序、动作音时机 |
| “接着上个镜头往前走” | motion-context；只需末帧可原生 I2VA | 切口、重复动作、去除重叠头部 |
| “按实拍动作改成动漫” | canny-control + 适用关键帧 | 运动结构、风格、人物漂移 |
| “中间要走到这张构图” | keyframe-guide | 关键时刻与动作合理性 |
| “三个人物参考图，快速试镜” | pdd-8 + Ref2VA | 人物标签、身份串用；不选 LightX2V |
| “构图认可，提高新镜头清晰度” | pdd-upscale | 新内容符合要求、尺寸、保留音频 |

所有方案仍需完整解码、音画与切口验收；管线测试通过不等于用户这一次内容已经审片。
