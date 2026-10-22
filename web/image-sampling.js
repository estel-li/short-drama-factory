import { el, field, select } from "./api.js?v=3.8.0";

export const samplingDefaults = { steps: null, cfg: 1, sampler: "euler", scheduler: "auto", denoise: 1, negative_prompt: "" };
const samplers = ["euler", "euler_ancestral", "heun", "dpmpp_2m", "dpmpp_2m_sde", "dpmpp_sde", "uni_pc"];
const schedulers = [{ value: "auto", label: "模型推荐（Turbo 官方 / 标准 simple）" }, ...["simple", "normal", "karras", "exponential", "sgm_uniform", "beta"]];

export function readSampling(controls, edit) {
  const steps = controls.steps.value.trim();
  const cfg = controls.cfg.value.trim(), denoise = controls.denoise.value.trim();
  const result = { steps: steps === "" ? null : Number(steps), cfg: Number(cfg), sampler: controls.sampler.value,
    scheduler: controls.scheduler.value, denoise: edit ? Number(denoise) : 1, negative_prompt: controls.negative_prompt.value.trim() };
  if (result.steps !== null && (!Number.isInteger(result.steps) || result.steps < 1 || result.steps > 100)) throw Error("采样步数请输入 1～100 的整数，或留空使用模型推荐。");
  if (!cfg || !Number.isFinite(result.cfg) || result.cfg < 1 || result.cfg > 20) throw Error("CFG 请输入 1～20。");
  if (edit && (!denoise || !Number.isFinite(result.denoise) || result.denoise < 0.05 || result.denoise > 1)) throw Error("重绘强度请输入 0.05～1。");
  return result;
}

export class ImageSamplingControls {
  constructor({ value = {}, onChange = () => {}, disabled = false } = {}) {
    this.disabled = disabled;
    this.controls = {
      steps: el("input", { type: "number", min: 1, max: 100, step: 1, placeholder: "留空：Turbo 8 / 标准 40" }),
      cfg: el("input", { type: "number", min: 1, max: 20, step: 0.1 }),
      sampler: select(samplers, "euler"), scheduler: select(schedulers, "auto"),
      denoise: el("input", { type: "number", min: 0.05, max: 1, step: 0.05 }),
      negative_prompt: el("textarea", { rows: 2, maxLength: 4000, placeholder: "例如：水印、文字、模糊、多余手指；CFG 大于 1 时生效" }),
    };
    const c = this.controls;
    this.note = el("p", { class: "field-help", role: "status" });
    this.root = el("div", { class: "image-sampling-controls" },
      el("div", { class: "grid" }, field("采样步数 steps", c.steps), field("提示词引导 CFG", c.cfg),
        field("采样器 sampler", c.sampler), field("调度器 scheduler", c.scheduler), field("重绘强度 denoise", c.denoise,
          "仅编辑原图可用；小于 1 时从第一张原图编码后加噪重绘。越低通常保留越多，1 使用模型原生编辑。")),
      field("负面提示词", c.negative_prompt), this.note,
      el("p", { class: "field-help" }, "对应 ComfyUI 的采样参数。CFG > 1 增加计算量；增加步数不保证画质提升。Turbo 建议先用 8 步、CFG 1、Euler。"));
    for (const control of Object.values(c)) control.addEventListener("input", () => { this.sync(); onChange(); });
    this.load(value); this.setContext(false);
  }
  load(value = {}) {
    for (const [key, control] of Object.entries(this.controls)) control.value = value[key] ?? samplingDefaults[key] ?? "";
    this.sync();
  }
  draft() { return Object.fromEntries(Object.entries(this.controls).map(([key, control]) => [key, control.value])); }
  read() { return readSampling(this.controls, this.edit); }
  setModel(spec) {
    this.model = spec;
    this.controls.steps.placeholder = spec?.sampling?.steps ? `留空：模型推荐 ${spec.sampling.steps} 步` : "留空：Qwen Turbo 8 / 标准 40";
    this.sync();
  }
  setContext(edit, variant = this.variant, disabled = this.disabled) {
    this.edit = edit; this.variant = variant; this.disabled = disabled; this.sync();
  }
  sync() {
    for (const control of Object.values(this.controls)) control.disabled = !!this.disabled;
    this.controls.denoise.disabled = !!this.disabled || !this.edit;
    const c = this.controls, turbo = !this.model && this.variant?.startsWith("turbo"), steps = Number(c.steps.value || this.model?.sampling?.steps || (turbo ? 8 : 40));
    const official = turbo && steps === 8 && c.scheduler.value === "auto" && (!this.edit || Number(c.denoise.value) === 1);
    const scheduler = c.scheduler.value === "auto" ? this.model?.sampling?.scheduler || "simple" : c.scheduler.value;
    this.note.textContent = `${this.model || this.variant ? `${steps} 步 · ${official ? "官方 Turbo sigma 序列" : scheduler + " 调度"}` : "留空步数随实际模型选择：Qwen Turbo 8 步，标准 40 步"}。${Number(c.cfg.value) === 1 ? "CFG 为 1，负面提示词不参与引导。" : "负面提示词参与 CFG 引导。"}${turbo && !official ? " 当前已覆盖 Qwen Turbo 官方采样预设，建议先少量试图。" : ""}`;
  }
}

export function samplingSummary(value) {
  const scheduler = value.scheduler === "official_turbo" ? "官方 Turbo" : value.scheduler;
  return `${value.steps} 步 · CFG ${value.cfg} · ${value.sampler} · ${scheduler} · 重绘 ${value.denoise}`;
}
