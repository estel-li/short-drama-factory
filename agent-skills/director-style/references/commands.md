# 导演风格命令与恢复

以下用 sdf 表示应用中的 `agent-skills/short-drama-factory/scripts/sdf.py`。已独立安装本技能时也可用 `python scripts/director.py --app 应用目录 --` 加同样的参数。

```powershell
python sdf.py style prepare --video "D:/reference/film.mp4" --start 0 --end 90 --wait 45
python sdf.py job watch JOB_ID --seconds 45
python sdf.py style analysis ANALYSIS_ID
python sdf.py style clip ANALYSIS_ID --start 18 --end 24 --wait 45
python sdf.py style publish --json authored-style.json --request-key learn-film-v1
python sdf.py style list
python sdf.py style show --style STYLE_ID --version VERSION
python sdf.py style brief --style STYLE_ID --version VERSION
python sdf.py style bind --project PID --style STYLE_ID --version VERSION
python sdf.py style brief --project PID
python sdf.py style check --project PID
python sdf.py style review --project PID --json review.json
python sdf.py style install --style STYLE_ID --version VERSION --target "新的 AI 技能目录"
python sdf.py style import --folder "收到的完整导演风格包目录"
```

prepare 会先计算本机参考文件 SHA256，后台核对同一文件后提取。路径须在服务所在机器可读；不把远端机器路径假装本地上传。支持 mp4/mov/mkv/webm/avi 及常见音频，单片最多4小时；提取范围可指定 start/end。max-frames 默认240、上限1200；max-clips 默认8、上限24；sample-seconds 默认3，长片会按总帧数上限调整。

analysis 默认返回紧凑查看入口；--full 返回完整抽帧、切点与音频测量。连续片段 start/end 使用原片绝对秒数，单次最多60秒；同时保留原片时间对应关系。提取是 CPU 处理，不调用生成引擎。

发布 JSON 结构见 [样例](../assets/style-example.json)。style_id 使用小写字母开头的小写字母/数字/短横线，最多40字节；初次 expected_version 为 null，已有风格更新必须提交当前 expected_version。新规则生成新的内容版本，旧版本仍可读取。

写操作支持 --request-key 和本地 .sdf 请求账本。超时先 `operation get KEY`，有原账本时 `operation retry KEY`，不能重新创建身份不明的分析。job stop/resume 操作原任务；停止仅取消该任务。发布或绑定回执丢失可用相同键恢复，不重复覆盖已更新版本。

用户风格库在服务的用户目录中。install 的目标也指服务机器上的目录，必须尚不存在；更新时选择新的目录，保留原安装和个人修改。安装后可单独读取 SKILL.md 和随包证据，不依赖原片仍在旧位置。

跨机器收到完整风格包时先 style import，再按返回的 id/version 绑定项目；不需要原分析目录或原片。CLI 记录清单 SHA256，导入会逐文件校验，拒绝变化中的包；已有其他当前版本时需 --expected-version，避免覆盖并发更新。同一完整版本可重复导入。

HTTP 对应 `/api/v2/director/analyses`、`/api/v2/director/styles` 以及 `/api/v2/projects/{pid}/director-style`，具体类型以实例 /openapi.json 为准。引用文件只通过分析清单的 files 路径读取，不提供任意本地文件下载。
