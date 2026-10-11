import { api, el, field, select, download } from "./api.js";
import { optionsEditor, MODES } from "./options.js";
import {
  ProjectDraft,
  STAGES,
  isBusy,
  projectStatus,
  shotRecord,
  continuationIssue,
} from "./state.js";
import { badge, dialog, empty, icon, tabs } from "./ui.js";

const SCOPES = { story: "分镜", settings: "项目设置", outline: "大纲" };
const PANEL_NAMES = [
  { id: "story", label: "分镜" },
  { id: "media", label: "成片与镜头" },
  { id: "outline", label: "故事与大纲" },
  { id: "settings", label: "项目设置" },
  { id: "assets", label: "素材" },
  { id: "records", label: "记录" },
];
export const mediaUrl = (pid, relative) =>
  "/media/" +
  pid +
  "/" +
  relative.replaceAll("\\", "/").split("/").map(encodeURIComponent).join("/");
const clipPath = (record, shot) =>
  record.clip_relative ||
  (record.clip
    ? "clips/" + record.clip.split(/[/\\]/).pop()
    : "clips/" + (shot.uid || String(shot.id).padStart(3, "0")) + ".mp4");

export class Workspace {
  constructor(container, services) {
    this.container = container;
    this.services = services;
    this.panel = "story";
    this.selectedShot = null;
    this.draft = null;
    this.saving = false;
    this.openDetails = new Set();
    this.rawStoryJson = null;
    this.invalidBindings = new Map();
  }
  get current() {
    return this.draft?.project;
  }
  get busy() {
    return (
      !!this.current?.busy ||
      isBusy(projectStatus(this.current || {}, this.services.jobs()))
    );
  }
  button(text, work, primary = false, props = {}) {
    return el(
      "button",
      {
        class: primary ? "primary" : "",
        onclick: (event) => this.services.act(work, event.currentTarget),
        ...props,
      },
      text,
    );
  }
  load(project) {
    this.draft = new ProjectDraft(project);
    this.rawStoryJson = null;
    this.invalidBindings.clear();
    this.selectedShot = project.story?.shots[0]?.uid;
    this.panel = project.story ? "story" : "outline";
    this.render();
  }
  update(project) {
    if (!this.current || project.id !== this.current.id) return;
    const before = JSON.stringify([
        this.draft.data.story,
        this.draft.data.outline,
        this.draft.data.settings,
        Object.values(this.current.state.shots || {}).map((record) => [
          record.status,
          record.clip_relative,
          record.first_frame?.file,
        ]),
        this.current.assets,
        this.current.references,
        this.current.final,
        this.current.subtitled,
      ]),
      wasBusy = this.renderedBusy;
    this.draft.ingest(project);
    const after = JSON.stringify([
      this.draft.data.story,
      this.draft.data.outline,
      this.draft.data.settings,
      Object.values(project.state.shots || {}).map((record) => [
        record.status,
        record.clip_relative,
        record.first_frame?.file,
      ]),
      project.assets,
      project.references,
      project.final,
      project.subtitled,
    ]);
    if (before !== after || wasBusy !== this.busy) this.render();
    else this.renderStatus();
  }
  mark(scope) {
    this.draft.mark(scope);
    this.renderSaveBar();
  }
  async canLeave() {
    if (this.saving) {
      this.services.toast("正在保存，完成后即可切换项目。");
      return false;
    }
    if (!this.draft?.dirty.size) return true;
    const choice = await dialog(
      "当前项目还有未保存修改",
      `未保存：${[...this.draft.dirty].map((s) => SCOPES[s]).join("、")}。保存后再切换，或放弃本次修改。`,
      [
        { label: "继续编辑", value: null },
        { label: "放弃修改", value: "discard" },
        { label: "保存并切换", value: "save", primary: true },
      ],
    );
    if (choice === "discard") {
      this.draft.discard();
      this.rawStoryJson = null;
      this.invalidBindings.clear();
      this.renderSaveBar();
      return true;
    }
    if (choice === "save") return this.saveAll();
    return false;
  }
  async save(scope) {
    const { value, revision } = this.draft.snapshot(scope),
      pid = this.current.id;
    if (scope === "story") {
      if (this.rawStoryJson !== null)
        throw Error(
          "完整分镜 JSON 有未应用的修改，请先点击“应用 JSON 到编辑区”。",
        );
      if (this.invalidBindings.size)
        throw Error("素材绑定 JSON 格式有误，请修正后保存。");
      if (!value?.shots?.length) throw Error("至少保留一个分镜。");
      for (const [index, shot] of value.shots.entries())
        if (shot.use_previous_last_frame) {
          const issue = continuationIssue(value.shots, index);
          if (issue)
            throw Error(`镜头 ${index + 1} 无法启用首帧功能：${issue}`);
        }
      await api("/api/story", { id: pid, story: value });
    } else if (scope === "outline") {
      let outline;
      try {
        outline = JSON.parse(value);
      } catch {
        throw Error("大纲 JSON 格式有误。请检查引号、逗号和括号。");
      }
      await api(`/api/projects/${pid}/outline`, outline);
    } else await api(`/api/projects/${pid}/settings`, value);
    const next = await api("/api/project/" + pid);
    this.draft.commit(scope, revision, next);
  }
  async saveAll() {
    if (this.saving) return false;
    const invalid = this.container.querySelector(
      "input:invalid,select:invalid,textarea:invalid",
    );
    if (invalid) {
      for (
        let parent = invalid.parentElement;
        parent;
        parent = parent.parentElement
      )
        if (parent.tagName === "DETAILS") parent.open = true;
      invalid.reportValidity();
      this.services.toast("请先修正标出的输入，再保存。", true);
      return false;
    }
    if (this.busy) {
      this.services.toast("任务执行中，请停止后保存编辑。", true);
      return false;
    }
    this.saving = true;
    this.renderSaveBar();
    try {
      for (const scope of ["outline", "settings", "story"])
        if (this.draft.dirty.has(scope)) await this.save(scope);
      this.render();
      await this.services.refresh();
      if (this.draft.dirty.size) {
        this.services.toast(
          "已保存提交时的版本；之后输入的修改仍保留，请再次保存。",
        );
        return false;
      }
      this.services.toast("修改已保存。受影响的提示词和视频会在继续时更新。");
      return true;
    } catch (error) {
      this.services.toast(error.message, true);
      return false;
    } finally {
      this.saving = false;
      this.renderSaveBar();
    }
  }
  async run(stage, force = false, uid) {
    if (this.busy) throw Error("这个项目已有排队或执行中的任务。");
    if (this.draft.dirty.size && !(await this.saveAll())) return;
    if (force) {
      const choice = await dialog(
        uid ? "重写这个镜头？" : "重新生成这个阶段？",
        "未锁定的内容将重新生成。已保存版本和历史视频会保留，可在记录中查看。",
        [
          { label: "取消", value: null },
          { label: "开始重新生成", value: true, primary: true },
        ],
      );
      if (!choice) return;
    }
    if (uid)
      await api(`/api/projects/${this.current.id}/shots/${uid}/regenerate`, {
        kind: stage === "prompt" ? "prompt" : "video",
      });
    else
      await api(`/api/projects/${this.current.id}/stage/${stage}`, { force });
    this.services.toast("任务已排队，可以继续查看内容。");
    await this.services.refresh();
  }
  renderSaveBar() {
    const bar = document.getElementById("save-bar"),
      dirty = this.draft?.dirty;
    bar.hidden =
      !dirty?.size ||
      document.getElementById("projects").classList.contains("hidden");
    if (!dirty?.size) return;
    bar.replaceChildren(
      el(
        "p",
        {},
        "有未保存修改",
        el(
          "small",
          {},
          [...dirty].map((s) => SCOPES[s]).join(" · ") + " · Ctrl / ⌘ + S 保存",
        ),
      ),
      el(
        "div",
        { class: "actions" },
        this.button(
          "放弃",
          async () => {
            const choice = await dialog(
              "放弃当前修改？",
              "将恢复上次保存的内容。已保存的项目和视频不受影响。",
              [
                { label: "继续编辑", value: null },
                { label: "放弃修改", value: true, danger: true },
              ],
            );
            if (choice) {
              this.draft.discard();
              this.rawStoryJson = null;
              this.invalidBindings.clear();
              this.render();
            }
          },
          false,
          { class: "quiet", disabled: this.saving },
        ),
        this.button(
          this.saving ? "保存中…" : "保存全部",
          () => this.saveAll(),
          true,
          { disabled: this.saving || this.busy },
        ),
      ),
    );
  }
  renderStatus() {
    const root = this.container.querySelector("#project-status");
    if (!root) return;
    const p = this.current,
      status = projectStatus(p, this.services.jobs()),
      shots = p.story?.shots || [],
      done = shots.filter((s) => shotRecord(p, s).status === "done").length;
    root.replaceChildren(
      el(
        "div",
        { class: "status-top" },
        badge(status),
        el(
          "span",
          { class: "workspace-meta" },
          shots.length
            ? `${done} / ${shots.length} 镜头已完成`
            : "从文字规划开始",
        ),
      ),
      el(
        "p",
        { class: status === "error" ? "notice error" : "status-message" },
        p.state.message || "准备好后开始生成。",
      ),
    );
    const completed = {
      outline: !!p.outline_result || p.settings.input_mode === "storyboard",
      storyboard: !!p.story,
      prompt: !!shots.length && shots.every((s) => !!s.prompt),
      render: !!p.final,
    };
    const active = p.state.current_stage,
      activeStage = [
        "encoding",
        "sampling",
        "decoding",
        "first_frame",
        "assembling",
      ].includes(active)
        ? "render"
        : active;
    root.append(
      el(
        "div",
        { class: "pipeline" },
        ["outline", "storyboard", "prompt", "render"].map((stage, i) =>
          el(
            "div",
            {
              class:
                "pipeline-step" +
                (this.busy && activeStage === stage
                  ? " current"
                  : completed[stage]
                    ? " done"
                    : ""),
            },
            `${i + 1}. ${["大纲", "分镜", "提示词", "成片"][i]}`,
          ),
        ),
      ),
    );
  }
  render() {
    const box = this.container,
      p = this.current;
    if (!p) return;
    this.renderedBusy = this.busy;
    box.replaceChildren();
    const controls = el("div", { class: "workspace-actions" });
    if (this.busy)
      controls.append(
        this.button("完成当前镜头后停止", async () => {
          this.services.toast((await api("/api/stop", { id: p.id })).message);
          await this.services.refresh();
        }),
        this.button(
          "立即停止",
          async () => {
            const choice = await dialog(
              "立即停止当前任务？",
              "当前镜头可能需要重新计算。已完成的视频会保留。",
              [
                { label: "继续生成", value: null },
                { label: "立即停止", value: true, danger: true },
              ],
            );
            if (choice) {
              this.services.toast(
                (await api("/api/stop", { id: p.id, immediate: true })).message,
              );
              await this.services.refresh();
            }
          },
          false,
          { class: "danger" },
        ),
      );
    else
      controls.append(
        this.button(
          p.final
            ? "继续 / 更新视频"
            : p.story
              ? "生成 / 继续视频"
              : "开始规划",
          () => this.run(p.story ? "render" : "all"),
          true,
        ),
      );
    box.append(
      el(
        "div",
        { class: "workspace-heading" },
        el(
          "div",
          {},
          el(
            "p",
            { class: "eyebrow" },
            p.episode?.series_title
              ? `第 ${p.episode.number} 集 · ${p.episode.series_title}`
              : "PROJECT WORKSPACE",
          ),
          el(
            "h1",
            {},
            this.draft.data.story?.title ||
              p.title ||
              p.outline_result?.title ||
              "新的故事",
          ),
        ),
        controls,
      ),
      el("div", { id: "project-status", class: "project-status" }),
    );
    this.renderStatus();
    box.append(
      tabs(
        PANEL_NAMES,
        this.panel,
        (id) => {
          this.panel = id;
          this.render();
        },
        "项目内容",
      ),
    );
    const panel = el("section", {
      class: "workspace-panel",
      role: "tabpanel",
      "aria-label": PANEL_NAMES.find((item) => item.id === this.panel)?.label,
    });
    box.append(panel);
    ({
      story: () => this.renderStoryboard(panel),
      media: () => this.renderMedia(panel),
      outline: () => this.renderOutline(panel),
      settings: () => this.renderSettings(panel),
      assets: () => this.renderAssets(panel),
      records: () => this.renderRecords(panel),
    })[this.panel]();
    this.renderSaveBar();
  }
  details(id, label, ...children) {
    const item = el(
      "details",
      { open: this.openDetails.has(id) },
      el("summary", {}, label),
      ...children,
    );
    item.addEventListener("toggle", () => {
      if (item.open) this.openDetails.add(id);
      else this.openDetails.delete(id);
    });
    return item;
  }
  renderSettings(box) {
    const read = optionsEditor(
      box,
      this.services.config(),
      this.services.presets().builtin,
      this.services.skills(),
      this.draft.data.settings,
      (values) => {
        this.draft.data.settings = values;
        this.mark("settings");
      },
    );
    const execution = select(
      [
        { value: "review", label: "逐阶段检查" },
        { value: "auto", label: "全自动生成成片" },
      ],
      this.draft.data.settings.execution_mode,
    );
    execution.onchange = () => {
      this.draft.data.settings = { ...read(), execution_mode: execution.value };
      this.mark("settings");
    };
    box.prepend(field("创作方式", execution));
    if (this.busy) {
      for (const control of box.querySelectorAll("input,select,textarea"))
        control.disabled = true;
      box.prepend(
        el(
          "div",
          { class: "notice compact" },
          "任务执行中，设置暂时只读。停止后即可编辑。",
        ),
      );
    }
    box.append(
      el(
        "p",
        { class: "muted" },
        "修改后点击下方“保存全部”。切换分区会保留尚未保存的内容。",
      ),
    );
  }
  renderOutline(box) {
    const p = this.current;
    box.append(
      el("h2", {}, "原始故事"),
      el(
        "p",
        { class: "muted" },
        "你提供的输入保留在这里，AI 以它为创作依据。",
      ),
      el("textarea", {
        rows: 6,
        value: p.outline,
        readOnly: true,
        "aria-label": "原始故事",
      }),
    );
    if (!p.outline_result) {
      box.append(
        el(
          "div",
          { class: "notice" },
          p.settings.input_mode === "storyboard"
            ? "已有分镜无需先生成大纲，可以直接生成提示词与视频。"
            : "还没有生成大纲。开始规划后会出现在这里。",
        ),
      );
      return;
    }
    box.append(
      el("h3", {}, "大纲"),
      el(
        "p",
        { class: "muted" },
        "编辑 JSON 中的内容后保存，未锁定的下游分镜会在继续时重建。",
      ),
      el("textarea", {
        class: "code-editor",
        rows: 12,
        value: this.draft.data.outline,
        readOnly: this.busy,
        "aria-label": "编辑大纲 JSON",
        oninput: (event) => {
          this.draft.data.outline = event.target.value;
          this.mark("outline");
        },
      }),
      this.button("重新生成大纲", () => this.run("outline", true), false, {
        disabled: this.busy,
      }),
    );
  }
  renderStoryboard(box) {
    const story = this.draft.data.story;
    if (!story) {
      box.append(
        empty(
          "分镜还没开始",
          "先完成文字规划，AI 分镜人会把故事拆成镜头。",
          this.button("生成分镜", () => this.run("all"), true, {
            disabled: this.busy,
          }),
        ),
      );
      return;
    }
    if (!story.shots.some((s) => s.uid === this.selectedShot))
      this.selectedShot = story.shots[0]?.uid;
    const toolbar = el(
      "div",
      { class: "section-toolbar" },
      el(
        "span",
        { class: "muted" },
        `${story.shots.length} 个镜头 · 选择一个镜头，专注编辑`,
      ),
      this.button(
        "增加镜头",
        () => {
          const shot = {
            id: story.shots.length + 1,
            uid: crypto.randomUUID().replaceAll("-", "").slice(0, 20),
            scene: "",
            summary: "",
            camera: "",
            action: "",
            duration: 4,
            characters: [],
            dialogue: [],
            prompt: "",
            locked: false,
            mode: "auto",
            bindings: {},
            use_previous_last_frame: false,
          };
          story.shots.push(shot);
          this.selectedShot = shot.uid;
          this.mark("story");
          this.render();
        },
        false,
        { disabled: this.busy },
      ),
    );
    box.append(toolbar);
    const layout = el("div", { class: "shot-layout" }),
      nav = el("div", { class: "shot-nav", "aria-label": "镜头列表" }),
      editor = el("div", { class: "shot-editor" });
    layout.append(nav, editor);
    box.append(layout);
    story.shots.forEach((shot, index) =>
      nav.append(
        this.button(
          "",
          () => {
            this.selectedShot = shot.uid;
            this.render();
          },
          false,
          {
            class: shot.uid === this.selectedShot ? "selected" : "",
            "aria-label": `编辑镜头 ${index + 1}`,
          },
        ),
      ),
    );
    [...nav.children].forEach((node, index) => {
      const shot = story.shots[index],
        record = shotRecord(this.current, shot);
      node.append(
        el(
          "span",
          { class: "shot-nav-title" },
          `镜头 ${String(index + 1).padStart(2, "0")}`,
          badge(record.status || "new"),
        ),
        el(
          "span",
          { class: "shot-nav-summary" },
          shot.summary || "填写这个镜头的故事",
        ),
        el(
          "small",
          { class: "muted" },
          `${shot.duration} 秒${shot.locked ? " · 已锁定" : ""}${shot.use_previous_last_frame ? " · 首帧接续" : ""}`,
        ),
      );
    });
    const index = story.shots.findIndex((s) => s.uid === this.selectedShot),
      shot = story.shots[index];
    if (!shot) return;
    const record = shotRecord(this.current, shot),
      locked = shot.locked,
      readOnly = this.busy || locked;
    const mark = () => this.mark("story");
    const area = (key, label, rows = 3) =>
      field(
        label,
        el("textarea", {
          rows,
          value: shot[key] || "",
          disabled: readOnly,
          oninput: (event) => {
            shot[key] = event.target.value;
            mark();
            if (key === "scene" || key === "continuity_group") updateFrame();
          },
        }),
      );
    const move = (delta) => {
      const target = index + delta;
      if (target < 0 || target >= story.shots.length) return;
      [story.shots[index], story.shots[target]] = [
        story.shots[target],
        story.shots[index],
      ];
      mark();
      this.render();
    };
    const tools = el(
      "div",
      { class: "shot-tools" },
      this.button("上移", () => move(-1), false, {
        disabled: this.busy || index === 0,
      }),
      this.button("下移", () => move(1), false, {
        disabled: this.busy || index === story.shots.length - 1,
      }),
      this.button(
        "删除",
        async () => {
          const choice = await dialog(
            `移除镜头 ${index + 1}？`,
            "这次修改保存前可放弃；已保存的历史版本和旧视频仍会保留。相邻镜头的首帧接续需要重新检查。",
            [
              { label: "保留镜头", value: null },
              { label: "移除镜头", value: true, danger: true },
            ],
          );
          if (choice) {
            story.shots.splice(index, 1);
            this.selectedShot =
              story.shots[Math.min(index, story.shots.length - 1)]?.uid;
            mark();
            this.render();
          }
        },
        false,
        {
          disabled: this.busy || locked || story.shots.length === 1,
          class: "danger",
        },
      ),
    );
    editor.append(
      el(
        "div",
        { class: "shot-heading" },
        el("h2", {}, `镜头 ${String(index + 1).padStart(2, "0")}`),
        tools,
      ),
    );
    const lock = el("input", {
      type: "checkbox",
      checked: locked,
      disabled: this.busy,
      onchange: (event) => {
        shot.locked = event.target.checked;
        mark();
        this.render();
      },
    });
    editor.append(el("label", { class: "check" }, lock, "锁定这个镜头"));
    if (locked)
      editor.append(
        el(
          "p",
          { class: "field-help" },
          "已锁定。先解除锁定，再修改内容或重新生成。",
        ),
      );
    const duration = el("input", {
      type: "number",
      min: 4,
      max: this.draft.data.settings.allow_long_shots ? 15 : 8,
      step: 0.1,
      value: shot.duration,
      disabled: readOnly,
      oninput: (event) => {
        shot.duration = Number(event.target.value);
        mark();
      },
    });
    editor.append(
      el(
        "div",
        { class: "grid" },
        area("scene", "场景", 2),
        field("镜头时长（秒）", duration),
      ),
      area("summary", "这个镜头讲什么", 2),
      area("action", "人物动作与状态", 3),
      area("camera", "景别与镜头运动", 2),
    );
    const cast = el(
      "select",
      {
        multiple: true,
        size: Math.min(4, Math.max(2, story.characters.length)),
        disabled: readOnly,
      },
      story.characters.map((c) =>
        el(
          "option",
          { value: c.id, selected: shot.characters.includes(c.id) },
          c.name,
        ),
      ),
    );
    cast.onchange = () => {
      shot.characters = [...cast.selectedOptions].map((o) => o.value);
      mark();
    };
    const dialogue = el("textarea", {
      rows: 3,
      disabled: readOnly,
      value: shot.dialogue.map((l) => `${l.speaker}: ${l.text}`).join("\n"),
      placeholder: "人物名：一句对白\n没有对白可以留空",
      oninput: (event) => {
        shot.dialogue = event.target.value
          .split("\n")
          .filter((s) => s.trim())
          .map((line) => {
            const n = line.search(/[:：]/);
            return {
              speaker: n < 0 ? "" : line.slice(0, n).trim(),
              text: n < 0 ? line : line.slice(n + 1).trim(),
            };
          });
        mark();
      },
    });
    editor.append(
      el(
        "div",
        { class: "grid" },
        field(
          "出场人物",
          cast,
          story.characters.length
            ? "可多选，仅选择本镜出现的人物。"
            : "人物设定可在“素材”或完整分镜 JSON 中补充。",
        ),
        field("对白", dialogue),
      ),
    );
    const frame = el("input", {
      type: "checkbox",
      checked: shot.use_previous_last_frame === true,
      disabled: readOnly || (index === 0 && !shot.use_previous_last_frame),
      "aria-label": `镜头 ${index + 1} 首帧功能`,
      onchange: (event) => {
        shot.use_previous_last_frame = event.target.checked;
        mark();
        updateFrame();
      },
    });
    const frameHelp = el("p", { class: "continuity-help" }),
      frameCard = el(
        "div",
        { class: "continuity-card" },
        el(
          "div",
          {},
          el(
            "label",
            { class: "switch-card" },
            frame,
            el(
              "span",
              {},
              el("strong", {}, "首帧功能"),
              el("small", {}, "从上一镜头的实际末帧继续生成"),
            ),
          ),
          frameHelp,
        ),
      );
    if (shot.use_previous_last_frame && record.first_frame?.file)
      frameCard.append(
        el("img", {
          class: "asset-thumb",
          src: mediaUrl(this.current.id, record.first_frame.file),
          alt: "上一镜头末帧预览",
        }),
      );
    editor.append(frameCard);
    const mode = select(MODES, shot.mode || "auto");
    mode.onchange = () => {
      shot.mode = mode.value;
      mark();
    };
    const slots = el("div", { class: "grid" });
    for (const [slot, label, type, multiple] of [
      ["first_frame", "手动首帧", "image", false],
      ["last_frame", "尾帧", "image", false],
      ["images", "人物 / 图片参考", "image", true],
      ["videos", "视频参考", "video", true],
      ["audios", "音频参考", "audio", true],
    ]) {
      const selected = multiple
          ? shot.bindings?.[slot] || []
          : [shot.bindings?.[slot]],
        pick = el(
          "select",
          { multiple, size: multiple ? 2 : 1 },
          ...(!multiple ? [el("option", { value: "" }, "不绑定")] : []),
          ...Object.values(this.current.assets)
            .filter((a) => a.type === type)
            .map((a) =>
              el(
                "option",
                { value: a.id, selected: selected.includes(a.id) },
                a.name,
              ),
            ),
        );
      pick.onchange = () => {
        shot.bindings ??= {};
        const ids = [...pick.selectedOptions]
          .map((o) => o.value)
          .filter(Boolean);
        if (ids.length) shot.bindings[slot] = multiple ? ids : ids[0];
        else delete shot.bindings[slot];
        mark();
      };
      slots.append(field(label, pick));
    }
    function updateFrame() {
      const enabled = shot.use_previous_last_frame === true,
        issue = continuationIssue(story.shots, index);
      mode.disabled = readOnly || enabled;
      mode.value = enabled ? "I2VA" : shot.mode || "auto";
      const preview = frameCard.querySelector("img");
      if (preview) preview.hidden = !enabled;
      for (const input of slots.querySelectorAll("select"))
        input.disabled = readOnly || enabled;
      frameHelp.textContent = enabled
        ? issue
          ? "无法接续：" + issue
          : `自动使用镜头 ${index} 的末帧，以 I2VA 生成。${shot.first_frame_reason ? " AI 判断：" + shot.first_frame_reason : ""}`
        : index === 0
          ? "第一镜没有可接续的前镜。"
          : "默认关闭，由 AI 分镜人判断是否适合同场景连续动作。";
      frameHelp.classList.toggle("error-text", enabled && !!issue);
    }
    updateFrame();
    const prompt = el("textarea", {
      rows: 9,
      value: shot.prompt,
      class: "code-editor",
      disabled: readOnly,
      "aria-label": `镜头 ${index + 1} H3 提示词`,
      oninput: (event) => {
        shot.prompt = event.target.value;
        mark();
      },
    });
    editor.append(
      this.details(
        "prompt",
        "H3 提示词与参考素材",
        field("生成模式", mode),
        slots,
        field("完整提示词", prompt),
        el(
          "p",
          { class: "field-help" },
          "修改剧情或素材后，旧自动提示词将在保存时失效。主动编辑的提示词会保留。",
        ),
      ),
    );
    const bindings = el("textarea", {
      rows: 4,
      value:
        this.invalidBindings.get(shot.uid) ??
        JSON.stringify(shot.bindings || {}, null, 2),
      disabled: readOnly,
      class: "code-editor",
      "aria-label": "高级素材绑定 JSON",
      oninput: (event) => {
        mark();
        try {
          shot.bindings = JSON.parse(event.target.value);
          this.invalidBindings.delete(shot.uid);
          bindings.setCustomValidity("");
        } catch {
          this.invalidBindings.set(shot.uid, event.target.value);
          bindings.setCustomValidity("素材绑定 JSON 格式有误。");
        }
      },
    });
    editor.append(
      this.details(
        "advanced-shot",
        "连续段、种子与高级绑定",
        area("continuity_group", "连续段标识", 1),
        field(
          "单镜种子（空白继承项目）",
          el("input", {
            type: "number",
            min: 0,
            value: shot.seed ?? "",
            disabled: readOnly,
            oninput: (event) => {
              shot.seed =
                event.target.value === "" ? null : Number(event.target.value);
              mark();
            },
          }),
        ),
        field("素材绑定 JSON", bindings),
      ),
    );
    editor.append(
      el(
        "div",
        { class: "actions" },
        this.button(
          "重写此提示词",
          () => this.run("prompt", true, shot.uid),
          false,
          { disabled: readOnly },
        ),
        this.button(
          "换种子重生成",
          () => this.run("render", true, shot.uid),
          false,
          { disabled: readOnly },
        ),
      ),
    );
    if (record.status === "done")
      editor.append(
        el("video", {
          class: "shot-preview",
          controls: true,
          preload: "none",
          src: mediaUrl(this.current.id, clipPath(record, shot)),
        }),
      );
    if (record.timings)
      editor.append(
        el(
          "p",
          { class: "field-help" },
          Object.entries(record.timings)
            .map(
              ([phase, value]) =>
                `${STAGES[phase] || phase} ${value.seconds} 秒`,
            )
            .join(" · "),
        ),
      );
    box.append(
      this.details("story-json", "完整分镜 JSON", this.storyJsonEditor()),
      el(
        "div",
        { class: "actions" },
        this.button("重新生成分镜", () => this.run("storyboard", true), false, {
          disabled: this.busy,
        }),
        this.button("导出分镜", () =>
          download("分镜.json", this.draft.data.story),
        ),
      ),
    );
  }
  storyJsonEditor() {
    const editor = el("textarea", {
      class: "code-editor",
      rows: 15,
      value:
        this.rawStoryJson ?? JSON.stringify(this.draft.data.story, null, 2),
      disabled: this.busy,
      "aria-label": "完整分镜 JSON",
      oninput: (event) => {
        this.rawStoryJson = event.target.value;
        this.mark("story");
      },
    });
    const apply = this.button(
      "应用 JSON 到编辑区",
      async () => {
        let story;
        try {
          story = JSON.parse(editor.value);
        } catch {
          throw Error("分镜 JSON 格式有误，请检查后再应用。");
        }
        if (!story.title || !Array.isArray(story.shots) || !story.shots.length)
          throw Error("分镜需要标题和至少一个镜头。");
        const revision = this.draft.revisions.story,
          draft = this.draft,
          pid = this.current.id;
        const normalized = await api(`/api/projects/${pid}/validate-story`, {
          story,
        });
        if (draft !== this.draft || revision !== this.draft.revisions.story)
          throw Error("验证时又有新修改，请再次应用 JSON。");
        this.draft.data.story = normalized;
        this.rawStoryJson = null;
        this.invalidBindings.clear();
        this.mark("story");
        this.render();
        this.services.toast("JSON 已应用到编辑区，点击“保存全部”写入项目。");
      },
      false,
      { disabled: this.busy },
    );
    return el("div", {}, editor, apply);
  }
  renderMedia(box) {
    const p = this.current;
    if (p.final) {
      box.append(
        el("h2", {}, "完整成片"),
        el("video", {
          controls: true,
          preload: "metadata",
          src: mediaUrl(p.id, p.subtitled ? "成片_字幕版.mp4" : "成片.mp4"),
        }),
        el(
          "div",
          { class: "actions" },
          el(
            "a",
            { class: "button", href: mediaUrl(p.id, "成片.mp4"), download: "" },
            "下载无字幕成片",
          ),
          p.subtitled
            ? el(
                "a",
                {
                  class: "button",
                  href: mediaUrl(p.id, "成片_字幕版.mp4"),
                  download: "",
                },
                "下载字幕版",
              )
            : null,
          el(
            "a",
            { class: "button", href: mediaUrl(p.id, "字幕.srt"), download: "" },
            "下载 SRT",
          ),
        ),
      );
    } else
      box.append(
        el(
          "div",
          { class: "notice" },
          "完整成片尚未生成，已完成镜头可在下面单独播放。",
        ),
      );
    const grid = el("div", { class: "media-grid" });
    box.append(grid);
    for (const shot of p.story?.shots || []) {
      const record = shotRecord(p, shot),
        card = el(
          "div",
          { class: "media-card" },
          badge(record.status || "new"),
          el("h3", {}, `镜头 ${shot.id}`),
        );
      card.append(
        record.status === "done"
          ? el("video", {
              controls: true,
              preload: "none",
              src: mediaUrl(p.id, clipPath(record, shot)),
            })
          : el("div", { class: "media-placeholder" }, "等待生成"),
        el("p", { class: "field-help" }, shot.summary),
      );
      grid.append(card);
    }
    box.append(
      el(
        "div",
        { class: "actions" },
        this.button(
          "导出项目迁移包",
          async () => {
            if (!(await this.canLeave())) return;
            const value = await api("/api/export", {
              projects: [p.id],
              include_videos: true,
            });
            el("a", { href: value.url, download: "" }).click();
            this.services.toast(
              "迁移包已生成，包含素材与视频，已排除认证信息。",
            );
          },
          false,
          { disabled: this.busy },
        ),
      ),
    );
  }
  renderAssets(box) {
    const p = this.current,
      story = this.draft.data.story;
    box.append(
      el("h2", {}, "参考素材"),
      el(
        "p",
        { class: "muted" },
        "添加人物图、短视频或声音，然后在镜头的参考素材中选择。单文件最多 8MB。",
      ),
    );
    const cast = select(
        [
          { value: "", label: "不绑定人物" },
          ...(story?.characters || []).map((c) => ({
            value: c.id,
            label: c.name,
          })),
        ],
        "",
      ),
      upload = el("input", {
        type: "file",
        accept:
          "image/png,image/jpeg,image/webp,video/mp4,video/webm,video/quicktime,audio/wav,audio/mpeg,audio/flac,audio/mp4,audio/ogg",
        disabled: this.busy,
      });
    box.append(
      el(
        "div",
        { class: "grid" },
        field("用于人物身份图", cast),
        field("选择参考素材", upload),
      ),
      this.button(
        "添加素材",
        async () => {
          const file = upload.files[0];
          if (!file) throw Error("请先选择参考素材。");
          if (file.size > 8000000)
            throw Error("单个参考素材最多 8MB，请使用更小的图片或片段。");
          const data = await new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = () => resolve(reader.result.split(",")[1]);
            reader.onerror = () => reject(Error("读取文件失败，请重新选择。"));
            reader.readAsDataURL(file);
          });
          const type = file.type.startsWith("video")
            ? "video"
            : file.type.startsWith("audio")
              ? "audio"
              : "image";
          await api(`/api/projects/${p.id}/assets`, {
            data,
            name: file.name,
            type,
            character: cast.value,
          });
          this.update(await api("/api/project/" + p.id));
          this.services.toast("素材已添加，可在分镜中绑定。");
        },
        true,
        { disabled: this.busy },
      ),
    );
    for (const asset of Object.values(p.assets))
      box.append(
        el(
          "div",
          { class: "asset-row" },
          asset.type === "image"
            ? el("img", {
                class: "asset-thumb",
                src: mediaUrl(p.id, asset.file),
                alt: asset.name,
              })
            : asset.type === "video"
              ? el("video", {
                  class: "asset-thumb",
                  controls: true,
                  preload: "none",
                  src: mediaUrl(p.id, asset.file),
                })
              : el("audio", {
                  controls: true,
                  preload: "none",
                  src: mediaUrl(p.id, asset.file),
                }),
          el(
            "div",
            {},
            el("strong", {}, asset.name),
            el(
              "p",
              {},
              asset.character ? "人物身份图 · " + asset.character : "参考素材",
            ),
            this.details(
              "asset-" + asset.id,
              "素材编号",
              el("pre", {}, asset.id),
            ),
          ),
        ),
      );
    for (const [cid, ref] of Object.entries(p.references || {}))
      if (ref.local_file)
        box.append(
          el(
            "div",
            { class: "asset-row" },
            el("img", {
              class: "asset-thumb",
              src: mediaUrl(p.id, ref.local_file),
              alt: cid + " 自动参考",
            }),
            el(
              "div",
              {},
              el("strong", {}, "自动人物参考"),
              el("p", {}, `${cid} · 来自镜头 ${ref.shot_id}`),
            ),
          ),
        );
    if (story)
      box.append(
        this.details(
          "cast-json",
          "人物、场景和道具设定",
          el(
            "pre",
            {},
            JSON.stringify(
              {
                characters: story.characters,
                scenes: story.scenes,
                props: story.props,
              },
              null,
              2,
            ),
          ),
          el(
            "p",
            { class: "muted" },
            "在分镜页的完整 JSON 编辑中修改这些设定。",
          ),
        ),
      );
  }
  renderRecords(box) {
    const p = this.current;
    box.append(
      el("h2", {}, "阶段与版本"),
      el(
        "p",
        { class: "muted" },
        "保存的版本、实际模型请求与媒体验收都在这里。",
      ),
    );
    const versions = el(
      "div",
      { class: "table-wrap" },
      el(
        "table",
        {},
        el(
          "thead",
          {},
          el(
            "tr",
            {},
            ["阶段", "保存时间", "版本编号"].map((t) => el("th", {}, t)),
          ),
        ),
        el(
          "tbody",
          {},
          p.versions
            .slice()
            .reverse()
            .map((v) =>
              el(
                "tr",
                {},
                el("td", {}, STAGES[v.stage] || v.stage),
                el("td", {}, v.created_at),
                el("td", {}, v.id),
              ),
            ),
        ),
      ),
    );
    box.append(versions);
    const records = el(
      "div",
      {},
      el("p", { class: "muted" }, "正在读取请求与媒体记录…"),
    );
    box.append(records);
    this.services.act(async () => {
      const data = await api(`/api/projects/${p.id}/records`),
        pick = select(
          [
            { value: "", label: "选择一条模型请求" },
            ...data.requests.map((r) => ({ value: r.file, label: r.file })),
          ],
          "",
        ),
        output = el("pre");
      pick.onchange = () =>
        this.services.act(async () => {
          output.textContent = pick.value
            ? JSON.stringify(
                await api(`/api/projects/${p.id}/requests/${pick.value}`),
                null,
                2,
              )
            : "";
        });
      records.replaceChildren(
        field("模型请求与响应", pick),
        output,
        this.details(
          "renderer",
          "实际模型版本与媒体检查",
          el(
            "pre",
            {},
            JSON.stringify(
              { renderer: data.renderer, media: data.media },
              null,
              2,
            ),
          ),
        ),
      );
    });
  }
}
