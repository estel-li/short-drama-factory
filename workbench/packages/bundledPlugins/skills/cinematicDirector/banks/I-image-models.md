# BANK I · 图片模型路由与提示词写法 —— 图片车道的作业图

> **用法：** 图片车道是外科手术，不是短片。本库按六段给出一张作业图：先认模型（§1），再定写法（§2），再锁身份（§3），再防漂移（§4），再压色板（§5），最后走编辑车道（§6）。
> **模板一律保留英文。** `CHANGE` / `PRESERVE EXACTLY` / 色板封装公式是**直接粘进提示词的字**，中文只做说明；语料里出现的英文例句同样逐字保留。
> **语料依据：** 1954 条提示中 484 条属图片车道（`nano_banana_2` 113、`soul_cinematic` 100、`seedream_v5_pro` 97、`gpt_image_2` 46、`seedream_v4_5` 42、`soul_cinema_studio` 29 …）；源技能 `Lira — Image Prompt Optimization` 共 39 节 / 620 行，本库是它的可执行压缩。
>
> **何时开这个库：** 要写、修、迭代一条图片提示词；要造角色表 / 地点板 / 道具板；要改一张已完成的图；要防插画漂移；要压 60/30/10 色板；要决定这一张该走哪个图片模型。
> **不加载：** 纯视频提示词（走 06 / 07）；没有图片产出的镜头。

---

## 一、模型路由：先认模型，再下笔

> 这一段的顺序是固定的：**先认模型，再写字**。图片车道只认这几个名字：Higgsfield Soul 2.0、Cinema Studio AI Cast、Higgsfield Soul Cinema、Nano Banana Pro（NBP）、Seedream 4.5、GPT Image 2。名字写错、专长用反，后面六段全部作废。

### T-I-01 · 角色走 Soul 2.0：写实角色生成的正位
**为什么：** Soul 2.0 专为写实角色而生（casting 组图、肖像、UGC、时尚编辑大片）；质量 1.5k / 2k，画幅 1:1、16:9、9:16、4:3、3:4、3:2、2:3，参考图 1 张——**没有 21:9**，宽银幕角色帧要改走 Soul Cinema 加 Soul ID。
**失效表现：** 宽银幕角色板硬塞进 Soul 2.0，人物被裁、脸被挤扁；同一角色连着两张板就换了一张脸。
**说：** 角色提示词写成紧凑自然散文，带身份锚点 `the same real person in all three panels` 与照片锚点 `studio photographs`、`film character sheet`、有方向的光。

### T-I-02 · 地点走 Soul Cinema：电影级静帧再加 21:9
**为什么：** Soul Cinema 给电影级静帧、概念图、建立镜头、电影静帧；质量 1.5k / 2k，画幅含 **21:9**（cinemascope 画幅走这里），参考图 1 张，可以把 Soul ID 角色放进电影感场景。它原生就带胶片颗粒与质感，技术块写一行 register 就够。
**失效表现：** 地点板拍出来像平墙纸、没有体积；颗粒词堆到画面发脏；换个机位就换一间房。
**说：** 机位锚点用大白话写死：`high angle three-quarter wide shot, camera high above the room looking diagonally down at 45 degrees`——比 CCTV / 鱼眼这类抽象行话可靠。

### T-I-03 · 角色参考表先问 AI Cast：它自动出表
**为什么：** Cinema Studio AI Cast 会自动构建角色参考图组——Higgsfield 上的独立工具，所有参数在它自己的界面里设，**不需要提示词**；Soul 2.0 里的手动三栏模板只在需要完全控制时才用。
**失效表现：** 明明只要一张参考表，却手写二十行提示词反复重生成；出来的三栏里三张脸各不相同。
**说：** 目标是参考图组时先提供 AI Cast 这条快路径；要逐像素控制排布，再回到手写三栏。

### T-I-04 · 编辑走 NBP：它是编辑车道的第一站，也管道具
**为什么：** Nano Banana Pro（NBP）的职责一是编辑——每一次帧编辑都从它开始，编辑 = 对原始帧的后处理（原图是底，只改最小量）；职责二是道具与产品风格物件。分辨率 1k / 2k / 4k，所有标准画幅 + 21:9 与 4:5 / 5:4，最多 14 张参考图，帧内文字渲染最好。
**失效表现：** 拿 NBP 重画整帧，原图的脸、布局、光全丢；道具上的文字糊成色块。
**说：** 编辑提示第一行写清目标，第二行只写一处 `CHANGE`，其余全部进 `PRESERVE EXACTLY`；要写字就用引号给精确文案 + 字体/字重/颜色：`Write 'GENUINE' in bold red serif on the sign`。

### T-I-05 · 质感只走 Seedream 4.5：它只有这一个职责
**为什么：** Seedream 4.5 唯一的职责是救活成片帧里泥浆感的 AI 质感——皮肤（毛孔）、织物（织纹）、表面（脏污、质感）；basic 最高 4K / high 最高约 6K，支持多参考图。它**做不了点编辑**。
**失效表现：** 让 Seedream 改一处细节，整块表面被重画，脸和构图一起动；或把它当成主编辑模型，越改越脏。
**说：** 提示词里目标写成 `reviving sloppy AI textures`；`CHANGE` 只列表面（皮肤毛孔、织物织纹、地面脏污）；`PRESERVE` 锁住构图、脸、光、调色。

### T-I-06 · 最后手段走 GPT Image 2：整体脏、局部强
**为什么：** GPT Image 2 整帧整体很 "dirty"（会碰整张图），但局部极强；它只接 NBP 接不住的最细局部微编辑，CHANGE 越小结果越干净。分辨率 1k / 2k / 4k，质量 low / medium / high；地点视角更换它在行。
**失效表现：** 用它改一颗纽扣，结果整张图的色调、颗粒、背景全变了。
**说：** 用同一份外科式模板，把 `PRESERVE` 列表写到最大程度的穷尽——模型很乐意重画它不该动的东西。

---

## 二、两套写法：自然散文 vs 关键词堆

> 六个模型都吃**连贯的自然散文**，没有一个吃关键词堆。所谓"两套写法"，第二套不是关键词，而是**编辑车道的结构化块**（`CHANGE` / `PRESERVE EXACTLY`）——它只属于编辑，不属于生成。

### T-I-07 · 生成提示写自然散文，不写关键词堆
**为什么：** 所有模型解析的是连贯流畅的场景描述；关键词堆砌（`4k, masterpiece, trending`）不产生任何控制力。精准的 80–150 词胜过一个散乱的 400 词版本——过了某个点，多出的每个从句都在稀释注意力。
**失效表现：** 结尾堆一串 `8k, masterpiece, best quality`，画面照样糊；字数越多，细节掉得越厉害。
**说：** 把画面写成一个连续场景：谁、在哪、什么光、什么材质、镜头怎么给；形容词只留能落到画面上的。

### T-I-08 · 全大写结构化块只属于编辑提示
**为什么：** 生成提示里出现全大写小节标题，模型会把它当画面内容读；`CHANGE` / `PRESERVE EXACTLY` 这类结构化块是**编辑提示专用**语法，生成提示不用。
**失效表现：** 图片生成提示里分了 `STYLE:` / `LIGHTING:` 几块，图上真的出现大写字样或拼贴色块。
**说：** 生成提示：一整段散文，无小节标题。编辑提示：才允许 `CHANGE` 与 `PRESERVE EXACTLY` 两个块。

---

## 三、角色一致性：Soul ID 承载身份，散文只加固

> 身份不是写出来的，是**平台参数锁出来的**。散文负责加固（同衣橱、同标记、同角度），Soul ID 负责让同一张脸在一次次生成之间不换人；跨镜头一致性以 Soul ID 为准，散文只做加固。

### T-I-09 · 身份锚在 Soul ID 上
**为什么：** Soul ID 是 Soul 2.0 与 Soul Cinema 上的平台一致性参数，承载的是"同一张脸"；散文只能复述同衣橱、同标记、同角度，它不单独承载身份。
**失效表现：** 三张板三个脸；同一个人每张板的痣、发型、脸型都在慢慢漂。
**说：** 先设 Soul ID，再用一句 `the same real person in all three panels` 加固；跨镜一致性以 ID 为准，不以文字描述为准。

### T-I-10 · 三栏面板给多角度证据，衣橱逐栏对齐
**为什么：** 三栏（正面全身 / 背面全身 / 头肩特写）把"同一个人"的多角度证据一次交给模型；衣橱不逐栏对齐，模型会在面板之间自己补细节。
**失效表现：** 只有一张正面照，侧脸和后脑全靠编；三栏之间衣服的领口、口袋、磨损位置各不相同。
**说：** `The same real person in all three, consistent across panels`，衣橱再补一句 `consistent in all panels`；面板之间不许出现新道具。

---

## 四、插画漂移：照片写实请求怎么不跑成插画

> 照片写实跑成插画，九成是**触发词**和**NOT 堆**造成的：`character reference sheet`、`painterly` 会把模型推向概念图；`not cartoon, not anime` 这类否定串恰好把被点名的风格注入画面。修漂移靠**加强正向锚点**。

### T-I-11 · 把两个插画触发词换成照片语言
**为什么：** `character reference sheet` 与 `painterly` 会触发概念图观感；照片写实请求要改用 `studio photographs`、`film character sheet`、`cinematic film still` 这一类照片语言。
**失效表现：** 要照片写实，出来的板却有笔触、边缘发软、像概念设定图；皮肤像上过一层粉。
**说：** 角色表写 `a film character sheet`，不写 `character reference sheet`；写 `studio photographs`，不写 `painterly`。

### T-I-12 · 用正向锚点修漂移，不用 NOT 堆
**为什么：** 漂移是"照片写实证据不足"，不是"禁止得不够"；补胶片型号、镜头、真实材质这些照片写实锚点，比加一长串否定有效。
**失效表现：** `not cartoon, not anime` 写得越长，画面越像插画——被点名的风格反而被注入。
**说：** 加 `ARRI Alexa LF anamorphic Cooke S4 lens at T2.0`＋真实材质名（`board-formed concrete`、`oxidized copper verdigris`），不加 NOT 串。

---

## 五、色板控制与色板封装：60 / 30 / 10

> 色板是**可核对的数字**，不是情绪词。所有模型都读百分比；分配从用户指令、场景语境、上传参考里推导，不凭空发明。

### T-I-13 · 用 60 / 30 / 10 写色板，色相用词写实
**为什么：** 百分比在所有模型上都读得准，60/30/10 给的是"主色—辅色—点缀"的层级；色相要写真实颜色名（`warm ochre`、`deep charcoal`、`rust-red`），不写 `moody`、`cinematic colours` 这类空词。
**失效表现：** 两张板色调不一致；或把参考图的颜色压掉，换成自己发明的一套配色。
**说：** `palette of 60% warm ochre, 30% deep charcoal, 10% rust-red`；分配从用户指令 / 场景语境 / 上传参考里来。

### T-I-14 · 需要统一调色时套"色板封装"公式
**为什么：** 同一项目多张板要共享一套调色时，用一条封装公式一次写死主色、唯一暖对比、黑位、对比与明暗结构，比每张板各写一套更稳。
**失效表现：** 角色板和地点板各有一套调色，剪在一起像两个项目；或照片写实角色板套了绘画感封装，皮肤出了笔触。
**说：** 模板本体保留英文，直接粘贴：
```text
Refined desaturated [painterly] palette: [cool/dominant tones] dominating,
[warm element] as the only warm contrast, deep crushed blacks, restrained
naturalistic grading, soft low contrast, strong cinematic chiaroscuro
```
照片写实角色作品把方括号里的 `[painterly]` 去掉；只有**有意做成绘画感**的环境板才保留。

---

## 六、编辑车道：外科式修图、点编辑、质感通道

> 编辑车道的顺序是固定的：**NBP 第一 → Seedream 4.5 只做质感 → GPT Image 2 最后手段**。编辑是"改一处 + 钉住其余"，不是重写；需要重建整帧时不叫编辑，回 Soul 系重新生成。

### T-I-15 · 外科式模板：最小 CHANGE + 穷尽 PRESERVE
**为什么：** 编辑不是重写，是"改一处 + 钉住其余"；把不变的东西逐条列出来，模型才没有自由发挥的空间。模板本体保留英文，逐字粘贴：
**失效表现：** 只写"把外套换成黑色"，结果背景、光、构图、脸全被重画。
**说：**
```text
Edit the image: [one-line goal].

CHANGE: [only the single thing that changes, described precisely].

PRESERVE EXACTLY:
- [list every element that must stay identical: face, clothing, props,
  positions, wall/floor, camera angle, all existing shadows]
- Color grade, palette, contrast, grain, falloff

ONLY CHANGE: [restate the one change]. 100% identical otherwise.
```

### T-I-16 · 一次只改一处，PRESERVE 逐字保留
**为什么：** 每多一个变更，`PRESERVE` 清单就多一处漏洞；一个主题可以拆成编号子项，但不能一遍里换装又改脸又换背景。收尾的 `ONLY CHANGE` 与 `100% identical otherwise` 是给模型的最后一道闸。
**失效表现：** 一遍改完客户说"太过了"——不是改错，是改太多；`PRESERVE` 里列到的背景仍被重画。
**说：** 模板本体保留英文，逐字粘贴：`CHANGE: [the single thing]` → `PRESERVE EXACTLY: [list every element]` → `ONLY CHANGE: [restate the one change]. 100% identical otherwise.`

### T-I-17 · 点编辑与质感通道分工：NBP → GPT 最后手段，质感只给 Seedream
**为什么：** 点编辑（改一处细节）走 NBP；NBP 接不住的最细局部才给 GPT Image 2（最后手段，CHANGE 越小越干净）；质感泥浆只给 Seedream 4.5（它只有这一个职责）；要重建整帧就回 Soul 系重新生成，不拿编辑硬修。
**失效表现：** 用 Seedream 做点编辑，整块表面被重画；或用编辑去重建一帧，脸和布局全变。
**说：** 点编辑：NBP → GPT Image 2；质感：Seedream 4.5；重建：Soul 系重新生成。

### T-I-18 · 地点视角更换：GPT 默认，NBP 要逐物写新排布
**为什么：** 反打 / 换机位时，模型不知道物体该翻到哪边；GPT Image 2 处理地点视角更换很好，是默认路由；用 NBP 就必须把镜像后的新排布逐件写死。
**失效表现：** 反打之后沙发跑到同一边、门消失、左右墙互换——几何被搅乱。
**说：** 用 NBP 时逐物件写：`In the main view the sofa is on the right; in this reverse view the sofa is on the LEFT, the doorway behind the camera is now visible ahead`。

---

## 自检（本库相关）

- [ ] 模型按路由认过：角色 → Soul 2.0；地点 → Soul Cinema；参考图组 → 先问 AI Cast；编辑 → NBP 第一；质感 → 仅 Seedream 4.5；最后手段 → GPT Image 2
- [ ] 宽银幕角色帧没有硬塞进 Soul 2.0（21:9 走 Soul Cinema + Soul ID）
- [ ] 生成提示是自然散文，没有关键词堆，没有全大写小节标题
- [ ] `CHANGE` / `PRESERVE EXACTLY` 只出现在编辑提示里
- [ ] 角色一致性挂在 Soul ID 上，散文只做加固；三栏有身份锚点与逐栏衣橱对齐
- [ ] 照片写实提示没有 `character reference sheet` / `painterly`，插画漂移用正向锚点修
- [ ] 色板写成 60 / 30 / 10 的真实色相；需要统一调色时套了色板封装，照片写实去掉了 `[painterly]`
- [ ] 编辑一次只改一处；`PRESERVE` 逐项列全；收尾有 `ONLY CHANGE` 与 `100% identical otherwise`
- [ ] 点编辑与质感通道没有串线（Seedream 只做质感，重建回 Soul 系）
- [ ] 地点视角更换走 GPT Image 2，或 NBP 已逐物件写清镜像后的新排布
