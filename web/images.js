import { api, el, field, select } from "./api.js?v=2.5.0";
import { badge, icon } from "./ui.js?v=2.5.0";

const kinds = { general: "自由创作", character: "角色参考", scene: "场景参考", prop: "道具参考" };
const variants = [{ value: "auto", label: "根据显存自动选择" }, { value: "turbo-int8", label: "Turbo INT8 · 快速预览" }, { value: "turbo-bf16", label: "Turbo BF16 · 大显存" }, { value: "quality-int8", label: "标准 INT8 · 细节优先" }];
const resolutions = ["auto", "512", "768", "1024", "1536", "2048"].map(value => ({ value, label: value === "auto" ? "根据显存自动选择" : `${value} 档（按比例换算）` }));
const bytes = value => `${(value / 1024 ** 3).toFixed(1)} GB`;

export class ImageWorkspace {
  constructor(container, services) {
    this.container = container;
    this.services = services;
    this.dirty = false;
    this.revision = 0;
    this.mounted = false;
    this.pendingOptimize = null;
  }
  button(text, work, props = {}) {
    return el("button", { onclick: event => this.services.act(work, event.currentTarget), ...props }, text);
  }
  mount() {
    if (this.mounted) return;
    this.mounted = true;
    const settings = this.services.config().image_generation || {};
    this.settings = settings;
    this.controls = {
      prompt: el("textarea", { rows: 6, maxLength: 12000, placeholder: "例如：雨后的小巷，暖黄色窗灯，一把蓝色旧伞，温暖手绘动漫风格……", required: true }),
      optimize: el("input", { type: "checkbox", checked: true }),
      optimized_prompt: el("textarea", { rows: 5, maxLength: 20000, placeholder: "可先优化查看结果，也可直接生成。填写后将使用这里的内容。" }),
      purpose: select(Object.entries(kinds).map(([value, label]) => ({ value, label })), "general"),
      ratio: select(["1:1", "3:4", "4:3", "9:16", "16:9", "2:3", "3:2"], "1:1"),
      resolution: select(resolutions, "auto"), variant: select(variants, "auto"),
      seed: el("input", { type: "number", min: 0, step: 1, placeholder: "留空随机" }),
      style: el("input", { maxLength: 3000, placeholder: "例如：二维动漫、写实摄影、水彩绘本" }),
      transparent: el("input", { type: "checkbox" }),
      provider: select(this.services.config().providers.map(p => ({ value: p.id, label: p.name })), settings.provider || "deepseek"),
      model: el("input", { value: settings.model || "", placeholder: "留空沿用提供商模型" }),
      skill: select([{ value: "", label: "根据用途选择 Skill" }, ...this.services.skills().filter(s => s.stage === "image_prompt").map(s => ({ value: s.id, label: s.name }))], ""),
    };
    const c = this.controls;
    const form = el("div", { class: "card image-prompt-card" },
      el("h2", {}, "描述你想看到的画面"), field("自然语言描述", c.prompt),
      el("div", { class: "grid three" }, field("用途", c.purpose), field("画幅", c.ratio), field("风格", c.style)),
      el("label", { class: "image-switch" }, c.optimize, el("span", {}, "优化提示词", el("small", {}, "默认开启；保留原意，补充构图、光影和可辨识细节。"))),
      field("优化后的提示词（可编辑）", c.optimized_prompt),
      el("details", { class: "option-section" }, el("summary", {}, "模型、清晰度与优化设置"),
        el("div", { class: "grid three" }, field("图片模型", c.variant), field("图片大小", c.resolution), field("随机种子", c.seed),
          field("文字提供商", c.provider), field("文字模型", c.model), field("优化 Skill", c.skill)),
        el("label", { class: "image-switch" }, c.transparent, "请求透明背景 PNG"),
        this.button("保存为图片默认设置", async () => {
          this.settings = await api("/api/images/settings", { ...this.settings, variant: c.variant.value, provider: c.provider.value,
            model: c.model.value.trim(), skill: c.skill.value || "image-qwen-general" });
          await this.services.reloadConfig(); this.services.toast("图片模型和优化提供商默认设置已保存。");
        })),
      el("div", { class: "actions" }, this.button("先优化提示词", () => this.submit(true)),
        this.button("生成图片", () => this.submit(false), { class: "primary" })),
      el("p", { class: "field-help" }, "图片在本地 ComfyUI 生成。勾选优化时，文字会发送到所选文字提供商；也可选本地模型。"));
    for (const [name, control] of Object.entries(c)) control.addEventListener("input", () => {
      this.dirty = true; this.revision++;
      if (["prompt", "purpose", "style", "ratio"].includes(name)) c.optimized_prompt.value = "";
      c.optimized_prompt.disabled = !c.optimize.checked;
    });
    c.variant.addEventListener("change", () => this.services.act(() => this.refreshEnvironment()));
    this.environmentBox = el("div", { class: "card image-environment" });
    this.progressBox = el("div", { class: "notice", hidden: true, role: "status" });
    this.gallery = el("div", { class: "image-gallery" });
    this.container.replaceChildren(el("div", { class: "image-studio-layout" }, form, this.environmentBox), this.progressBox,
      el("div", { class: "section-toolbar" }, el("h2", {}, "图片历史 · 最近 200 张"), this.button("刷新", () => this.refresh())), this.gallery);
    this.services.act(() => this.refreshEnvironment());
    this.services.act(() => this.refresh());
  }
  read() {
    const values = Object.fromEntries(Object.entries(this.controls).map(([name, c]) => [name, c.type === "checkbox" ? c.checked : c.value.trim()]));
    if (!values.prompt) throw Error("请先写下想生成的画面。");
    values.seed = values.seed === "" ? null : Number(values.seed);
    if (values.seed !== null && (!Number.isSafeInteger(values.seed) || values.seed < 0)) throw Error("随机种子请输入非负安全整数，或留空。");
    if (!values.optimize) values.optimized_prompt = "";
    return values;
  }
  async submit(optimizeOnly) {
    const request = this.read();
    if (optimizeOnly) { request.optimize = true; request.optimized_prompt = ""; }
    const result = await api("/api/images", { request, optimize_only: optimizeOnly });
    if (optimizeOnly) this.pendingOptimize = { id: result.id, revision: this.revision };
    this.dirty = false;
    this.services.toast(optimizeOnly ? "优化任务已排队，完成后会显示可编辑提示词。" : "图片已排队，准备模型和生成进度会保留。");
    await this.refresh();
  }
  load(record) {
    for (const [name, control] of Object.entries(this.controls)) {
      const value = name === "optimized_prompt" ? record.optimized_prompt || record.request.optimized_prompt || "" : record.request[name];
      if (control.type === "checkbox") control.checked = !!value;
      else control.value = value ?? "";
    }
    this.controls.optimized_prompt.disabled = !this.controls.optimize.checked;
    this.dirty = true; this.revision++;
    this.controls.prompt.focus();
    this.services.toast("参数已载入，可以编辑提示词后再生成。");
  }
  async refreshEnvironment() {
    const version = this.environmentRevision = (this.environmentRevision || 0) + 1;
    this.environmentBox.replaceChildren(el("p", {}, "正在检测图片引擎与目标显卡……"));
    const plan = await api("/api/images/environment?variant=" + encodeURIComponent(this.controls.variant.value));
    if (version !== this.environmentRevision) return;
    this.plan = plan;
    const s = this.engineDraft || this.settings;
    const engine = select([{ value: "auto", label: "自动选择兼容引擎" }, { value: "shared", label: "复用指定 ComfyUI" }, { value: "managed", label: "独立图片引擎" }], s.engine || "auto");
    const url = el("input", { value: s.comfy_url || "", placeholder: "留空使用视频引擎地址" });
    const directory = el("input", { value: s.models_dir || "", placeholder: "留空使用推荐目录" });
    const port = el("input", { type: "number", min: 1024, max: 65535, value: s.managed_port || 8190 });
    const auto = el("input", { type: "checkbox", checked: s.auto_download !== false });
    for (const control of [engine, url, directory, port, auto]) control.addEventListener("input", () => {
      this.engineDraft = { ...s, engine: engine.value, comfy_url: url.value, models_dir: directory.value, managed_port: Number(port.value), auto_download: auto.checked };
      this.dirty = true;
    });
    this.environmentBox.replaceChildren(el("h2", {}, "图片生成环境"), el("span", { class: "badge " + (plan.ready ? "success" : "warning") }, plan.ready ? "环境就绪" : "需要准备"),
      el("p", {}, plan.gpu?.name?.replace(/^cuda:\d+\s*:?\s*/, "").replace(/\s*:\s*cudaMallocAsync.*$/, "") || "显卡信息暂不可用", plan.vram_mb ? ` · ${(plan.vram_mb / 1024).toFixed(1)} GB` : ""),
      el("p", { class: "muted" }, plan.recommendation.message),
      el("p", {}, `本次方案：${plan.variants[plan.variant].name}`),
      el("p", {}, plan.engine === "managed" ? "使用独立图片引擎" : "复用已有 ComfyUI"),
      el("p", {}, `待下载 ${bytes(plan.download_bytes)} · 磁盘剩余 ${bytes(plan.free_disk_bytes)}`),
      plan.bootstrap_needed ? el("p", { class: "muted" }, `首次还会准备独立 GPU 运行时（下载 ${bytes(plan.runtime_download_bytes)}，另需解压空间）。`) : null,
      el("ul", { class: "model-download-list" }, plan.models.map(m => el("li", {}, `${m.action === "available" ? "已识别" : m.action === "verify" ? "待校验" : "需下载"} · ${m.name} · ${bytes(m.size)}`))),
      el("p", { class: "notice warning" }, plan.license.notice, " ", el("a", { href: plan.license.url, target: "_blank", rel: "noopener noreferrer" }, "模型许可")),
      el("div", { class: "actions" }, this.button("检查环境", () => this.refreshEnvironment()),
        this.button("准备 / 继续下载", async () => { await api("/api/images/environment/prepare", { variant: this.controls.variant.value }); this.services.toast("环境准备已排队。"); await this.refresh(); }),
        this.button("停止准备", async () => { await api("/api/images/environment/stop", {}); await this.refresh(); })),
      el("details", { class: "option-section" }, el("summary", {}, "图片引擎设置"), field("引擎方式", engine), field("已有服务地址", url), field("模型存放目录", directory), field("独立引擎端口", port),
        el("label", { class: "image-switch" }, auto, "生成时自动准备缺少的模型和引擎"),
        this.button("保存引擎设置", async () => {
          this.settings = await api("/api/images/settings", { ...s, engine: engine.value, comfy_url: url.value.trim(), models_dir: directory.value.trim(), managed_port: Number(port.value), auto_download: auto.checked });
          this.engineDraft = null;
          await this.services.reloadConfig(); await this.refreshEnvironment();
          this.services.toast("图片引擎设置已保存。");
        })));
  }
  async refresh() {
    if (!this.mounted || this.refreshing) return;
    this.refreshing = true;
    try {
      const [records, progress] = await Promise.all([api("/api/images"), api("/api/images/environment/progress")]);
      this.progressBox.hidden = !progress.status;
      this.progressBox.replaceChildren(el("p", {}, progress.message || ""));
      if (progress.progress?.total) this.progressBox.append(el("progress", { max: progress.progress.total, value: progress.progress.bytes || 0 }));
      if (progress.status === "done" && this.lastEnvironmentStatus !== "done") this.services.act(() => this.refreshEnvironment());
      this.lastEnvironmentStatus = progress.status;
      const pending = this.pendingOptimize && records.find(r => r.id === this.pendingOptimize.id);
      if (pending?.status === "ready") {
        if (this.revision === this.pendingOptimize.revision) { this.controls.optimized_prompt.value = pending.optimized_prompt; this.dirty = true; }
        this.pendingOptimize = null;
      }
      const stamp = JSON.stringify(records);
      if (stamp === this.galleryStamp) return;
      this.galleryStamp = stamp;
      this.gallery.replaceChildren(...records.map(record => this.card(record)));
      if (!records.length) this.gallery.append(el("div", { class: "empty" }, icon("image"), el("h3", {}, "第一张画面，从一句话开始"), el("p", {}, "生成的图片、提示词和种子会一起保留。")));
    } finally { this.refreshing = false; }
  }
  card(record) {
    const status = record.busy && ["new", "ready", "paused"].includes(record.status) ? "queued" : record.status;
    const row = el("article", { class: "card image-result" },
      record.url ? el("a", { href: record.url, target: "_blank", rel: "noopener" }, el("img", { src: record.url, alt: record.request.prompt, loading: "lazy" })) : el("div", { class: "image-placeholder" }, icon("image"), badge(status)),
      el("div", { class: "image-result-body" }, badge(status), el("p", { class: "image-caption" }, record.request.prompt), el("small", {}, record.message),
        el("p", { class: "muted" }, `${kinds[record.request.purpose]} · ${record.width || "—"} × ${record.height || "—"} · 种子 ${record.request.seed}`),
        record.model_plan?.variant ? el("small", {}, record.model_plan.variants?.[record.model_plan.variant]?.name || record.model_plan.variant) : null));
    const actions = el("div", { class: "actions" }, this.button("载入参数", () => this.load(record)));
    if (record.url) actions.append(el("a", { class: "button", href: record.url, download: `${record.id}.png` }, "下载 PNG"));
    if (record.busy) actions.append(this.button("停止", async () => { await api(`/api/images/${record.id}/stop`, {}); await this.refresh(); }));
    else {
      actions.append(this.button(record.url ? "重新生成" : "新种子重试", async () => { await api(`/api/images/${record.id}/regenerate`, {}); await this.refresh(); }, { disabled: record.project_busy }));
      if (!record.url) actions.append(this.button("继续原任务", async () => { await api(`/api/images/${record.id}/resume`, {}); await this.refresh(); }, { disabled: record.project_busy }));
    }
    row.append(actions);
    if (record.url && record.request.transparent && !record.has_transparency) row.append(el("p", { class: "notice warning" }, "本次未生成透明区域，可调整描述后重试。"));
    if (record.optimized_prompt || record.effective_prompt) row.append(el("details", {}, el("summary", {}, "查看生成提示词"), el("p", { class: "prompt-text" }, record.optimized_prompt || record.effective_prompt)));
    return row;
  }
}

export async function renderReferenceImages(workspace, box) {
  const pid = workspace.current.id;
  const block = el("section", { class: "reference-studio" }, el("h2", {}, "用 Qwen 生成项目参考图"),
    el("p", { class: "muted" }, "角色图用于身份一致性，场景图用于空间一致性。生成并采用后，会更新对应分镜；旧图和历史版本保留。"));
  box.prepend(block);
  const data = await api(`/api/projects/${pid}/image-references`);
  if (!block.isConnected || workspace.current.id !== pid) return;
  const blocked = workspace.busy || !!workspace.draft.dirty.size;
  if (workspace.draft.dirty.size) block.append(el("p", { class: "notice warning" }, "请先保存分镜和项目设置，再生成或采用参考图。"));
  block.append(workspace.button("生成缺少的角色 / 场景图", async () => {
    await api(`/api/projects/${pid}/image-references/generate`, {});
    await workspace.services.refresh();
  }, true, { disabled: blocked || !data.candidates.length }));
  workspace.imageDrafts ||= new Map();
  const grid = el("div", { class: "reference-image-grid" });
  for (const item of data.candidates) {
    const draftKey = `${pid}/${item.key}`;
    const prompt = el("textarea", { rows: 3, value: workspace.imageDrafts.get(draftKey) || `${item.name}：${item.description}`, disabled: blocked,
      oninput: event => workspace.imageDrafts.set(draftKey, event.target.value) });
    const card = el("article", { class: "card reference-image-card" }, el("h3", {}, item.name), el("small", {}, kinds[item.kind]), field("画面描述", prompt),
      workspace.button(item.selected_asset ? "重新生成并采用" : "生成并采用", async () => {
        await api(`/api/projects/${pid}/image-references/${item.key}/generate`, { request: { prompt: prompt.value } });
        await workspace.services.refresh();
      }, false, { disabled: blocked }));
    for (const version of item.history) card.append(el("div", { class: "reference-version" },
      el("img", { src: workspace.current.assets[version.asset_id]?.file ? `/media/${pid}/` + workspace.current.assets[version.asset_id].file.split("/").map(encodeURIComponent).join("/") : `/api/images/${version.image_id}/file`, alt: `${item.name}历史图片`, loading: "lazy" }),
      workspace.button(version.asset_id === item.selected_asset ? "正在使用" : "采用此版本", async () => {
        await api(`/api/projects/${pid}/image-references/${item.key}/adopt`, { image_id: version.image_id });
        await workspace.services.refresh();
      }, false, { disabled: blocked || version.asset_id === item.selected_asset })));
    const latest = data.images.find(image => image.target === item.key);
    if (latest && !latest.file) card.append(badge(latest.busy ? "running" : latest.status), el("p", {}, latest.busy ? "项目顶部持续显示任务进度。" : latest.message));
    grid.append(card);
  }
  block.append(grid);
  if (!data.candidates.length) block.append(el("p", {}, "分镜生成后，这里会列出角色、场景和道具。"));
}
