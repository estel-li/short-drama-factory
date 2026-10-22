import {api, el, field, select} from "./api.js?v=3.9.0";
import {dialog} from "./ui.js?v=3.9.0";

export const slotNames = {source_audio: "驱动原声", source_video: "工作流源视频", guide_image: "中段引导图"};
export const formatSize = v => v < 1024 ** 3 ? `${(v / 1024 ** 2).toFixed(1)} MB` : `${(v / 1024 ** 3).toFixed(2)} GB`;
const active = state => ["queued", "running"].includes(state?.status);
const states = {queued: "排队中", running: "准备中", done: "已就绪", paused: "已暂停", error: "准备失败", idle: "未准备"};
const actions = {available: "引擎已识别", verified: "已校验", verify: "本地已有，待校验", local: "本地已有", missing: "未找到", download: "待下载"};

export function parameterSpecs(base) {
  const workflow = base.workflow || "native";
  const specs = [{key: "megapixels", title: "生成分辨率（百万像素）", min: .1, max: 4, step: .1,
    help: "16GB 显存从 0.4MP 起步；长镜头和放大会增加内存需求。"},
    {key: "steps", title: "采样步数", min: 1, max: 100, step: 1,
      choices: workflow === "pdd-8" ? [4, 6, 8] : ["lightx2v-8", "pdd-upscale"].includes(workflow) ? [8] : null}];
  const number = (key, title, min, max, step, fallback, help = "") => specs.push({key, title, min, max, step, fallback, help});
  if (!workflow.startsWith("h3-") && (base.turbo || workflow.startsWith("pdd") || workflow === "lightx2v-8")) number("lora_strength", "LoRA 强度", -2, 2, .05, 1);
  if (workflow.startsWith("pdd")) number("head_strength", "PDD 头强度", 0, 2, .05, 1);
  if (workflow === "pdd-upscale") {
    number("upscale_by", "神经放大倍数", 1, 2, .25, 1.25);
    specs.push({key: "refine_denoise", title: "放大后精修", choices: [{value: 0, label: "关闭"}, {value: .125, label: "单个训练块，轻度精修"}], fallback: .125});
  }
  if (["h3-audio-drive", "h3-foley", "h3-canny-control"].includes(workflow)) number("source_start_seconds", "源素材起点（秒）", 0, 15, .1, 0, "视频可用帧数须覆盖帧对齐后的镜长。");
  if (workflow === "h3-keyframe-guide") number("guide_position", "引导图时间位置（0～1）", .01, .99, .01, .5, "0.5 表示片段中间，是模型引导，不是逐像素拼贴。");
  if (workflow === "h3-motion-context") {
    specs.push({key: "context_frames", title: "动作上下文（帧）", choices: [5, 22, 39, 56], fallback: 22, help: "取源片末尾，采样后剪去重叠头部；上下文越长开销越高。"});
    number("audio_context_frames", "声音上下文（帧）", 0, 240, 1, 18, "0 跟随画面；有明确人声时需检查接续切口。");
  }
  if (workflow === "h3-canny-control") {
    number("control_strength", "轮廓控制强度", .05, 2, .05, .7);
    number("control_start", "控制开始（采样比例）", 0, 1, .01, 0);
    number("control_end", "控制结束（采样比例）", 0, 1, .01, .9);
    number("canny_low", "Canny 低阈值", .01, .99, .01, .2);
    number("canny_high", "Canny 高阈值", .01, .99, .01, .5);
  }
  return specs;
}

export function videoWorkflowControls(config, profile, onSaved) {
  const summary = el("div", {class: "workflow-summary"}), files = el("div");
  const note = el("p", {class: "field-help", role: "status", "aria-live": "polite"});
  const progress = el("progress", {max: 100, hidden: true, "aria-label": "当前文件准备进度"});
  const root = el("div", {class: "workflow-card"});
  let busy = false, observing = false, latest = null;
  const setButtons = () => { prepare.disabled = busy || active(latest); stop.hidden = !active(latest); stop.disabled = busy || !!latest?.cancel_requested; };
  const showState = state => {
    latest = state;
    const label = config.profiles[state.profile]?.label || state.profile || "";
    note.textContent = `${states[state.status] || ""}${label ? " · " + label : ""}：${state.message || ""}`;
    note.classList.toggle("error-text", state.status === "error");
    progress.hidden = !active(state);
    const p = state.progress;
    if (active(state) && p?.total && Number.isFinite(p.bytes)) {
      progress.value = Math.min(100, 100 * p.bytes / p.total);
      note.textContent += ` · ${formatSize(p.bytes)} / ${formatSize(p.total)}`;
    } else progress.removeAttribute("value");
    setButtons();
  };
  const observe = async jobId => {
    if (observing) return;
    observing = true;
    try {
      do {
        const state = await api("/api/video/workflows/progress" + (jobId ? `?job_id=${encodeURIComponent(jobId)}` : ""));
        if (!root.isConnected) break;
        showState(state);
        if (!active(state)) break;
        jobId = state.job_id;
        await new Promise(resolve => setTimeout(resolve, 1500));
      } while (root.isConnected);
    } catch (error) { note.textContent = error.message + " 后台任务可能仍在运行，点击“查看准备进度”重新连接。"; }
    finally { observing = false; setButtons(); }
  };
  const prepare = el("button", {class: "primary", onclick: async () => {
    if (busy || active(latest)) return;
    busy = true; setButtons();
    const selected = profile.value;
    try {
      note.textContent = "正在检查本地资源和所选工作流……";
      const plan = await api(`/api/video/workflows/plan?profile=${encodeURIComponent(selected)}`);
      files.replaceChildren(el("details", {}, el("summary", {}, "资源检查详情"),
        el("ul", {class: "model-download-list"}, [...plan.models, ...plan.plugins].map(item => el("li", {}, `${actions[item.action] || item.action} · ${item.name}`))),
        plan.missing_nodes?.length ? el("p", {class: "field-help"}, "待加载节点：" + plan.missing_nodes.join("、")) : null));
      if (plan.ready) { note.textContent = "所选工作流附加资源已就绪。基础 H3 模型请在“模型与环境”检查。"; return; }
      if (plan.remote) throw Error("请在远程 ComfyUI 准备所需节点和模型后重新检查。");
      if (plan.requires_confirmation) {
        const choice = await dialog("确认工作流资源下载", `工作流：${config.profiles[selected]?.label || selected}。需下载 ${formatSize(plan.download_bytes)}，可用磁盘 ${formatSize(plan.free_disk_bytes)}。文件：${[...plan.models, ...plan.plugins].filter(f => f.action === "download").map(f => f.name).join("、")}。`,
          [{label: "取消", value: "cancel"}, {label: "下载并准备", value: "prepare", primary: true}]);
        if (choice !== "prepare") { note.textContent = "已取消，本次没有开始下载。"; return; }
      }
      const result = await api("/api/video/workflows/prepare", {profile: selected, download_confirmation: plan.confirmation_token || ""});
      showState({job_id: result.job_id, profile: selected, status: "queued", message: "等待后台准备，可继续编辑。"});
      void observe(result.job_id);
    } catch (error) { note.textContent = error.message; }
    finally { busy = false; setButtons(); }
  }}, "检查并准备工作流");
  const stop = el("button", {hidden: true, onclick: async () => {
    stop.disabled = true;
    try { await api("/api/video/workflows/stop", {}); latest = {...latest, cancel_requested: true}; note.textContent = "已请求暂停，正在保存下载断点。"; }
    catch (error) { note.textContent = error.message; stop.disabled = false; }
  }}, "暂停准备");
  root.append(summary, el("div", {class: "actions"}, prepare,
    el("button", {onclick: () => editProfile(config, profile, onSaved, note)}, "调整参数 / 另存方案"),
    el("button", {onclick: () => observe()}, "查看准备进度"), stop), progress, note, files);
  const explain = () => {
    const p = config.profiles[profile.value] || {}, spec = config.video_workflows?.[p.workflow] || {};
    summary.replaceChildren(el("strong", {}, p.label || "请选择工作流"), el("p", {}, spec.description || "原生 H3 音画生成；适合常规短剧镜头。"),
      el("div", {class: "workflow-facts"}, el("span", {}, `${p.megapixels ?? "—"} MP · ${p.steps ?? "—"} 步 · ${spec.cost || "随参数变化"}开销`),
        el("span", {}, `模式：${spec.supported_modes?.join(" / ") || "文字 / 关键帧 / 多模态参考"}`)),
      el("p", {class: "field-help"}, spec.required_slots?.length ? "逐镜必需素材：" + spec.required_slots.map(k => slotNames[k] || k).join("、") + "。在分镜的“提示词与参考素材”中绑定。" : "无额外必需素材；按 H3 模式提供参考图或首尾帧。"),
      spec.limitation ? el("p", {class: "field-help"}, spec.limitation) : null);
  };
  profile.addEventListener("change", () => {
    explain(); files.replaceChildren();
    if (!active(latest)) {
      note.textContent = "已切换方案，点击“检查并准备工作流”核对附加资源。";
      note.classList.remove("error-text");
    }
  }); explain();
  queueMicrotask(() => { if (root.isConnected) void observe(); });
  return root;
}

function editProfile(config, profile, onSaved, note) {
  const baseId = profile.value, base = config.profiles[baseId];
  if (!base) { note.textContent = "请先选择有效工作流。"; return; }
  const modal = el("dialog", {class: "modal workflow-modal", "aria-labelledby": "workflow-editor-title"});
  const label = el("input", {value: base.label + " · 自定义", maxLength: 200, required: true}), controls = {};
  const inputs = parameterSpecs(base).map(spec => {
    const value = base[spec.key] ?? spec.fallback;
    const control = controls[spec.key] = spec.choices ? select(spec.choices.map(x => typeof x === "number" ? {value: x, label: String(x)} : x), value)
      : el("input", {type: "number", value, min: spec.min, max: spec.max, step: spec.step, required: true});
    return field(spec.title, control, spec.help);
  });
  const error = el("p", {class: "field-help error-text", role: "alert"});
  const close = () => { modal.close(); modal.remove(); profile.focus(); };
  const cancel = el("button", {onclick: close}, "取消");
  const save = el("button", {class: "primary", onclick: async () => {
    if (!label.reportValidity() || !label.value.trim()) return;
    save.disabled = true; cancel.disabled = true; error.textContent = "";
    try {
      const changes = Object.fromEntries(Object.entries(controls).map(([key, c]) => {
        if (!c.reportValidity() || c.value.trim() === "" || !Number.isFinite(Number(c.value))) throw Error("请填写范围内的有效数值。");
        return [key, Number(c.value)];
      }));
      if (changes.canny_low >= changes.canny_high) throw Error("Canny 低阈值必须小于高阈值。");
      if (changes.control_start >= changes.control_end) throw Error("控制开始比例必须小于结束比例。");
      const result = await api("/api/video/workflows/profiles", {base_profile: baseId, label: label.value.trim(), changes});
      config.profiles[result.id] = result.profile;
      profile.append(el("option", {value: result.id}, result.profile.label)); profile.value = result.id;
      profile.dispatchEvent(new Event("change", {bubbles: true})); onSaved();
      note.textContent = "方案已另存并选中。保存项目设置后生效。"; close();
    } catch (e) { error.textContent = e.message; }
    finally { save.disabled = false; cancel.disabled = false; }
  }}, "另存并选中");
  modal.append(el("h2", {id: "workflow-editor-title"}, "调整工作流参数"), el("p", {class: "field-help"}, `基于 ${base.label}，另存为独立方案。`),
    field("方案名称", label), el("div", {class: "grid"}, inputs), error, el("div", {class: "actions"}, cancel, save));
  modal.addEventListener("cancel", event => { event.preventDefault(); if (!save.disabled) close(); });
  document.body.append(modal); modal.showModal(); label.focus();
}
