import { el, field, select } from "./api.js?v=3.6.6";
import {videoWorkflowControls} from "./video-workflows.js?v=3.6.6";

const DEFAULTS = {
  duration_rule: "total",
  total_seconds: 24,
  shot_seconds: 4,
  shot_count: 6,
  style: "温暖的二维动漫短剧",
  genre: "治愈",
  ratio: "9:16",
  profile: "draft",
  seed: 12345,
  auto_reference: true,
  subtitles: true,
  h3_mode: "auto",
  missing_reference: "error",
  dialogue_language: "Chinese",
  narration: false,
  music: "N/A",
  manual_durations: [],
  render_retries: 1,
  dialogue_timing: "fit",
  speech_rate: 5.6,
  speech_lead: 0.4,
  speech_gap: 0.3,
  speech_tail: 0.55,
  edit_preset: "gentle",
  subtitle_alignment: "speech",
  review_stages: ["outline", "storyboard", "prompt"],
  stages: {
    outline: { provider: "deepseek", model: "", skill: "outline-hook" },
    storyboard: { provider: "deepseek", model: "", skill: "storyboard-fast" },
    prompt: { provider: "deepseek", model: "", skill: "h3-t2va" },
  },
};
const MODES = [
  { value: "auto", label: "自动选择（推荐）" },
  { value: "T2VA", label: "T2VA · 文字生成" },
  { value: "I2VA", label: "I2VA · 首帧生成" },
  { value: "FL2VA", label: "FL2VA · 首尾帧生成" },
  { value: "L2VA", label: "L2VA · 尾帧生成" },
  { value: "Ref2VA", label: "Ref2VA · 多模态参考" },
];
export { MODES };

export function optionsEditor(
  container,
  config,
  presets,
  skills,
  current = {},
  onchange = () => {},
) {
  container.replaceChildren();
  const values = { ...structuredClone(DEFAULTS), ...current };
  const controls = {},
    stageControls = {},
    reviews = {},
    wrappers = {};
  const input = (name, type = "text", props = {}) =>
    (controls[name] = el("input", {
      type,
      value: values[name] ?? "",
      ...props,
    }));
  const dropdown = (name, items) =>
    (controls[name] = select(items, values[name]));
  function choice(name, items, label, type = "text") {
    const editor = input(name, type, { "aria-label": `${label} · 自定义值` });
    const match = items.some((value) => String(value) === String(values[name]));
    const pick = select(
      [
        ...items.map((value) => ({
          value: String(value),
          label: String(value),
        })),
        { value: "__custom", label: "自定义…" },
      ],
      match ? String(values[name]) : "__custom",
    );
    pick.setAttribute("aria-label", label);
    editor.hidden = match;
    editor.placeholder = "填写自定义值";
    pick.addEventListener("change", () => {
      editor.hidden = pick.value !== "__custom";
      if (pick.value !== "__custom") editor.value = pick.value;
      else editor.focus();
    });
    return el("div", { class: "choice" }, pick, editor);
  }
  const section = (title, hint, ...children) =>
    el(
      "fieldset",
      { class: "option-section" },
      el("legend", {}, title),
      el("p", { class: "section-help" }, hint),
      ...children,
    );
  const style = section(
    "画面与故事",
    "先确定整体感觉，各分镜会沿用这些设置。",
    el(
      "div",
      { class: "grid three" },
      field("视觉风格", choice("style", presets.styles, "视觉风格")),
      field("故事题材", choice("genre", presets.genres, "故事题材")),
      field("画面比例", choice("ratio", presets.ratios, "画面比例")),
    ),
  );
  const rule = dropdown("duration_rule", [
    { value: "total", label: "按总时长分配" },
    { value: "count", label: "固定镜头数量" },
    { value: "manual", label: "逐镜指定时长" },
  ]);
  const durationGrid = el(
    "div",
    { class: "grid three" },
    field("分镜安排", rule),
  );
  for (const [name, label, items] of [
    ["total_seconds", "目标总时长（秒）", presets.total_seconds],
    ["shot_count", "镜头数量", presets.shot_counts],
    ["shot_seconds", "每镜头目标（秒）", [4, 5, 6, 7, 8]],
  ]) {
    wrappers[name] = field(label, choice(name, items, label, "number"));
    durationGrid.append(wrappers[name]);
    Object.assign(controls[name], {
      min: name === "shot_count" ? 1 : 4,
      max: name === "shot_count" ? 150 : name === "total_seconds" ? 600 : 15,
      step: name === "shot_count" ? 1 : 0.1,
    });
  }
  wrappers.manual_durations = field(
    "各镜头时长（秒）",
    input("manual_durations", "text", { placeholder: "例如：4, 6, 4" }),
    "以逗号分隔，每镜头默认 4～8 秒。",
  );
  controls.manual_durations.value = values.manual_durations.join(", ");
  durationGrid.append(wrappers.manual_durations);
  durationGrid.append(
    field(
      "视频工作流 / 质量",
      dropdown(
        "profile",
        Object.entries(config.profiles).map(([value, p]) => ({
          value,
          label: p.label,
        })),
      ),
      "建议先用快速预览确认分镜，再提高质量。",
    ),
  );
  durationGrid.append(videoWorkflowControls(config,controls.profile,()=>controls.profile.dispatchEvent(new Event("input",{bubbles:true}))));
  function durationVisibility() {
    wrappers.total_seconds.hidden = rule.value === "manual";
    wrappers.shot_count.hidden = rule.value !== "count";
    wrappers.shot_seconds.hidden = rule.value !== "total";
    wrappers.manual_durations.hidden = rule.value !== "manual";
  }
  rule.addEventListener("change", durationVisibility);
  durationVisibility();
  container.append(
    style,
    section(
      "时长与分镜",
      "实际视频按 H3 帧数规则对齐；下方预览会显示最终长度。",
      durationGrid,
    ),
  );
  container.append(
    section(
      "对白与节奏",
      "对白拟合会按实际台词调整新分镜的镜长（4～8 秒）；没有对白的动作镜头沿用原计划。手动指定镜长始终优先，总时长为规划目标。",
      el(
        "div",
        { class: "grid three" },
        field(
          "镜长策略",
          dropdown("dialogue_timing", [
            { value: "fit", label: "按对白预算拟合（推荐）" },
            { value: "fixed", label: "保持时长分配，检查对白能否说完" },
          ]),
        ),
        field(
          "目标语速（字 / 秒）",
          input("speech_rate", "number", { min: 1, max: 12, step: 0.1 }),
          "默认 5.6；这是预算，实际人声会在成片质检中测量。",
        ),
        field(
          "起手留白（秒）",
          input("speech_lead", "number", { min: 0, max: 2, step: 0.05 }),
        ),
        field(
          "句间停顿（秒）",
          input("speech_gap", "number", { min: 0, max: 2, step: 0.05 }),
        ),
        field(
          "收尾留白（秒）",
          input("speech_tail", "number", { min: 0, max: 2, step: 0.05 }),
        ),
        field(
          "生成后的剪辑",
          dropdown("edit_preset", [
            { value: "original", label: "保留原始节奏" },
            { value: "gentle", label: "保守收紧（推荐）" },
            { value: "compact", label: "紧凑剪辑" },
          ]),
        ),
        field(
          "字幕对齐",
          dropdown("subtitle_alignment", [
            { value: "speech", label: "跟随检测人声（推荐）" },
            { value: "approximate", label: "按字数与镜长近似分配" },
          ]),
        ),
      ),
    ),
  );
  const stageBox = el(
    "details",
    { class: "option-section" },
    el(
      "summary",
      {},
      "文字模型与创作规则",
      el("small", { class: "muted" }, "大纲 / 分镜 / 提示词可分别配置"),
    ),
  );
  stageBox.append(
    el(
      "p",
      { class: "section-help" },
      "默认使用提供商的模型。切换提供商后，模型名可留空，或填写该服务的真实名称。",
    ),
  );
  for (const [name, label] of [
    ["outline", "大纲策划"],
    ["storyboard", "AI 分镜"],
    ["prompt", "H3 提示词"],
  ]) {
    const value = values.stages[name] || {},
      provider = select(
        config.providers.map((p) => ({ value: p.id, label: p.name })),
        value.provider || config.providers[0]?.id,
      );
    const model = el("input", {
        value: value.model || "",
        placeholder: "使用提供商默认模型",
      }),
      skill = select(
        skills
          .filter((s) => s.stage === name)
          .map((s) => ({ value: s.id, label: s.name })),
        value.skill,
      );
    stageControls[name] = { provider, model, skill };
    stageBox.append(
      el(
        "div",
        { class: "stage-row" },
        el("strong", {}, label),
        el(
          "div",
          { class: "grid three" },
          field(label + " · 提供商", provider),
          field(label + " · 模型名称", model),
          field(label + " · Skill", skill),
        ),
      ),
    );
  }
  const advanced = el(
    "details",
    { class: "option-section" },
    el("summary", {}, "声音、生成模式与高级设置"),
  );
  advanced.append(
    el(
      "div",
      { class: "grid three" },
      field("对白语言", input("dialogue_language")),
      field("配乐方向", input("music"), "N/A 表示不指定额外配乐。"),
      field("默认 H3 模式", dropdown("h3_mode", MODES)),
      field(
        "参考素材缺失时",
        dropdown("missing_reference", [
          { value: "error", label: "暂停并提示补齐" },
          { value: "text", label: "允许退回文字生成" },
        ]),
      ),
      field("随机种子", input("seed", "number", { min: 0, step: 1 })),
      field(
        "视频生成额外重试",
        input("render_retries", "number", { min: 0, max: 2, step: 1 }),
        "文字请求重试在提供商设置中配置。",
      ),
    ),
  );
  const switches = el("div", { class: "switch-grid" });
  for (const [name, label, help] of [
    [
      "auto_reference",
      "自动角色参考",
      "从单角色镜头提取身份图，帮助保持外观。",
    ],
    ["subtitles", "字幕版成片", "同时保留无字幕成片和 SRT。"],
    ["narration", "采用画外旁白", "将旁白方向传给提示词模型。"],
    ["allow_long_shots", "开放 8～15 秒镜头", "更占显存，需在目标电脑验证。"],
  ]) {
    const item = (controls[name] = el("input", {
      type: "checkbox",
      checked: !!values[name],
    }));
    switches.append(
      el(
        "label",
        { class: "switch-card" },
        item,
        el("span", {}, el("strong", {}, label), el("small", {}, help)),
      ),
    );
  }
  advanced.append(
    switches,
    el("h3", {}, "逐阶段检查时的暂停位置"),
    el(
      "div",
      { class: "check-row" },
      ["outline", "storyboard", "prompt"].map((name, i) => {
        const check = (reviews[name] = el("input", {
          type: "checkbox",
          checked: values.review_stages.includes(name),
        }));
        return el(
          "label",
          { class: "check" },
          check,
          ["大纲完成", "分镜完成", "提示词完成"][i],
        );
      }),
    ),
  );
  const referenceValues = { enabled: false, characters: true, scenes: true, props: false, optimize: true,
    variant: "auto", resolution: "auto", provider: "", model: "", ...(values.reference_images || {}) };
  const referenceControls = {};
  const referenceBox = section("用本地模型生成参考图", "启用后，分镜流程会先用所选模型生成角色与场景图片，再编写视频提示词；文字规划也会包含这一步。已有手动人物图优先保留。");
  referenceControls.image_model = select(Object.entries(config.image_models || { "qwen-image-2.1": { name: "Qwen-Image 2.1" } }).map(([value, spec]) => ({ value, label: spec.name })), referenceValues.image_model || "qwen-image-2.1");
  for (const [key, label] of [["enabled", "自动生成项目参考图"], ["characters", "角色身份图"], ["scenes", "场景图"], ["props", "道具图"], ["optimize", "优化图片提示词"]]) {
    const input = referenceControls[key] = el("input", { type: "checkbox", checked: referenceValues[key] });
    referenceBox.append(el("label", { class: "image-switch" }, input, label));
  }
  referenceControls.variant = select([{ value: "auto", label: "按显存自动选择" }, { value: "turbo-int8", label: "Turbo INT8" }, { value: "turbo-bf16", label: "Turbo BF16" }, { value: "quality-int8", label: "标准 INT8" }], referenceValues.variant);
  referenceControls.resolution = select(["auto", "512", "768", "1024", "1536", "2048"].map(value => ({ value, label: value === "auto" ? "按显存自动选择" : value + " 档" })), referenceValues.resolution);
  referenceControls.provider = select([{ value: "", label: "使用图片工作室默认提供商" }, ...config.providers.map(p => ({ value: p.id, label: p.name }))], referenceValues.provider);
  referenceControls.model = el("input", { value: referenceValues.model, placeholder: "留空继承提供商模型" });
  referenceBox.append(el("div", { class: "grid" }, field("生图模型", referenceControls.image_model), field("Qwen 精度方案", referenceControls.variant), field("图片大小", referenceControls.resolution), field("提示词优化提供商", referenceControls.provider), field("优化文字模型", referenceControls.model)),
    el("p", { class: "field-help" }, "生图在本地运行；Qwen-Image 2.1 使用非商用研究许可，商业用途需要模型方授权。"));
  container.append(stageBox, referenceBox, advanced);
  function read() {
    const result = { ...values };
    for (const [name, control] of Object.entries(controls))
      result[name] =
        control.type === "checkbox"
          ? control.checked
          : [
                "total_seconds",
                "shot_seconds",
                "shot_count",
                "seed",
                "render_retries",
                "speech_rate",
                "speech_lead",
                "speech_gap",
                "speech_tail",
              ].includes(name)
            ? Number(control.value)
            : name === "manual_durations"
              ? control.value
                  .split(/[,，]/)
                  .filter((v) => v.trim())
                  .map(Number)
              : control.value;
    result.stages = {};
    for (const [name, row] of Object.entries(stageControls))
      result.stages[name] = {
        provider: row.provider.value,
        model: row.model.value.trim(),
        skill: row.skill.value,
      };
    result.review_stages = Object.keys(reviews).filter(
      (key) => reviews[key].checked,
    );
    result.reference_images = { ...referenceValues, ...Object.fromEntries(Object.entries(referenceControls).map(([key, node]) => [key, node.type === "checkbox" ? node.checked : node.value.trim()])) };
    return result;
  }
  container.oninput = () => onchange(read());
  container.onchange = () => onchange(read());
  return read;
}
