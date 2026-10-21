import { api, el, field, select } from "./api.js?v=3.6.0";
import { badge, dialog, icon } from "./ui.js?v=3.6.0";
import { ImageInputPicker, imageFileData } from "./image-inputs.js?v=3.6.0";
import { ImageSamplingControls, samplingSummary } from "./image-sampling.js?v=3.6.0";

const kinds = { general: "自由创作", character: "角色参考", scene: "场景参考", prop: "道具参考" };
const variants = [{ value: "auto", label: "根据显存自动选择" }, { value: "turbo-int8", label: "Turbo INT8 · 快速预览" }, { value: "turbo-bf16", label: "Turbo BF16 · 大显存" }, { value: "quality-int8", label: "标准 INT8 · 细节优先" }];
const resolutions = ["auto", "512", "768", "1024", "1536", "2048"].map(value => ({ value, label: value === "auto" ? "根据显存自动选择" : `${value} 档（按比例换算）` }));
const bytes = value => `${(value / 1024 ** 3).toFixed(1)} GB`;
const modelLabels = { diffusion_models: "主模型文件", text_encoders: "文本编码器文件", vae: "VAE 文件", checkpoints: "整合模型文件" };

export class ImageWorkspace {
  constructor(container, services) {
    this.container = container;
    this.services = services;
    this.dirty = false;
    this.revision = 0;
    this.mounted = false;
    this.pendingOptimize = null;
    this.draftId = null;
    this.submitting = false;
    this.references = [];
  }
  button(text, work, props = {}) {
    return el("button", { onclick: event => this.services.act(work, event.currentTarget), ...props }, text);
  }
  mount() {
    if (this.mounted) return;
    this.mounted = true;
    const settings = this.services.config().image_generation || {};
    this.modelCatalog = this.services.config().image_models || { "qwen-image-2.1": { name: "Qwen-Image 2.1" } };
    this.settings = settings;
    this.controls = {
      image_model: select(Object.entries(this.modelCatalog).map(([value, spec]) => ({ value, label: spec.name })), settings.image_model || "qwen-image-2.1"),
      prompt: el("textarea", { rows: 6, maxLength: 12000, placeholder: "例如：雨后的小巷，暖黄色窗灯，一把蓝色旧伞，温暖手绘动漫风格……", required: true }),
      optimize: el("input", { type: "checkbox", checked: true }),
      optimized_prompt: el("textarea", { rows: 5, maxLength: 20000, placeholder: "可先优化查看结果，也可直接生成。填写后将使用这里的内容。" }),
      purpose: select(Object.entries(kinds).map(([value, label]) => ({ value, label })), "general"),
      ratio: select(["1:1", "3:4", "4:3", "9:16", "16:9", "2:3", "3:2"], "1:1"),
      resolution: select(resolutions, "auto"), variant: select(variants, "auto"),
      seed: el("input", { type: "number", min: 0, step: 1, placeholder: "留空随机" }),
      style: el("input", { maxLength: 3000, placeholder: "例如：二维动漫、写实摄影、水彩绘本" }),
      transparent: el("input", { type: "checkbox" }),
      reference_mode: select([{ value: "reference", label: "参考图创作（按所选画幅）" }, { value: "edit", label: "编辑原图（保持原图比例）" }], "reference"),
      provider: select(this.services.config().providers.map(p => ({ value: p.id, label: p.name })), settings.provider || "deepseek"),
      model: el("input", { value: settings.model || "", placeholder: "留空沿用提供商模型" }),
      skill: select([{ value: "", label: "根据用途选择 Skill" }, ...this.services.skills().filter(s => s.stage === "image_prompt").map(s => ({ value: s.id, label: s.name }))], ""),
    };
    const c = this.controls;
    this.modelNote = el("p", { class: "field-help", role: "status" });
    this.sampling = new ImageSamplingControls({ value: settings.sampling, onChange: () => { this.dirty = true; this.revision++; } });
    this.modelControls = Object.fromEntries(Object.keys(modelLabels).map(key => [key,
      select([{ value: "", label: "使用推荐文件" }, ...(settings.models?.[key] ? [{ value: settings.models[key], label: settings.models[key] }] : [])], settings.models?.[key] || "")]));
    this.optimizeButton = this.button("先优化提示词", () => this.submit(true));
    this.generateButton = this.button("生成图片", () => this.submit(false), { class: "primary" });
    this.draftNote = el("p", { class: "field-help", role: "status" });
    this.referencePicker = new ImageInputPicker({
      upload: async file => api("/api/image-inputs", { data: await imageFileData(file), name: file.name }),
      onChange: items => { this.references = items; this.referencesChanged(); },
      act: work => this.services.act(work),
      onBusy: busy => { this.referencesBusy = busy; this.syncButtons(); },
    });
    const form = el("div", { class: "card image-prompt-card" },
      el("h2", {}, "描述你想看到的画面"), field("生图模型", c.image_model), this.modelNote, field("自然语言描述", c.prompt),
      el("div", { class: "grid three" }, field("用途", c.purpose), field("画幅", c.ratio), field("风格", c.style)),
      el("details", { class: "option-section image-reference-options" }, el("summary", {}, "参考图 / 图生图"),
        this.referencePicker.root, field("参考方式", c.reference_mode),
        el("p", { class: "field-help" }, "无参考图时按文字生成。参考图上传到所选图片引擎；提示词优化只发送文字和图片编号。")),
      el("label", { class: "image-switch" }, c.optimize, el("span", {}, "优化提示词", el("small", {}, "默认开启；保留原意，补充构图、光影和可辨识细节。"))),
      field("优化后的提示词（可编辑）", c.optimized_prompt),
      el("details", { class: "option-section image-sampling-options" }, el("summary", {}, "高级采样参数 · 步数 / CFG / 重绘强度"),
        this.sampling.root, this.button("恢复模型推荐参数", () => {
          this.sampling.load(this.modelCatalog[c.image_model.value]?.sampling); this.dirty = true; this.revision++;
        })),
      el("details", { class: "option-section" }, el("summary", {}, "模型、清晰度与优化设置"),
        el("div", { class: "grid three" }, field("Qwen 精度方案", c.variant), field("图片大小", c.resolution), field("随机种子", c.seed),
          field("文字提供商", c.provider), field("文字模型", c.model), field("优化 Skill", c.skill)),
        el("p", { class: "field-help" }, "可选择目录中已有的文件；替换文件须与当前模型架构兼容。整合模型已包含编码器和 VAE，分体模型使用各自的编码器。"),
        el("div", { class: "grid" }, Object.entries(this.modelControls).map(([key, control]) => field(modelLabels[key], control))),
        el("label", { class: "image-switch" }, c.transparent, "请求透明背景 PNG"),
        this.button("保存为图片默认设置", async () => {
          this.settings = await api("/api/images/settings", { ...this.settings, image_model: c.image_model.value, variant: c.variant.value, provider: c.provider.value,
            model: c.model.value.trim(), skill: c.skill.value || "image-qwen-general", models: this.readModels(), sampling: this.sampling.read() });
          await this.services.reloadConfig(); this.services.toast("图片模型、采样参数和优化提供商默认设置已保存。");
        })),
      el("div", { class: "actions" }, this.optimizeButton, this.generateButton), this.draftNote,
      el("p", { class: "field-help" }, "图片在本地 ComfyUI 生成。勾选优化时，文字会发送到所选文字提供商；也可选本地模型。"));
    for (const [name, control] of Object.entries(c)) control.addEventListener("input", () => {
      this.dirty = true; this.revision++;
      if (["prompt", "purpose", "style", "ratio", "transparent", "reference_mode", "image_model"].includes(name)) c.optimized_prompt.value = "";
      c.optimized_prompt.disabled = !c.optimize.checked;
      if (name === "reference_mode") this.syncReferenceMode();
    });
    c.variant.addEventListener("change", () => this.services.act(() => this.refreshEnvironment()));
    c.image_model.addEventListener("change", () => {
      c.optimized_prompt.value = "";
      this.pendingOptimize = null;
      for (const control of Object.values(this.modelControls)) control.value = "";
      this.sampling.load(this.modelCatalog[c.image_model.value]?.sampling);
      c.variant.value = "auto";
      this.syncReferenceMode();
      this.services.act(() => this.refreshEnvironment());
    });
    for (const control of Object.values(this.modelControls)) control.addEventListener("change", () => {
      this.dirty = true; this.revision++;
      this.services.act(() => this.refreshEnvironment());
    });
    this.environmentBox = el("div", { class: "card image-environment" });
    this.progressBox = el("div", { class: "notice", hidden: true, role: "status" });
    this.gallery = el("div", { class: "image-gallery" });
    this.container.replaceChildren(el("div", { class: "image-studio-layout" }, form, this.environmentBox), this.progressBox,
      el("div", { class: "section-toolbar" }, el("h2", {}, "图片历史 · 最近 200 张"), this.button("刷新", () => this.refresh())), this.gallery);
    this.services.act(() => this.refreshEnvironment());
    this.services.act(() => this.refresh());
    this.syncReferenceMode();
  }
  syncReferenceMode() {
    const c = this.controls, qwen = c.image_model.value === "qwen-image-2.1";
    const spec = this.modelCatalog[c.image_model.value] || {};
    c.variant.disabled = !qwen;
    c.transparent.disabled = !qwen;
    if (!qwen) {
      c.transparent.checked = false;
      if (this.references.length) c.reference_mode.value = "edit";
    }
    for (const option of c.reference_mode.options) option.disabled = !qwen && option.value === "reference";
    if (this.modelNote) this.modelNote.textContent = qwen ? "支持最多 10 张语义参考图、编辑原图及原生透明通道。" :
      `${spec.name || "所选模型"}：支持文字生图和单张原图重绘；重绘强度越低通常保留越多。${spec.validation === "pending" ? " 本机生成测试进行中。" : ""}`;
    if (this.referencePicker && this.referencePicker.maxItems !== (qwen ? 10 : 1)) {
      this.referencePicker.maxItems = qwen ? 10 : 1;
      this.referencePicker.render();
    }
    this.controls.reference_mode.disabled = !this.references.length || !!this.referencesBusy;
    if (!this.references.length) this.controls.reference_mode.value = "reference";
    this.controls.ratio.disabled = this.references.length > 0 && this.controls.reference_mode.value === "edit";
    this.sampling?.setModel(qwen ? null : spec);
    this.sampling?.setContext(this.references.length > 0 && this.controls.reference_mode.value === "edit", this.plan?.variant);
  }
  referencesChanged() {
    this.dirty = true; this.revision++;
    this.controls.optimized_prompt.value = "";
    this.syncReferenceMode();
  }
  read() {
    const values = Object.fromEntries(Object.entries(this.controls).map(([name, c]) => [name, c.type === "checkbox" ? c.checked : c.value.trim()]));
    if (!values.prompt) throw Error("请先写下想生成的画面。");
    values.seed = values.seed === "" ? null : Number(values.seed);
    if (values.seed !== null && (!Number.isSafeInteger(values.seed) || values.seed < 0)) throw Error("随机种子请输入非负安全整数，或留空。");
    if (!values.optimize) values.optimized_prompt = "";
    values.models = this.readModels();
    if (values.image_model !== "qwen-image-2.1" && this.references.length > 1) throw Error("当前模型仅支持一张原图；请移除多余图片，或选择 Qwen 多图参考。");
    values.reference_images = this.references.map(item => item.id);
    values.sampling = this.sampling.read();
    return values;
  }
  readModels() { return Object.fromEntries(Object.entries(this.modelControls).map(([key, control]) => [key, control.value])); }
  syncButtons() {
    this.optimizeButton.disabled = this.generateButton.disabled = !!(this.submitting || this.draftBusy || this.referencesBusy);
    if (this.referencePicker) {
      this.referencePicker.disabled = !!(this.submitting || this.draftBusy);
      this.referencePicker.render();
      this.syncReferenceMode();
    }
  }
  async confirmPreparation(request) {
    const plan = await api("/api/images/environment/plan", { image_model: request.image_model || "qwen-image-2.1", variant: request.variant, models: request.models });
    if (plan.selection_errors?.length) throw Error(plan.selection_errors.join("；"));
    if (!plan.ready && !plan.local_download) throw Error("请在目标图片服务安装所选模型；本机下载无法修复远程模型目录。");
    if (plan.requires_confirmation) {
      const files = plan.models.filter(m => m.action === "download").map(m => m.name).join("、");
      const choice = await dialog("需要下载模型", `${files || "需要准备图片引擎运行时"}。预计下载 ${bytes(plan.download_bytes)}${plan.verify_bytes ? `，另有 ${bytes(plan.verify_bytes)} 待校验，失败时需要补下载` : ""}，目标目录：${plan.models_dir}。已有文件先校验并复用，确认后会显示进度，可随时暂停。`,
        [{ label: "暂不下载", value: "cancel" }, { label: "确认下载并继续", value: "download", primary: true }]);
      if (choice !== "download") return null;
    }
    return plan;
  }
  async submit(optimizeOnly) {
    if (this.submitting || this.draftBusy || this.referencesBusy) return;
    this.submitting = true; this.syncButtons();
    try {
    const request = this.read();
    if (optimizeOnly) { request.optimize = true; request.optimized_prompt = ""; }
    const revision = this.revision;
    let existing = this.draftId ? await api(`/api/images/${this.draftId}`) : null;
    if (existing?.busy) throw Error("提示词任务仍在处理中，请等待完成后继续。");
    if (existing?.file || existing?.prompt_id) existing = null;
    const plan = optimizeOnly ? null : await this.confirmPreparation(request);
    if (!optimizeOnly && !plan) return;
    const body = { request, optimize_only: optimizeOnly, download_confirmation: plan?.confirmation_token || "" };
    const result = await api(existing ? `/api/images/${existing.id}/generate` : "/api/images", body);
    this.draftId = result.id; this.draftBusy = true;
    if (optimizeOnly) this.pendingOptimize = { id: result.id, revision };
    if (revision === this.revision) this.dirty = false;
    this.services.toast(optimizeOnly ? "优化任务已排队，生成图片时会继续这条任务。" : existing ? "已继续原任务，使用当前编辑后的提示词生成。" : "图片已排队。");
    if (plan && !plan.ready) this.showProgress({ imageId: result.id });
    await this.refresh();
    } finally { this.submitting = false; this.syncButtons(); }
  }
  load(record) {
    for (const [name, control] of Object.entries(this.controls)) {
      const value = name === "optimized_prompt" ? record.optimized_prompt || record.request.optimized_prompt || "" : record.request[name];
      if (control.type === "checkbox") control.checked = !!value;
      else control.value = value ?? (name === "image_model" ? "qwen-image-2.1" : name === "reference_mode" ? "reference" : "");
    }
    this.controls.optimized_prompt.disabled = !this.controls.optimize.checked;
    this.sampling.load(record.request.sampling);
    this.references = record.reference_inputs || [];
    this.referencePicker.items = this.references; this.referencePicker.render();
    this.syncReferenceMode();
    for (const [key, control] of Object.entries(this.modelControls)) {
      const value = record.request.models?.[key] || "";
      if (![...control.options].some(option => option.value === value)) control.append(el("option", { value }, value));
      control.value = value;
    }
    this.draftId = !record.file && !record.prompt_id ? record.id : null;
    this.draftBusy = !!record.busy; this.pendingOptimize = null; this.syncButtons();
    this.dirty = true; this.revision++;
    this.controls.prompt.focus();
    this.services.toast("参数已载入，可以编辑提示词后再生成。");
    this.services.act(() => this.refreshEnvironment());
  }
  async refreshEnvironment() {
    const version = this.environmentRevision = (this.environmentRevision || 0) + 1;
    this.environmentBox.replaceChildren(el("p", {}, "正在检测图片引擎与目标显卡……"));
    const plan = await api("/api/images/environment/plan", { image_model: this.controls.image_model.value, variant: this.controls.variant.value, models: this.readModels() });
    if (version !== this.environmentRevision) return;
    for (const [key, control] of Object.entries(this.modelControls)) {
      const needed = plan.models.some(model => model.category === key);
      control.closest(".field").hidden = !needed;
    }
    this.plan = plan;
    this.syncReferenceMode();
    for (const [key, control] of Object.entries(this.modelControls)) {
      const value = control.value;
      const entries = plan.available_models?.[key] || [];
      control.replaceChildren(el("option", { value: "" }, "使用推荐文件"), ...entries.map(item => el("option", { value: item.name }, `${item.name}${item.source === "folder" ? "（目录已有）" : ""}`)));
      if (value && !entries.some(item => item.name === value)) control.append(el("option", { value }, value + "（未找到）"));
      control.value = value;
    }
    const s = this.engineDraft || this.settings;
    const engine = select([{ value: "auto", label: "自动选择兼容引擎" }, { value: "shared", label: "复用指定 ComfyUI" }, { value: "managed", label: "独立图片引擎" }], s.engine || "auto");
    const url = el("input", { value: s.comfy_url || "", placeholder: "留空使用视频引擎地址" });
    const directoryKey = this.controls.image_model.value === "qwen-image-2.1" ? "models_dir" : "library_models_dir";
    const directory = el("input", { value: s[directoryKey] || "", placeholder: "留空使用推荐目录" });
    const port = el("input", { type: "number", min: 1024, max: 65535, value: s.managed_port || 8190 });
    for (const control of [engine, url, directory, port]) control.addEventListener("input", () => {
      this.engineDraft = { ...s, engine: engine.value, comfy_url: url.value, [directoryKey]: directory.value, managed_port: Number(port.value) };
      this.dirty = true;
    });
    this.environmentBox.replaceChildren(el("h2", {}, "图片生成环境"), el("span", { class: "badge " + (plan.ready ? "success" : "warning") }, plan.ready ? "环境就绪" : "需要准备"),
      el("p", {}, plan.gpu?.name?.replace(/^cuda:\d+\s*:?\s*/, "").replace(/\s*:\s*cudaMallocAsync.*$/, "") || "显卡信息暂不可用", plan.vram_mb ? ` · ${(plan.vram_mb / 1024).toFixed(1)} GB` : ""),
      el("p", { class: "muted" }, plan.recommendation.message),
      el("p", {}, `本次方案：${plan.variants[plan.variant].name}`),
      el("p", {}, plan.engine === "managed" ? "使用独立图片引擎" : "复用已有 ComfyUI"),
      el("p", {}, plan.download_bytes ? `待下载 ${bytes(plan.download_bytes)} · 磁盘剩余 ${bytes(plan.free_disk_bytes)}` : plan.verify_bytes ? "本地模型需要校验，校验通过后直接启动引擎。" : plan.ready ? "所选模型已就绪，无需下载。" : "所选模型已在本地，启动引擎即可使用，无需下载。"),
      ...(plan.selection_errors?.length ? [el("p", { class: "notice warning" }, plan.selection_errors.join("；"))] : []),
      ...(plan.bootstrap_needed ? [el("p", { class: "muted" }, `首次还会准备独立 GPU 运行时（下载 ${bytes(plan.runtime_download_bytes)}，另需解压空间）。`)] : []),
      el("ul", { class: "model-download-list" }, plan.models.map(m => el("li", {}, `${({ available: "已识别", verified: "已校验，可复用", verify: "本地已有，待校验", local: "目录已有", missing: "文件缺失" })[m.action] || "需下载"} · ${m.name} · ${m.size ? bytes(m.size) : "大小由目标服务管理"}`))),
      el("p", { class: "notice warning" }, plan.license.notice, " ", el("a", { href: plan.license.url, target: "_blank", rel: "noopener noreferrer" }, "模型许可")),
      el("div", { class: "actions" }, this.button("检查环境", () => this.refreshEnvironment()),
        this.button(plan.download_bytes ? "下载缺少的文件" : plan.ready ? "检查就绪状态" : "启动 / 准备图片引擎", () => this.prepareEnvironment()),
        this.button("查看准备进度", () => this.showProgress(this.downloadSession || { environment: true }))),
      el("details", { class: "option-section" }, el("summary", {}, "图片引擎设置"), field("引擎方式", engine), field("已有服务地址", url), field("模型存放目录", directory), field("独立引擎端口", port),
        el("p", { class: "field-help" }, "缺少模型时先确认下载。窗口可关闭，后台继续准备；暂停后可继续下载。"),
        this.button("保存引擎设置", async () => {
          this.settings = await api("/api/images/settings", { ...s, engine: engine.value, comfy_url: url.value.trim(), [directoryKey]: directory.value.trim(), managed_port: Number(port.value), auto_download: false });
          this.engineDraft = null;
          await this.services.reloadConfig(); await this.refreshEnvironment();
          this.services.toast("图片引擎设置已保存。");
        })));
  }
  async prepareEnvironment() {
    const request = { image_model: this.controls.image_model.value, variant: this.controls.variant.value, models: this.readModels() };
    const plan = await this.confirmPreparation(request);
    if (!plan) return;
    if (plan.ready) { this.services.toast("所选图片模型已就绪。"); return; }
    const result = await api("/api/images/environment/prepare", { ...request, download_confirmation: plan.confirmation_token });
    this.showProgress({ environment: true, jobId: result.job_id });
  }
  showProgress(session) {
    this.downloadSession = session;
    this.progressModal?.close();
    const content = el("div", { class: "image-download-progress", role: "status" }, "正在读取进度……");
    const modal = el("dialog", { class: "dialog image-download-dialog", "aria-label": "图片任务进度" }, el("h2", {}, "图片任务进度"), content);
    this.progressModal = modal;
    const stop = this.button("暂停任务", async () => {
      await api(session.imageId ? `/api/images/${session.imageId}/stop` : session.projectId ? "/api/stop" : "/api/images/environment/stop", session.projectId ? { id: session.projectId } : {});
      stop.disabled = true;
    });
    modal.append(el("p", { class: "field-help" }, "关闭窗口后任务继续。已有模型会直接复用；只有缺少文件时才需要确认下载。"),
      el("div", { class: "actions" }, stop, this.button("关闭窗口", () => modal.close())));
    let timer;
    modal.addEventListener("close", () => { clearTimeout(timer); modal.remove(); if (this.progressModal === modal) this.progressModal = null; });
    const tick = async () => {
      try {
        let state;
        if (session.imageId) state = await api(`/api/images/${session.imageId}`);
        else if (session.projectId) {
          const project = await api(`/api/project/${session.projectId}`);
          const jobs = await api("/api/jobs"), job = jobs.find(j => j.id === session.jobId);
          state = { ...(project.state.job_id === session.jobId ? project.state : {}),
            status: job?.status || "queued", busy: !job || ["queued", "running"].includes(job.status), message: job?.message || "参考图准备已排队。" };
        }
        else {
          state = await api("/api/images/environment/progress");
          const jobs = await api("/api/jobs");
          const job = session.jobId ? jobs.find(j => j.id === session.jobId) : jobs.find(j => j.project_id === "__image_environment");
          if (job) state = { ...(state.job_id === job.id ? state : {}), status: job.status, message: job.message || "环境准备已排队。", busy: ["queued", "running"].includes(job.status) };
        }
        if (!modal.open) return;
        const progress = state.progress || {};
        content.replaceChildren(badge(state.busy && state.status === "new" ? "queued" : state.status || "ready"), el("p", {}, state.message || "当前没有下载任务。"));
        if (progress.file) content.append(el("p", { class: "image-download-file" }, "当前文件：" + progress.file));
        if (progress.total) {
          const count = Math.min(progress.bytes || 0, progress.total), percent = Math.floor(count / progress.total * 100);
          content.append(el("progress", { max: progress.total, value: count }), el("p", {}, `${percent}% · ${bytes(count)} / ${bytes(progress.total)}`));
        }
        stop.disabled = !state.busy;
        if (state.busy || state.status === "running") timer = setTimeout(tick, 1500);
      } catch (error) {
        if (modal.open) { content.replaceChildren(el("p", {}, error.message + "，正在重新读取原任务。")); timer = setTimeout(tick, 3000); }
      }
    };
    document.body.append(modal); modal.showModal(); tick();
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
      let current = this.draftId && records.find(r => r.id === this.draftId);
      if (this.draftId && !current) current = await api(`/api/images/${this.draftId}`);
      this.draftBusy = !!current?.busy; this.syncButtons();
      this.draftNote.textContent = current?.busy ? "当前任务正在处理，请等待后继续。" : current?.status === "ready" ? "提示词已优化；生成图片将继续这条任务，可先编辑优化结果。" : "";
      const pending = this.pendingOptimize && current?.id === this.pendingOptimize.id ? current : null;
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
    if (record.url) actions.append(el("a", { class: "button", href: record.url, download: `${record.id}.png` }, "下载 PNG"), this.button("用作参考图", async () => {
      const item = await api(`/api/images/${record.id}/use-as-reference`, {});
      await this.referencePicker.run(() => this.referencePicker.addItems([item]));
      this.container.querySelector(".image-reference-options").open = true;
      this.referencePicker.root.scrollIntoView({ behavior: "smooth", block: "center" });
    }, { disabled: !!(this.submitting || this.draftBusy || this.referencesBusy) }));
    if (record.busy) actions.append(this.button("停止", async () => { await api(`/api/images/${record.id}/stop`, {}); await this.refresh(); }));
    else {
      actions.append(this.button(record.url ? "重新生成" : "新种子重试", async () => {
        const plan = await this.confirmPreparation(record.request); if (!plan) return;
        const result = await api(`/api/images/${record.id}/regenerate`, { download_confirmation: plan.confirmation_token });
        if (!plan.ready) this.showProgress({ imageId: result.id });
        await this.refresh();
      }, { disabled: record.project_busy }));
      if (!record.url) actions.append(this.button(record.status === "ready" ? "继续生成图片" : "继续原任务", async () => {
        if (!record.prompt_id) { this.load(record); await this.submit(false); }
        else { await api(`/api/images/${record.id}/resume`, {}); await this.refresh(); }
      }, { disabled: record.project_busy }));
      actions.append(this.button("删除", async () => {
        if (await dialog("删除这张图片？", "将删除图片库中的原图、提示词记录与工作流。项目已采用的素材及参考图历史会保留。", [{ label: "取消", value: "cancel" }, { label: "删除图片", value: "delete", danger: true }]) !== "delete") return;
        await api(`/api/images/${record.id}/delete`, {});
        if (this.draftId === record.id) { this.draftId = null; this.pendingOptimize = null; this.draftBusy = false; }
        await this.refresh();
      }, { disabled: record.project_busy }));
    }
    if (record.status === "preparing" || record.progress) actions.append(this.button("任务进度", () => this.showProgress({ imageId: record.id })));
    row.append(actions);
    if (record.url && record.request.transparent && !record.has_transparency) row.append(el("p", { class: "notice warning" }, "本次未生成透明区域，可调整描述后重试。"));
    if (record.optimized_prompt || record.effective_prompt) row.append(el("details", {}, el("summary", {}, "查看生成提示词"), el("p", { class: "prompt-text" }, record.optimized_prompt || record.effective_prompt)));
    if (record.effective_sampling) row.append(el("details", {}, el("summary", {}, "实际采样参数"),
      el("p", { class: "prompt-text" }, samplingSummary(record.effective_sampling)),
      record.effective_sampling.negative_prompt ? el("p", { class: "prompt-text" }, "负面提示词：" + record.effective_sampling.negative_prompt) : null));
    if (record.reference_inputs?.length) {
      const previews = record.reference_inputs.map((item, index) => el("a", { href: item.url, target: "_blank", rel: "noopener" },
        el("img", { src: item.url, alt: `生成依据 ${index + 1}`, loading: "lazy" })));
      row.append(el("details", {}, el("summary", {}, `生成依据 · ${record.reference_inputs.length} 张参考图 · ${record.request.reference_mode === "edit" ? "编辑原图" : "参考图创作"}`),
        el("div", { class: "image-input-grid" }, previews)));
    }
    return row;
  }
}

export async function renderReferenceImages(workspace, box) {
  const pid = workspace.current.id;
  const preparation = new ImageWorkspace(null, workspace.services);
  const imageModel = workspace.current.settings.reference_images?.image_model || "qwen-image-2.1";
  const imageSpec = workspace.services.config().image_models?.[imageModel];
  const referenceSampling = imageModel === (workspace.services.config().image_generation?.image_model || "qwen-image-2.1") ? workspace.services.config().image_generation?.sampling : imageSpec?.sampling;
  const modelRequest = { image_model: imageModel, variant: workspace.current.settings.reference_images?.variant || "auto", models: null };
  const block = el("section", { class: "reference-studio" }, el("h2", {}, "用本地模型生成项目参考图"),
    el("p", { class: "muted" }, "角色图用于身份一致性，场景图用于空间一致性。生成并采用后，会更新对应分镜；旧图和历史版本保留。"));
  box.prepend(block);
  const data = await api(`/api/projects/${pid}/image-references`);
  if (!block.isConnected || workspace.current.id !== pid) return;
  const blocked = workspace.busy || !!workspace.draft.dirty.size;
  if (workspace.draft.dirty.size) block.append(el("p", { class: "notice warning" }, "请先保存分镜和项目设置，再生成或采用参考图。"));
  const batchGenerate = workspace.button("生成缺少的角色 / 场景图", async () => {
    const plan = await preparation.confirmPreparation(modelRequest); if (!plan) return;
    const task = await api(`/api/projects/${pid}/image-references/generate`, { download_confirmation: plan.confirmation_token });
    if (!plan.ready) preparation.showProgress({ projectId: pid, jobId: task.job_id });
    await workspace.services.refresh();
  }, true, { disabled: blocked || !data.candidates.length });
  block.append(batchGenerate);
  const unsupportedNote = el("p", {class:"notice warning",hidden:true}, "所选模型只支持一张原图重绘。请移除多余参考图，并将有原图的项目改为“编辑第一张原图”后生成。");
  block.append(unsupportedNote);
  let savingSources = 0;
  const generateButtons = [batchGenerate];
  workspace.imageDrafts ||= new Map();
  workspace.imageSamplingDrafts ||= new Map();
  const syncGeneration = () => {
    const dirtySampling = [...workspace.imageSamplingDrafts.entries()].some(([key, value]) => key.startsWith(pid + "/") && value.dirty);
    const incompatible = imageModel !== "qwen-image-2.1" && data.candidates.some(item=>item.source_assets?.length && (item.source_assets.length>1 || item.reference_mode!=="edit"));
    unsupportedNote.hidden = !incompatible;
    for (const button of generateButtons) button.disabled = blocked || savingSources > 0 || dirtySampling || incompatible;
  };
  const grid = el("div", { class: "reference-image-grid" });
  for (const item of data.candidates) {
    const draftKey = `${pid}/${item.key}`;
    const prompt = el("textarea", { rows: 3, value: workspace.imageDrafts.get(draftKey) || `${item.name}：${item.description}`, disabled: blocked,
      oninput: event => workspace.imageDrafts.set(draftKey, event.target.value) });
    const generate = workspace.button(item.selected_asset ? "重新生成并采用" : "生成并采用", async () => {
        const plan = await preparation.confirmPreparation(modelRequest); if (!plan) return;
        const task = await api(`/api/projects/${pid}/image-references/${item.key}/generate`, { request: { prompt: prompt.value }, download_confirmation: plan.confirmation_token });
        if (!plan.ready) preparation.showProgress({ imageId: task.id });
        await workspace.services.refresh();
      }, false, { disabled: blocked });
    generateButtons.push(generate);
    const mode = select([{ value: "reference", label: "参考图创作" }, { value: "edit", label: "编辑第一张原图" }], item.source_assets?.length ? item.reference_mode || "reference" : imageModel === "qwen-image-2.1" ? "reference" : "edit");
    if (imageModel !== "qwen-image-2.1") mode.options[0].disabled = true;
    mode.disabled = blocked || !item.source_assets?.length;
    const assetItem = asset => ({ id: asset.id, name: asset.name, url: `/media/${pid}/` + asset.file.split("/").map(encodeURIComponent).join("/") });
    const available = select([{ value: "", label: "选择项目已有图片……" }, ...Object.values(workspace.current.assets).filter(a => a.type === "image").map(a => ({ value: a.id, label: a.name }))], "");
    available.disabled = blocked;
    const note = el("p", { class: "field-help" }, "已自动保存参考依据；移除仅取消生成引用，保留项目素材。无参考图时按文字生成。");
    const persist = async (items, selectedMode = mode.value, sampling = item.sampling) => {
      if (sampling && (!items.length || selectedMode !== "edit")) sampling = { ...sampling, denoise: 1 };
      const saved = await api(`/api/projects/${pid}/image-references/${item.key}/sources`, { asset_ids: items.map(a => a.id), reference_mode: items.length ? selectedMode : "reference", sampling: sampling || null });
      item.sampling = saved.sampling; item.reference_mode = saved.reference_mode;
      item.source_assets = saved.asset_ids;
      mode.value = !items.length && imageModel !== "qwen-image-2.1" ? "edit" : saved.reference_mode; mode.disabled = blocked || !items.length;
      syncSampling(); syncGeneration();
      note.textContent = items.length ? `已保存 ${items.length} 张参考图；单项及批量生成都会使用。` : "无参考图，按文字生成。项目素材仍保留。";
    };
    const picker = new ImageInputPicker({
      maxItems: imageModel === "qwen-image-2.1" ? 10 : 1,
      items: (item.source_assets || []).map(id => workspace.current.assets[id] ? assetItem(workspace.current.assets[id]) : { id, name: "参考素材缺失，请移除或重选", url: "" }),
      disabled: blocked, act: work => workspace.services.act(work), onChange: items => persist(items),
      onBusy: busy => {
        savingSources += busy ? 1 : -1;
        syncGeneration();
        available.disabled = blocked || busy; mode.disabled = blocked || busy || !picker.items.length;
        syncSampling();
      },
      upload: async file => {
        const asset = await api(`/api/projects/${pid}/assets`, { data: await imageFileData(file), name: file.name, type: "image", character: "" });
        workspace.current.assets[asset.id] = asset;
        available.append(el("option", { value: asset.id }, asset.name));
        return assetItem(asset);
      },
    });
    available.addEventListener("change", () => {
      const asset = workspace.current.assets[available.value];
      if (asset) picker.run(() => picker.addItems([assetItem(asset)]));
      available.value = "";
    });
    mode.addEventListener("change", () => {
      const selectedMode = mode.value;
      picker.run(async () => {
        try { await persist(picker.items, selectedMode); item.reference_mode = selectedMode; }
        catch (error) { mode.value = item.reference_mode || "reference"; throw error; }
      });
    });
    const storedSampling = workspace.imageSamplingDrafts.get(draftKey);
    const inheritSampling = el("input", { type: "checkbox", checked: storedSampling ? storedSampling.inherit : !item.sampling, disabled: blocked });
    let samplingControls;
    const samplingChanged = () => {
      workspace.imageSamplingDrafts.set(draftKey, { inherit: inheritSampling.checked, value: samplingControls.draft(), dirty: true });
      samplingStatus.textContent = "采样参数有修改，请保存后生成。";
      syncSampling(); syncGeneration();
    };
    samplingControls = new ImageSamplingControls({ value: storedSampling?.value || item.sampling || referenceSampling,
      onChange: samplingChanged });
    samplingControls.setModel(imageModel === "qwen-image-2.1" ? null : imageSpec);
    const samplingStatus = el("p", { class: "field-help", role: "status" }, storedSampling?.dirty ? "采样参数有修改，请保存后生成。" : "单项、批量和自动补齐均使用这里保存的参数。");
    function syncSampling() {
      samplingControls?.setContext(!!picker.items.length && mode.value === "edit", modelRequest.variant === "auto" ? undefined : modelRequest.variant,
        blocked || picker.busy || inheritSampling.checked);
      inheritSampling.disabled = blocked || picker.busy;
    }
    inheritSampling.addEventListener("change", samplingChanged);
    const saveSampling = workspace.button("保存本项采样参数", () => picker.run(async () => {
      const sampling = inheritSampling.checked ? null : samplingControls.read();
      await persist(picker.items, mode.value, sampling);
      workspace.imageSamplingDrafts.delete(draftKey); samplingStatus.textContent = "本项采样参数已保存。"; syncGeneration();
    }), false, { disabled: blocked });
    const resetSampling = workspace.button("恢复继承默认", () => {
      inheritSampling.checked = true;
      samplingControls.load(referenceSampling);
      samplingChanged();
    }, false, { disabled: blocked });
    syncSampling();
    const card = el("article", { class: "card reference-image-card" }, el("h3", {}, item.name), el("small", {}, kinds[item.kind]), field("画面描述", prompt),
      el("details", { class: "option-section", open: !!item.source_assets?.length }, el("summary", {}, "自定义图片参考"),
        picker.root, field("已有项目图片", available), field("参考方式", mode), note),
      el("details", { class: "option-section reference-sampling-options", open: !!storedSampling?.dirty }, el("summary", {}, "本项高级采样参数"),
        el("label", { class: "image-switch" }, inheritSampling, "继承图片工作室默认参数"), samplingControls.root,
        el("div", { class: "actions" }, saveSampling, resetSampling), samplingStatus), generate);
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
  syncGeneration();
  if (!data.candidates.length) block.append(el("p", {}, "分镜生成后，这里会列出角色、场景和道具。"));
}
