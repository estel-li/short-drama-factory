import { api, el, field, select, download } from "./api.js";
import { optionsEditor } from "./options.js";
import { Workspace } from "./project.js";
import { STAGES, isBusy, projectStatus } from "./state.js";
import { badge, dialog, empty, icon, tabs } from "./ui.js";
const $ = (id) => document.getElementById(id);
let config,
  presets,
  skills,
  projectList = [],
  seriesList = [],
  jobs = [],
  page = "projects",
  readNew,
  readSeries,
  currentSeries = null,
  selectedEpisodes = new Set();
let modelCatalog = null,
  plannedInstall = null,
  pollTimer,
  polling = null,
  previewTimer,
  previewVersion = 0,
  toastTimer,
  skillPackage = null,
  skillDirty = false,
  skillRawDirty = false,
  environmentTab = "provider";
let projectListStamp = "",
  seriesListStamp = "",
  jobsStamp = "",
  newFormTouched = false,
  seriesFormTouched = false;
let userNavigated = false;
let skillRevision = 0,
  skillLoadVersion = 0,
  appliedSkillFilter = "all",
  skillChoice = "";
const providerDrafts = new Map();
let environmentDraft = null,
  environmentRevision = 0,
  configSaving = false,
  comfyAuthDraft = "";
const formLocks = new Set();
const workspace = new Workspace($("workspace"), {
  config: () => config,
  presets: () => presets,
  skills: () => skills,
  jobs: () => jobs,
  act,
  toast,
  refresh,
});
function toast(message, error = false) {
  const box = $("toast");
  box.hidden = false;
  box.classList.toggle("error", error);
  box.setAttribute("role", error ? "alert" : "status");
  box.replaceChildren(
    icon(error ? "alert" : "check"),
    el("p", {}, message),
    el(
      "button",
      { "aria-label": "关闭提示", onclick: () => (box.hidden = true) },
      icon("close"),
    ),
  );
  clearTimeout(toastTimer);
  if (!error) toastTimer = setTimeout(() => (box.hidden = true), 5000);
}
function formError(form, message = "") {
  const target = $(
    form?.id === "create-form"
      ? "create-error"
      : form?.id === "series-form"
        ? "series-error"
        : "skill-error",
  );
  if (target) {
    target.hidden = !message;
    target.textContent = message;
  }
}
async function act(work, button) {
  const form = button?.form;
  if (button?.disabled || (form && formLocks.has(form))) return;
  const wasDisabled = button?.disabled,
    nodes = form
      ? [...form.querySelectorAll("button")].map((node) => [
          node,
          node.disabled,
        ])
      : [];
  if (form) {
    formLocks.add(form);
    for (const [node] of nodes) node.disabled = true;
    formError(form);
  }
  if (button) {
    button.disabled = true;
    button.setAttribute("aria-busy", "true");
  }
  try {
    return await work();
  } catch (error) {
    if (form) formError(form, error.message);
    toast(error.message, true);
    return false;
  } finally {
    if (form) {
      formLocks.delete(form);
      for (const [node, disabled] of nodes) node.disabled = disabled;
    }
    if (button) {
      button.disabled = !!wasDisabled;
      button.removeAttribute("aria-busy");
    }
  }
}
function setPage(name) {
  page = name;
  for (const node of document.querySelectorAll(".page"))
    node.classList.toggle("hidden", node.id !== name);
  for (const node of document.querySelectorAll("[data-tab]")) {
    const active = node.dataset.tab === name;
    node.classList.toggle("active", active);
    if (active) node.setAttribute("aria-current", "page");
    else node.removeAttribute("aria-current");
  }
  $("save-bar").hidden = name !== "projects" || !workspace.draft?.dirty.size;
  if (name === "jobs") renderJobs();
  if (name === "series" && !seriesList.length && !currentSeries)
    $("series-create").open = true;
}
for (const node of document.querySelectorAll("[data-icon]"))
  node.append(icon(node.dataset.icon));
for (const node of document.querySelectorAll("[data-tab],[data-open]"))
  node.addEventListener("click", () => {
    userNavigated = true;
    setPage(node.dataset.tab || node.dataset.open);
  });
$("brand-home").onclick = (event) => {
  event.preventDefault();
  setPage("projects");
};
window.addEventListener("beforeunload", (event) => {
  if (
    workspace.draft?.dirty.size ||
    skillDirty ||
    newFormTouched ||
    seriesFormTouched ||
    providerDrafts.size ||
    environmentDraft ||
    comfyAuthDraft ||
    $("hf-token").value
  ) {
    event.preventDefault();
    event.returnValue = "";
  }
});
window.addEventListener("keydown", (event) => {
  if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "s") {
    event.preventDefault();
    if (page === "projects") act(() => workspace.saveAll());
    else if (page === "skills") $("skill-save").click();
  }
});
async function boot() {
  [config, presets, skills] = await Promise.all([
    api("/api/config"),
    api("/api/presets"),
    api("/api/skills"),
  ]);
  readNew = optionsEditor(
    $("new-options"),
    config,
    presets.builtin,
    skills,
    {},
    schedulePreview,
  );
  readSeries = optionsEditor(
    $("series-options"),
    config,
    presets.builtin,
    skills,
    {},
  );
  renderProviders();
  renderEnvironment();
  renderSkills();
  renderEnvironmentTabs();
  await previewDuration(readNew());
  await refresh();
  if (!config.setup_complete && !userNavigated) {
    setPage("providers");
    environmentTab = "comfy";
    renderEnvironmentTabs();
  }
}
function schedulePreview(options) {
  newFormTouched = true;
  clearTimeout(previewTimer);
  previewTimer = setTimeout(() => previewDuration(options), 250);
}
async function previewDuration(options) {
  const version = ++previewVersion;
  try {
    const plan = await api("/api/duration-plan", options);
    if (version !== previewVersion) return;
    $("duration-preview").replaceChildren(
      el(
        "div",
        { class: "preview-stat" },
        "分镜",
        el("strong", {}, `${plan.count} 个`),
      ),
      el(
        "div",
        { class: "preview-stat" },
        "画幅",
        el("strong", {}, options.ratio),
      ),
      el(
        "div",
        { class: "preview-stat" },
        "分配时长",
        el("strong", {}, `${plan.allocated_total} 秒`),
      ),
      el(
        "div",
        { class: "preview-stat" },
        "视频时长",
        el("strong", {}, `约 ${plan.aligned_total} 秒`),
      ),
      el(
        "p",
        { class: "preview-aligned" },
        "H3 按固定帧数对齐，实际成片会略长于请求时长。",
      ),
    );
    $("create-start").disabled = false;
  } catch (error) {
    if (version !== previewVersion) return;
    $("duration-preview").replaceChildren(
      el("div", { class: "notice error" }, error.message),
    );
    $("create-start").disabled = true;
  }
}
function updateCreateInput() {
  const form = $("create-form"),
    mode = form.elements.input_mode.value,
    execution = form.elements.execution_mode.value;
  const hints = {
    idea: [
      "一句话、一个人物或一个冲突，就能开始。",
      "例如：失去声音的女孩，用一把红伞帮陌生人找到回家的路。",
    ],
    outline: [
      "保留你写好的剧情、人物与结局。",
      "人物是谁？遇到了什么冲突？最后发生了什么？",
    ],
    script: [
      "完整剧本中的对白与结局会保留。",
      "粘贴剧本，写明场景、动作、人物和对白。",
    ],
    storyboard: [
      "粘贴包含 title、characters、shots 的分镜 JSON。",
      '{"title":"我的故事","characters":[],"shots":[{"scene":"书房","summary":"一个安静的镜头","duration":4}]}',
    ],
  };
  $("input-help").textContent = hints[mode][0];
  form.elements.input.placeholder = hints[mode][1];
  form.elements.input.spellcheck = mode !== "storyboard";
  $("input-count").textContent =
    `${form.elements.input.value.length.toLocaleString()} / 50,000`;
  $("execution-help").textContent =
    execution === "review"
      ? "先规划，再检查。你可以在各阶段调整内容后继续，适合第一次创作。"
      : "从故事到成片连续执行。模型请求与 GPU 渲染将自动进行。";
}
$("create-form").addEventListener("input", () => {
  newFormTouched = true;
  updateCreateInput();
});
$("create-form").addEventListener("change", updateCreateInput);
async function create(start) {
  const form = $("create-form");
  if (!form.reportValidity()) return;
  if (!(await workspace.canLeave())) return;
  const options = {
      ...readNew(),
      input_mode: form.elements.input_mode.value,
      execution_mode: form.elements.execution_mode.value,
    },
    input = form.elements.input.value;
  if (options.input_mode === "storyboard") {
    try {
      JSON.parse(input);
    } catch {
      throw Error("分镜 JSON 格式有误。请检查引号、逗号和括号。");
    }
  }
  const result = await api("/api/projects", { input, options, start });
  newFormTouched = false;
  await openProject(result.id, true);
  await refresh();
  toast(start ? "故事已创建并加入任务队列。" : "草稿已保存，没有调用模型。");
}
$("create-form").addEventListener("submit", (event) => {
  event.preventDefault();
  act(() => create(true), event.submitter);
});
$("create-draft").onclick = (event) =>
  act(() => create(false), event.currentTarget);
$("save-preset").onclick = (event) =>
  act(async () => {
    const name = $("preset-name").value.trim();
    if (!name) throw Error("给这组设置取一个名字。");
    await api("/api/presets", {
      id: "preset-" + Date.now(),
      name,
      options: readNew(),
    });
    presets = await api("/api/presets");
    renderPersonalPresets();
    toast("个人预设已保存。");
  }, event.currentTarget);
updateCreateInput();
async function openProject(id, guarded = false) {
  if (!guarded && workspace.current?.id !== id && !(await workspace.canLeave()))
    return;
  if (workspace.current?.id === id) {
    setPage("projects");
    return;
  }
  const project = await api("/api/project/" + id);
  workspace.load(project);
  setPage("projects");
  projectListStamp = "";
  renderProjectList();
}
function renderProjectList() {
  const query = $("project-search").value.trim().toLowerCase(),
    filter = $("project-filter").value;
  const list = projectList.filter((project) => {
    const status = projectStatus(project, jobs),
      name = project.title + " " + (project.episode?.series_title || "");
    return (
      name.toLowerCase().includes(query) &&
      (filter === "all" ||
        (filter === "active" && isBusy(status)) ||
        (filter === "complete" && status === "complete") ||
        (filter === "attention" &&
          ["error", "paused", "review"].includes(status)))
    );
  });
  const stamp = JSON.stringify([
    list.map((p) => [p.id, p.title, p.state, p.episode]),
    workspace.current?.id,
    filter,
    query,
  ]);
  if (stamp === projectListStamp) return;
  projectListStamp = stamp;
  $("project-list").replaceChildren(
    ...list.map((project) => {
      const title = project.episode?.series_id
        ? `第 ${project.episode.number} 集 · ${project.episode.plan?.title || project.title}`
        : project.title === project.id
          ? "新的故事"
          : project.title;
      return el(
        "button",
        {
          class:
            "project-item" +
            (workspace.current?.id === project.id ? " selected" : ""),
          "aria-current":
            workspace.current?.id === project.id ? "true" : undefined,
          onclick: () => act(() => openProject(project.id)),
        },
        el("span", { class: "project-name" }, title),
        el(
          "span",
          { class: "project-meta" },
          badge(projectStatus(project, jobs)),
          `${project.state.total_shots || 0} 镜头`,
        ),
      );
    }),
  );
  if (!list.length)
    $("project-list").append(
      el(
        "p",
        { class: "muted" },
        projectList.length
          ? "没有匹配项目，换个关键词或筛选条件。"
          : "还没有项目，点击上方 + 开始一个故事。",
      ),
    );
}
$("project-search").oninput = renderProjectList;
$("project-filter").onchange = renderProjectList;
function renderJobs() {
  const active = jobs.filter((j) =>
      ["queued", "running"].includes(j.status),
    ).length,
    errors = jobs.filter((j) => j.status === "error").length;
  $("job-summary").replaceChildren(
    el(
      "div",
      { class: "job-stats" },
      el("span", {}, el("strong", {}, active), "进行中"),
      el("span", {}, el("strong", {}, errors), "遇到问题"),
      el("span", {}, el("strong", {}, jobs.length), "最近任务"),
    ),
  );
  const filter = $("job-filter").value,
    list = jobs.filter(
      (j) =>
        filter === "all" ||
        (filter === "active" && ["queued", "running"].includes(j.status)) ||
        (filter === "error" && j.status === "error") ||
        (filter === "done" && j.status === "done"),
    );
  const stamp = JSON.stringify([list, projectList.map((p) => [p.id, p.title])]);
  if (stamp === jobsStamp) return;
  jobsStamp = stamp;
  $("jobs-list").replaceChildren(
    ...list.map((job) => {
      const project = projectList.find((p) => p.id === job.project_id),
        card = el(
          "article",
          { class: "job-card" },
          el("div", { class: "job-icon" }, icon("clock")),
          el(
            "div",
            {},
            el("h3", {}, project?.title || STAGES[job.kind] || "任务"),
            el("p", {}, job.message || "等待执行"),
            el(
              "small",
              {},
              `${STAGES[job.kind] || job.kind} · ${job.updated_at} · 已尝试 ${job.attempts} 次`,
            ),
          ),
          badge(job.status),
        );
      if (project)
        card.children[1].append(
          el(
            "div",
            { class: "actions" },
            el(
              "button",
              { onclick: () => act(() => openProject(project.id)) },
              "打开项目",
            ),
          ),
        );
      return card;
    }),
  );
  if (!list.length)
    $("jobs-list").append(
      empty(
        "这里还没有任务",
        filter === "all"
          ? "开始创作后，每一步的进度都会记录在这里。"
          : "当前筛选下没有任务。",
      ),
    );
}
$("job-filter").onchange = () => {
  jobsStamp = "";
  renderJobs();
};
async function refresh() {
  if (polling) return polling;
  polling = (async () => {
    const results = await Promise.allSettled([
      api("/api/projects"),
      api("/api/health"),
      api("/api/jobs"),
      api("/api/series"),
    ]);
    if (results[0].status === "rejected") {
      $("connection-warning").hidden = false;
      return;
    }
    projectList = results[0].value;
    if (results[2].status === "fulfilled") jobs = results[2].value;
    if (results[3].status === "fulfilled") seriesList = results[3].value;
    if (results[1].status === "fulfilled") {
      const health = results[1].value;
      $("health").replaceChildren(
        el("i", { "aria-hidden": "true" }),
        health.comfy ? "生成引擎已连接" : "生成引擎未连接",
      );
      $("health").className = "badge " + (health.comfy ? "success" : "warning");
      $("health").title = health.comfy
        ? "ComfyUI 连接正常"
        : "在模型与环境中连接，开始渲染时也会尝试启动本地引擎。";
    } else {
      $("health").textContent = "连接暂时中断";
      $("health").className = "badge warning";
    }
    $("connection-warning").hidden = results.every(
      (result) => result.status === "fulfilled",
    );
    const count = jobs.filter((j) =>
      ["queued", "running"].includes(j.status),
    ).length;
    $("jobs-count").hidden = !count;
    $("jobs-count").textContent = count;
    renderProjectList();
    renderSeriesList();
    if (page === "jobs") renderJobs();
    if (workspace.current) {
      try {
        workspace.update(await api("/api/project/" + workspace.current.id));
      } catch {
        $("connection-warning").hidden = false;
      }
    }
    if (currentSeries) {
      try {
        const next = await api("/api/series/" + currentSeries.id);
        if (JSON.stringify(next) !== JSON.stringify(currentSeries)) {
          currentSeries = next;
          renderSeries();
        }
      } catch {
        $("connection-warning").hidden = false;
      }
    }
    if (page === "providers" && environmentTab === "install")
      await refreshInstall();
  })().finally(() => (polling = null));
  return polling;
}
function poll() {
  clearTimeout(pollTimer);
  pollTimer = setTimeout(async () => {
    try {
      if (!document.hidden) await refresh();
    } catch {
      $("connection-warning").hidden = false;
    } finally {
      poll();
    }
  }, 4000);
}
$("retry-connection").onclick = (event) => act(refresh, event.currentTarget);
function renderSeriesList() {
  const stamp = JSON.stringify([seriesList, currentSeries?.id]);
  if (stamp === seriesListStamp) return;
  seriesListStamp = stamp;
  $("series-list").replaceChildren(
    ...seriesList.map((series) =>
      el(
        "button",
        {
          class:
            "project-item" +
            (currentSeries?.id === series.id ? " selected" : ""),
          onclick: () => act(() => openSeries(series.id)),
        },
        el("span", { class: "project-name" }, series.title),
        el(
          "span",
          { class: "project-meta" },
          `${series.episode_count} 集`,
          `${series.progress.complete} 集完成`,
        ),
      ),
    ),
  );
  if (!seriesList.length)
    $("series-list").append(
      el("p", { class: "muted" }, "创建整剧后，各集将在这里独立保存。"),
    );
  if (!currentSeries)
    $("series-workspace").replaceChildren(
      empty(
        "把故事讲成一部剧",
        "创建整剧并选择集数，或手动提供每集大纲。",
        el(
          "button",
          {
            class: "primary",
            onclick: () => {
              $("series-create").open = true;
              $("series-form").elements.title.focus();
            },
          },
          "创建一部短剧",
        ),
      ),
    );
}
async function openSeries(id) {
  currentSeries = await api("/api/series/" + id);
  selectedEpisodes = new Set(
    currentSeries.episodes.filter((e) => !e.final).map((e) => e.number),
  );
  renderSeries();
  setPage("series");
  seriesListStamp = "";
  renderSeriesList();
}
function renderSeries() {
  const s = currentSeries,
    box = $("series-workspace");
  if (!s) return;
  selectedEpisodes = new Set(
    [...selectedEpisodes].filter((n) => s.episodes.some((e) => e.number === n)),
  );
  box.replaceChildren(
    el(
      "div",
      { class: "workspace-heading" },
      el(
        "div",
        {},
        el("p", { class: "eyebrow" }, "SERIES WORKSPACE"),
        el("h1", {}, s.title),
        el(
          "p",
          { class: "workspace-meta" },
          `${s.episode_count} 集 · ${s.progress.complete} 集完成 · ${s.progress.error} 集遇到问题`,
        ),
      ),
    ),
  );
  if (s.planner_status)
    box.append(
      el(
        "div",
        { class: "notice" + (s.planner_status === "error" ? " error" : "") },
        badge(s.planner_status),
        el("p", {}, s.planner_message || "分集计划已保存。"),
      ),
    );
  const selected = () => {
    if (!selectedEpisodes.size) throw Error("请至少选择一集。");
    return [...selectedEpisodes].sort((a, b) => a - b);
  };
  const run = async (kind) => {
    const result = await api(`/api/series/${s.id}/batch`, {
      numbers: selected(),
      kind,
    });
    toast(`已按集序排队 ${result.job_ids.length} 集。`);
    await refresh();
  };
  const selectedCount = el(
      "span",
      { class: "selection-count" },
      `已选 ${selectedEpisodes.size} 集`,
    ),
    batchButtons = [];
  const button = (text, work, primary = false) =>
    el(
      "button",
      {
        class: primary ? "primary" : "",
        onclick: (event) => act(work, event.currentTarget),
      },
      text,
    );
  box.append(
    el(
      "div",
      { class: "actions" },
      selectedCount,
      button("全选", () => {
        selectedEpisodes = new Set(s.episodes.map((e) => e.number));
        renderSeries();
      }),
      button("未完成", () => {
        selectedEpisodes = new Set(
          s.episodes.filter((e) => !e.final).map((e) => e.number),
        );
        renderSeries();
      }),
      button("失败 / 暂停", () => {
        selectedEpisodes = new Set(
          s.episodes
            .filter((e) => ["error", "paused"].includes(e.status))
            .map((e) => e.number),
        );
        renderSeries();
      }),
    ),
  );
  const planning = isBusy(s.planner_status),
    plan = button("规划 / 继续拆集", async () => {
      await api(`/api/series/${s.id}/plan`, {});
      toast("分集规划已排队。已完成计划会保留。");
      await refresh();
    });
  plan.disabled = planning;
  const actions = el("div", { class: "actions" }, plan);
  for (const [kind, label] of [
    ["plan", "批量文字规划"],
    ["all", "生成 / 继续所选集"],
  ]) {
    const node = button(label, () => run(kind), kind === "all");
    node.disabled = !selectedEpisodes.size || planning;
    batchButtons.push(node);
    actions.append(node);
  }
  if (planning || s.episodes.some((e) => isBusy(e.status)))
    actions.append(
      button("停止本剧任务", async () => {
        toast((await api(`/api/series/${s.id}/stop`, {})).message);
        await refresh();
      }),
    );
  box.append(
    actions,
    el(
      "p",
      { class: "field-help" },
      `每集独立保存，GPU 按集序生成。失败后${s.fail_policy === "stop" ? "暂停本批后续集" : "继续其他集"}。`,
    ),
  );
  const grid = el("div", { class: "episode-grid" });
  box.append(grid);
  for (const episode of s.episodes) {
    const check = el("input", {
        type: "checkbox",
        checked: selectedEpisodes.has(episode.number),
        onchange: (event) => {
          if (event.target.checked) selectedEpisodes.add(episode.number);
          else selectedEpisodes.delete(episode.number);
          selectedCount.textContent = `已选 ${selectedEpisodes.size} 集`;
          for (const button of batchButtons)
            button.disabled = !selectedEpisodes.size || planning;
        },
      }),
      card = el(
        "article",
        { class: "episode-card" },
        el(
          "div",
          { class: "episode-title" },
          el(
            "label",
            { class: "check" },
            check,
            `第 ${episode.number} 集 · ${episode.title}`,
          ),
          badge(episode.status),
        ),
        el(
          "p",
          {},
          episode.message ||
            episode.plan?.premise ||
            episode.input ||
            "等待整剧分集规划",
        ),
      );
    if (episode.project_id)
      card.append(button("打开这一集", () => openProject(episode.project_id)));
    grid.append(card);
  }
  box.append(
    el(
      "details",
      {},
      el("summary", {}, "整剧人物与分集计划"),
      el(
        "pre",
        {},
        JSON.stringify(
          {
            characters: s.characters,
            scenes: s.scenes,
            props: s.props,
            episodes: s.episodes.map((e) => ({
              number: e.number,
              plan: e.plan,
            })),
          },
          null,
          2,
        ),
      ),
    ),
  );
}
function updateSeriesMode() {
  const manual = $("series-form").elements.mode.value === "manual";
  $("series-manual-label").hidden = !manual;
  $("series-input-label").hidden = manual;
  $("episode-count-label").hidden = manual;
}
$("series-form").elements.mode.onchange = updateSeriesMode;
$("series-form").addEventListener("input", () => (seriesFormTouched = true));
$("series-form").addEventListener("submit", (event) => {
  event.preventDefault();
  act(async () => {
    const form = event.target;
    if (!form.reportValidity()) return;
    const data = Object.fromEntries(new FormData(form));
    let characters = [],
      episodes = [];
    try {
      characters = data.characters.trim() ? JSON.parse(data.characters) : [];
      episodes = data.mode === "manual" ? JSON.parse(data.episodes) : [];
    } catch {
      throw Error("人物或每集内容的 JSON 格式有误，请检查后重试。");
    }
    const result = await api("/api/series", {
      ...data,
      episode_count: Number(data.episode_count),
      characters,
      episodes,
      options: readSeries(),
      start: event.submitter?.value || "draft",
    });
    seriesFormTouched = false;
    $("series-create").open = false;
    await openSeries(result.id);
    await refresh();
    toast("短剧已创建，每集会按集序独立保存。");
  }, event.submitter);
});
function renderEnvironmentTabs() {
  $("environment-tabs").replaceChildren(
    tabs(
      [
        { id: "provider", label: "文字模型" },
        { id: "comfy", label: "ComfyUI 连接" },
        { id: "install", label: "安装与修复" },
      ],
      environmentTab,
      (id) => {
        environmentTab = id;
        renderEnvironmentTabs();
        if (id === "install")
          act(async () => {
            await detectEnvironment();
            await refreshInstall();
          });
      },
      "模型与环境分区",
    ),
  );
  for (const id of ["provider", "comfy", "install"])
    $(id === "provider" ? "provider-panel" : id + "-panel").hidden =
      id !== environmentTab;
}
async function saveConfig(next, render = true) {
  if (configSaving)
    throw Error("另一项配置正在保存，请稍后重试。输入内容会保留。");
  configSaving = true;
  try {
    config = await api("/api/config", next);
    config = await api("/api/config");
  } finally {
    configSaving = false;
  }
  plannedInstall = null;
  $("start-install").disabled = true;
  const draft = readNew ? readNew() : {},
    seriesDraft = readSeries ? readSeries() : {};
  readNew = optionsEditor(
    $("new-options"),
    config,
    presets.builtin,
    skills,
    draft,
    schedulePreview,
  );
  readSeries = optionsEditor(
    $("series-options"),
    config,
    presets.builtin,
    skills,
    seriesDraft,
  );
  if (render) {
    renderProviders();
    renderEnvironment();
  }
  if (workspace.current && workspace.panel === "settings") workspace.render();
}
function renderProviders() {
  const list = $("provider-list");
  list.replaceChildren();
  for (const provider of config.providers) {
    const savedDraft = providerDrafts.get(provider.id);
    const p = structuredClone(savedDraft?.provider || provider),
      name = el("input", { value: p.name, maxLength: 80 }),
      url = el("input", { type: "url", value: p.base_url }),
      model = el("input", {
        value: p.model,
        placeholder: "提供商支持的真实模型名称",
      }),
      kind = select(
        [
          { value: "deepseek", label: "DeepSeek" },
          { value: "ollama", label: "Ollama" },
          { value: "lmstudio", label: "LM Studio" },
          { value: "compatible", label: "兼容 OpenAI Chat API" },
        ],
        p.kind,
      ),
      key = el("input", {
        value: savedDraft?.key || "",
        type: "password",
        autocomplete: "new-password",
        placeholder: p.key_configured
          ? "已配置 · 留空保留原密钥"
          : "API key（本地服务可留空）",
      }),
      local = el("input", { type: "checkbox", checked: p.local }),
      stream = el("input", { type: "checkbox", checked: p.stream }),
      unload = el("input", { type: "checkbox", checked: p.unload_after_use }),
      structured = select(
        [
          { value: "text", label: "普通文字" },
          { value: "json", label: "JSON 输出" },
          { value: "schema", label: "JSON Schema" },
        ],
        p.structured,
      ),
      tokens = el("input", {
        type: "number",
        min: 128,
        max: 65536,
        value: p.max_tokens,
      }),
      timeout = el("input", {
        type: "number",
        min: 10,
        max: 1800,
        value: p.timeout,
      }),
      temperature = el("input", {
        type: "number",
        min: 0,
        max: 2,
        step: 0.1,
        value: p.temperature,
      }),
      retries = el("input", {
        type: "number",
        min: 0,
        max: 10,
        value: p.retries ?? 3,
      }),
      formatRetries = el("input", {
        type: "number",
        min: 0,
        max: 10,
        value: p.format_retries ?? 3,
      }),
      extra = el("textarea", {
        rows: 3,
        class: "code-editor",
        value: savedDraft?.extraRaw ?? JSON.stringify(p.extra || {}, null, 2),
        spellcheck: false,
      });
    const result = el("div", {
        class: "provider-result",
        "aria-live": "polite",
      }),
      advanced = el(
        "details",
        {},
        el("summary", {}, "重试、超时与高级参数"),
        el(
          "div",
          { class: "grid three" },
          field("请求超时（秒）", timeout),
          field("最大输出 tokens", tokens),
          field("温度", temperature),
          field("网络 / API 额外重试", retries),
          field("格式额外修复", formatRetries),
          field("结构化输出", structured),
        ),
        field("额外请求参数 JSON", extra),
        el("label", { class: "check" }, unload, "文字请求后卸载本地模型"),
        el(
          "p",
          { class: "field-help" },
          "默认首次请求失败后再尝试 3 次。网络与格式分别处理；认证、余额等确定性错误会直接提示。",
        ),
      );
    const card = el(
      "details",
      {
        class: "provider-card",
        open: p.id === config.providers[0]?.id || !!savedDraft,
      },
      el(
        "summary",
        {},
        el(
          "span",
          { class: "provider-heading" },
          p.name,
          el("small", {}, p.model || "尚未选择模型"),
        ),
        el(
          "span",
          {
            class:
              "badge " + (p.key_configured || p.local ? "success" : "warning"),
          },
          p.local ? "本地服务" : p.key_configured ? "密钥已配置" : "待配置密钥",
        ),
      ),
      el(
        "div",
        { class: "grid" },
        field("提供商名称", name),
        field("连接类型", kind),
        field("服务地址", url),
        field("默认模型", model),
        field("API key", key, "保存在本机。留空不会删除已有密钥。"),
      ),
      el(
        "div",
        { class: "check-row" },
        el("label", { class: "check" }, local, "本地模型"),
        el("label", { class: "check" }, stream, "流式请求"),
      ),
      advanced,
    );
    const button = (label, work, primary = false) =>
      el(
        "button",
        {
          class: primary ? "primary" : "",
          onclick: (event) => act(work, event.currentTarget),
        },
        label,
      );
    const draftHint = el(
      "p",
      { class: "field-help", hidden: !savedDraft },
      "有未保存修改，保存后再测试连接。",
    );
    card.append(draftHint);
    const revert = button("撤销本连接修改", async () => {
      const choice = await dialog(
        "撤销未保存的连接修改？",
        "恢复这个提供商上次保存的设置，其他提供商的草稿会保留。",
        [
          { label: "继续编辑", value: null },
          { label: "撤销修改", value: true },
        ],
      );
      if (choice) {
        providerDrafts.delete(p.id);
        renderProviders();
      }
    });
    revert.disabled = !savedDraft;
    card.append(revert);
    const capture = () => {
      const provider = {
        ...p,
        name: name.value,
        base_url: url.value,
        model: model.value,
        kind: kind.value,
        local: local.checked,
        stream: stream.checked,
        unload_after_use: unload.checked,
        structured: structured.value,
        timeout: Number(timeout.value),
        max_tokens: Number(tokens.value),
        temperature: Number(temperature.value),
        retries: Number(retries.value),
        format_retries: Number(formatRetries.value),
      };
      const revision = (providerDrafts.get(p.id)?.revision || 0) + 1;
      providerDrafts.set(p.id, {
        provider,
        key: key.value,
        extraRaw: extra.value,
        revision,
      });
      draftHint.hidden = false;
      revert.disabled = false;
    };
    card.addEventListener("input", capture);
    card.addEventListener("change", capture);
    const requireSaved = () => {
      if (providerDrafts.has(p.id))
        throw Error(
          "当前连接有未保存修改。请先点击“保存连接”，再测试或获取模型。",
        );
    };
    const save = async () => {
      const invalid = card.querySelector(
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
        throw Error("请先修正连接设置中标出的输入。");
      }
      capture();
      const submitted = providerDrafts.get(p.id);
      let extraValue;
      try {
        extraValue = JSON.parse(extra.value);
      } catch {
        throw Error("额外请求参数 JSON 格式有误。");
      }
      Object.assign(p, {
        name: name.value,
        base_url: url.value,
        model: model.value,
        kind: kind.value,
        local: local.checked,
        stream: stream.checked,
        unload_after_use: unload.checked,
        structured: structured.value,
        timeout: Number(timeout.value),
        max_tokens: Number(tokens.value),
        temperature: Number(temperature.value),
        retries: Number(retries.value),
        format_retries: Number(formatRetries.value),
        extra: extraValue,
      });
      const next = structuredClone(config);
      next.providers = next.providers.map((value) =>
        value.id === p.id ? p : value,
      );
      await saveConfig(next, false);
      if (submitted.key) {
        await api("/api/provider/key", { id: p.id, key: submitted.key });
        config = await api("/api/config");
      }
      if (providerDrafts.get(p.id)?.revision === submitted.revision)
        providerDrafts.delete(p.id);
      renderProviders();
      renderEnvironment();
      toast("连接配置已保存。");
    };
    card.append(
      el(
        "div",
        { class: "actions" },
        button("保存连接", save, true),
        button("测试连接", async () => {
          requireSaved();
          result.replaceChildren(
            el("p", { class: "muted" }, "正在测试已保存的服务连接…"),
          );
          const value = await api(`/api/providers/${p.id}/test`, {
            model: model.value,
          });
          result.replaceChildren(
            el(
              "div",
              { class: "notice success" },
              "连接成功",
              el("p", {}, value.text || "模型已响应。"),
            ),
          );
        }),
        button("获取可用模型", async () => {
          requireSaved();
          const value = await api(`/api/providers/${p.id}/models`);
          result.replaceChildren(
            el("p", { class: "muted" }, "点击模型名称即可填入，之后保存连接。"),
            el(
              "div",
              { class: "actions" },
              value.models.map((id) =>
                button(id, () => {
                  model.value = id;
                  capture();
                  toast("已填入模型名称，请保存连接。");
                }),
              ),
            ),
          );
        }),
        button("检测能力", async () => {
          requireSaved();
          result.replaceChildren(
            el("p", { class: "muted" }, "正在检查文字、流式与结构化输出能力…"),
          );
          const value = await api(`/api/providers/${p.id}/test`, {
            model: model.value,
            probe: true,
          });
          result.replaceChildren(el("pre", {}, JSON.stringify(value, null, 2)));
          const next = structuredClone(config);
          next.providers.find((value) => value.id === p.id).capabilities =
            value.capabilities;
          config = await api("/api/config", next);
        }),
        ...(p.local
          ? [
              button("卸载本地模型", async () => {
                const value = await api(`/api/providers/${p.id}/unload`, {
                  model: model.value,
                });
                result.replaceChildren(
                  el("pre", {}, JSON.stringify(value, null, 2)),
                );
              }),
            ]
          : []),
      ),
      result,
    );
    list.append(card);
  }
}
$("add-provider").onclick = (event) =>
  act(async () => {
    const next = structuredClone(config),
      base = next.providers[0];
    next.providers.push({
      ...base,
      id: "custom-" + Date.now(),
      name: "我的兼容服务",
      kind: "compatible",
      base_url: "http://127.0.0.1:8080/v1",
      model: "",
      local: true,
      extra: {},
      capabilities: {},
      key_configured: false,
    });
    await saveConfig(next);
    const card = $("provider-list").lastElementChild;
    card.open = true;
    card.querySelector("input").focus();
    toast("服务已添加，请填写地址和模型后保存。");
  }, event.currentTarget);
function renderEnvironment() {
  const form = $("environment-form"),
    env = { ...config.environment, ...environmentDraft?.fields };
  for (const name of ["mode", "comfy_url", "comfy_dir", "python"])
    form.elements[name].value = env[name] || "";
  form.elements.projects_dir.value =
    environmentDraft?.fields.projects_dir ?? config.projects_dir;
  form.elements.proxy.value =
    environmentDraft?.fields.proxy ?? config.proxy ?? "";
  $("quality-editor").value =
    environmentDraft?.quality ?? JSON.stringify(env.profiles, null, 2);
  renderModelInputs();
  $("install-mode").value = env.mode || "existing";
  updateEnvironmentMode();
  const auth = el("input", {
    value: comfyAuthDraft,
    oninput: (event) => {
      comfyAuthDraft = event.target.value;
    },
    type: "password",
    autocomplete: "new-password",
    placeholder: "远程服务 Bearer token，可留空",
  });
  $("comfy-auth").replaceChildren(
    el(
      "details",
      {},
      el("summary", {}, "服务认证（可选）"),
      field("ComfyUI Bearer token", auth),
      el(
        "button",
        {
          onclick: (event) =>
            act(async () => {
              await api("/api/provider/key", { id: "comfy", key: auth.value });
              auth.value = "";
              comfyAuthDraft = "";
              toast("服务认证已在本机保存。");
            }, event.currentTarget),
        },
        "保存服务认证",
      ),
    ),
  );
}
function updateEnvironmentMode() {
  const remote = $("environment-form").elements.mode.value === "remote";
  for (const node of document.querySelectorAll("[data-local-path]"))
    node.hidden = remote;
  plannedInstall = null;
  $("start-install").disabled = true;
}
$("environment-form").elements.mode.onchange = updateEnvironmentMode;
function renderModelInputs() {
  const labels = {
      fl_model: "文字 / 首尾帧模型",
      ref_model: "多模态参考模型",
      text_encoder: "文字编码器",
      video_vae: "视频 VAE",
      audio_vae: "音频 VAE",
      fl_lora: "文字加速 LoRA",
      ref_lora: "参考加速 LoRA",
      attention: "注意力后端",
    },
    grid = el("div", { class: "grid" });
  for (const [name, label] of Object.entries(labels)) {
    const selectedValue =
      environmentDraft?.fields[name] ?? config.environment[name];
    const input = modelCatalog
      ? select(
          [
            ...new Set(
              [selectedValue, ...(modelCatalog.models[name] || [])].filter(
                Boolean,
              ),
            ),
          ],
          selectedValue,
        )
      : el("input", { value: selectedValue || "" });
    input.name = name;
    grid.append(field(label, input));
  }
  $("h3-models").replaceChildren(
    el("details", {}, el("summary", {}, "H3 模型选择与高级配置"), grid),
  );
}
$("refresh-models").onclick = (event) =>
  act(async () => {
    modelCatalog = await api("/api/environment/catalog");
    renderModelInputs();
    toast(
      modelCatalog.missing_nodes.length
        ? "缺少节点：" + modelCatalog.missing_nodes.join("、")
        : "模型与节点已读取。",
    );
  }, event.currentTarget);
$("environment-form").addEventListener("submit", (event) => {
  event.preventDefault();
  act(async () => {
    const revision = environmentRevision;
    const data = Object.fromEntries(new FormData(event.target));
    let profiles;
    try {
      profiles = JSON.parse($("quality-editor").value);
    } catch {
      throw Error("质量预设 JSON 格式有误，请检查后保存。");
    }
    const next = structuredClone(config);
    next.environment = {
      ...next.environment,
      ...Object.fromEntries(
        Object.entries(data).filter(
          ([key]) => !["projects_dir", "proxy"].includes(key),
        ),
      ),
      profiles,
    };
    next.projects_dir = data.projects_dir;
    next.proxy = data.proxy;
    await saveConfig(next, false);
    if (environmentRevision === revision) environmentDraft = null;
    renderProviders();
    renderEnvironment();
    toast("生成环境已保存。");
  }, event.submitter);
});
$("environment-form").addEventListener("input", () => {
  environmentRevision++;
  environmentDraft = {
    fields: Object.fromEntries(new FormData($("environment-form"))),
    quality: $("quality-editor").value,
  };
});
$("environment-form").addEventListener("change", () => {
  environmentRevision++;
  environmentDraft = {
    fields: Object.fromEntries(new FormData($("environment-form"))),
    quality: $("quality-editor").value,
  };
});
$("verify-environment").onclick = (event) =>
  act(async () => {
    if (!(await workspace.canLeave())) return;
    const result = await api("/api/environment/verify", {});
    await openProject(result.id, true);
    await refresh();
    toast("4 秒样片已排队，会使用 GPU，不调用文字模型。");
  }, event.currentTarget);
async function detectEnvironment() {
  const result = await api("/api/environment"),
    h = result.hardware;
  $("hardware-info").replaceChildren(
    el("span", {}, `${h.os} · ${h.architecture}`),
    el(
      "span",
      {},
      h.gpu
        .map((g) => g.name + " " + Math.round(g.vram_mb / 1024) + "GB")
        .join(" / ") || "未检测到 NVIDIA 显卡",
    ),
    el("span", {}, `内存 ${Math.round(h.ram_bytes / 1024 ** 3)}GB`),
    el("span", {}, `磁盘剩余 ${Math.round(h.free_disk_bytes / 1024 ** 3)}GB`),
  );
  const selection = $("manifest-select").value;
  $("manifest-select").replaceChildren(
    ...result.manifests.map((m) =>
      el("option", { value: m.id, selected: m.id === selection }, m.name),
    ),
  );
}
function installOptions() {
  return {
    mode: $("install-mode").value,
    manifest: $("manifest-select").value,
    install_dir: $("install-dir").value.trim(),
    models_dir: $("models-dir").value.trim(),
    model_search_dirs: $("model-search-dirs")
      .value.split("\n")
      .map((s) => s.trim())
      .filter(Boolean),
    comfy_url: $("environment-form").elements.comfy_url.value,
    comfy_dir: $("environment-form").elements.comfy_dir.value,
    python: $("environment-form").elements.python.value,
  };
}
function invalidatePlan() {
  plannedInstall = null;
  $("start-install").disabled = true;
}
for (const id of [
  "install-mode",
  "manifest-select",
  "install-dir",
  "models-dir",
  "model-search-dirs",
])
  $(id).addEventListener("input", invalidatePlan);
$("environment-form").addEventListener("input", invalidatePlan);
$("detect-environment").onclick = (event) =>
  act(detectEnvironment, event.currentTarget);
$("plan-install").onclick = (event) =>
  act(async () => {
    if (!$("manifest-select").value) await detectEnvironment();
    const options = installOptions(),
      plan = await api("/api/environment/plan", options);
    plannedInstall = options;
    $("start-install").disabled = false;
    const files = [
      ...plan.models,
      ...(plan.mode === "fresh"
        ? [
            {
              name: plan.portable.name,
              size: plan.portable.size,
              action: "download",
              target: plan.install_dir,
            },
            ...(plan.runtime_wheels || []).map((w) => ({
              ...w,
              action: "download",
              target: "推理运行环境",
            })),
          ]
        : []),
    ];
    $("install-plan").replaceChildren(
      el(
        "div",
        { class: "notice" },
        plan.mode === "remote"
          ? "远程模式不会下载文件，将检查已填写的服务。"
          : `待下载约 ${(plan.download_bytes / 1024 ** 3).toFixed(1)}GB · 目标磁盘剩余 ${Math.round(plan.hardware.free_disk_bytes / 1024 ** 3)}GB`,
        el("p", {}, `模型保存到 ${plan.models_dir}`),
      ),
      el(
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
              ["文件", "操作", "大小", "位置"].map((t) => el("th", {}, t)),
            ),
          ),
          el(
            "tbody",
            {},
            files.map((file) =>
              el(
                "tr",
                {},
                el("td", {}, file.name),
                el(
                  "td",
                  {},
                  file.action === "reuse" ? "复用并校验" : "下载 / 校验缓存",
                ),
                el("td", {}, `${Math.round(file.size / 1024 ** 2)}MB`),
                el("td", {}, file.existing || file.target),
              ),
            ),
          ),
        ),
      ),
      el("p", { class: "field-help" }, plan.note),
    );
  }, event.currentTarget);
$("start-install").onclick = (event) =>
  act(async () => {
    if (!plannedInstall) throw Error("配置已变化，请先重新预览安装清单。");
    await api("/api/environment/install", plannedInstall);
    invalidatePlan();
    toast("安装任务已排队，文件校验与下载进度会显示在下方。");
    await refreshInstall();
  }, event.currentTarget);
$("stop-install").onclick = (event) =>
  act(
    async () => toast((await api("/api/environment/stop", {})).message),
    event.currentTarget,
  );
$("save-hf-token").onclick = (event) =>
  act(async () => {
    await api("/api/provider/key", { id: "hf", key: $("hf-token").value });
    $("hf-token").value = "";
    toast("HF token 已在本机保存。");
  }, event.currentTarget);
async function refreshInstall() {
  const progress = await api("/api/environment/progress");
  $("install-progress").hidden = !progress.status;
  $("stop-install").hidden = !jobs.some(
    (job) =>
      job.project_id === "__environment" &&
      ["queued", "running"].includes(job.status),
  );
  if (progress.status) {
    $("install-progress").replaceChildren(
      el(
        "span",
        {},
        progress.message || `${progress.status} ${progress.file || ""}`,
      ),
    );
    if (progress.total)
      $("install-progress").append(
        el("progress", { max: progress.total, value: progress.bytes || 0 }),
        el(
          "span",
          {},
          `${Math.round(((progress.bytes || 0) * 100) / progress.total)}%`,
        ),
      );
  }
}
function renderPersonalPresets() {
  $("personal-select").replaceChildren(
    el("option", { value: "" }, "选择个人预设"),
    ...Object.entries(presets.personal).map(([id, p]) =>
      el("option", { value: id }, p.name),
    ),
  );
}
function renderSkills(preferred, load = true) {
  const filter = $("skill-stage-filter").value,
    list = skills.filter((s) => filter === "all" || s.stage === filter),
    selected = preferred || $("skill-select").value;
  $("skill-select").replaceChildren(
    ...list.map((s) =>
      el(
        "option",
        { value: s.id, selected: s.id === selected },
        `${STAGES[s.stage]} · ${s.name}`,
      ),
    ),
  );
  renderPersonalPresets();
  appliedSkillFilter = filter;
  if (load && list.length && !skillDirty)
    act(() => loadSkill($("skill-select").value));
}
function setSkillPackage(value) {
  skillLoadVersion++;
  skillPackage = value;
  skillDirty = false;
  skillRawDirty = false;
  $("skill-name").value = value.metadata.name;
  $("skill-edit-stage").value = value.metadata.stage;
  $("skill-content").value = value.files["SKILL.md"];
  $("skill-editor").value = JSON.stringify(value, null, 2);
  $("skill-dirty").hidden = true;
  for (const id of ["skill-name", "skill-content", "skill-edit-stage"])
    $(id).disabled = false;
  if (
    ![...$("skill-select").options].some(
      (option) => option.value === value.metadata.id,
    )
  )
    $("skill-select").append(
      el(
        "option",
        { value: value.metadata.id },
        "未保存 · " + value.metadata.name,
      ),
    );
  $("skill-select").value = value.metadata.id;
  skillChoice = value.metadata.id;
  $("skill-info").replaceChildren(
    badge("ready"),
    el("h3", {}, value.metadata.name),
    el("p", {}, value.metadata.description || "可按自己的创作方式修改。"),
    el(
      "p",
      { class: "field-help" },
      `${STAGES[value.metadata.stage]} · ${Object.keys(value.files).length} 个规则与参考文件`,
    ),
  );
}
async function loadSkill(id) {
  const version = ++skillLoadVersion;
  const lock = (disabled) => {
    for (const key of [
      "skill-copy",
      "skill-new",
      "skill-save",
      "skill-export",
      "skill-apply-json",
      "skill-import",
      "skill-name",
      "skill-content",
      "skill-editor",
      "skill-edit-stage",
    ])
      $(key).disabled = disabled;
  };
  lock(true);
  let value;
  try {
    value = await api("/api/skills/" + id);
  } catch (error) {
    if (version === skillLoadVersion) lock(false);
    throw error;
  }
  if (version !== skillLoadVersion || skillDirty) return;
  lock(false);
  setSkillPackage({
    metadata: Object.fromEntries(
      Object.entries(value).filter(
        ([key]) => !["files", "content_hash"].includes(key),
      ),
    ),
    files: value.files,
  });
}
async function canChangeSkill() {
  if (!skillDirty) return true;
  const choice = await dialog(
    "规则还有未保存修改",
    "切换前可先保存，或放弃当前修改。",
    [
      { label: "继续编辑", value: null },
      { label: "放弃修改", value: "discard" },
      { label: "保存后切换", value: "save", primary: true },
    ],
  );
  if (choice === "discard") {
    skillDirty = false;
    return true;
  }
  if (choice === "save") return !!(await saveSkill());
  return false;
}
function readSkill() {
  if (skillRawDirty) {
    try {
      return JSON.parse($("skill-editor").value);
    } catch {
      throw Error("完整 Skill 包 JSON 格式有误。");
    }
  }
  const value = structuredClone(skillPackage);
  value.metadata.name = $("skill-name").value.trim();
  value.metadata.stage = $("skill-edit-stage").value;
  value.files["SKILL.md"] = $("skill-content").value;
  return value;
}
function markSkill(raw = false) {
  skillRevision++;
  skillDirty = true;
  skillRawDirty = raw;
  $("skill-dirty").hidden = false;
  for (const id of ["skill-name", "skill-content", "skill-edit-stage"])
    $(id).disabled = raw;
}
for (const id of ["skill-name", "skill-content", "skill-edit-stage"])
  $(id).addEventListener("input", () => {
    markSkill();
    $("skill-editor").value = JSON.stringify(readSkill(), null, 2);
  });
$("skill-editor").oninput = () => markSkill(true);
$("skill-select").onchange = () =>
  act(async () => {
    const id = $("skill-select").value;
    if (await canChangeSkill()) await loadSkill(id);
    else $("skill-select").value = skillChoice;
  });
$("skill-stage-filter").onchange = () =>
  act(async () => {
    if (await canChangeSkill()) renderSkills();
    else $("skill-stage-filter").value = appliedSkillFilter;
  });
async function saveSkill() {
  const value = readSkill(),
    revision = skillRevision;
  if (!value.metadata?.name) throw Error("请填写规则名称。");
  const saved = await api("/api/skills/" + value.metadata.id, value);
  skills = await api("/api/skills");
  if (revision !== skillRevision) {
    toast("提交时的版本已保存；之后输入的修改仍保留，请再次保存。");
    return false;
  }
  skillDirty = false;
  if (!["all", value.metadata.stage].includes($("skill-stage-filter").value))
    $("skill-stage-filter").value = "all";
  renderSkills(value.metadata.id, false);
  setSkillPackage({
    metadata: Object.fromEntries(
      Object.entries(saved).filter(
        ([key]) => !["files", "content_hash"].includes(key),
      ),
    ),
    files: saved.files,
  });
  const currentNew = readNew(),
    currentSeriesOptions = readSeries();
  readNew = optionsEditor(
    $("new-options"),
    config,
    presets.builtin,
    skills,
    currentNew,
    schedulePreview,
  );
  readSeries = optionsEditor(
    $("series-options"),
    config,
    presets.builtin,
    skills,
    currentSeriesOptions,
  );
  if (workspace.current && workspace.panel === "settings") workspace.render();
  toast("创作规则已保存。");
  return true;
}
$("skill-save").onclick = (event) => act(saveSkill, event.currentTarget);
$("skill-apply-json").onclick = (event) =>
  act(() => {
    let value;
    try {
      value = JSON.parse($("skill-editor").value);
    } catch {
      throw Error("完整 Skill 包 JSON 格式有误。");
    }
    if (
      !value.metadata?.id ||
      !value.metadata?.stage ||
      typeof value.files?.["SKILL.md"] !== "string"
    )
      throw Error("完整包需要 metadata.id、stage 和 files.SKILL.md。");
    setSkillPackage(value);
    markSkill();
    toast("完整包已应用，点击保存写入规则。");
  }, event.currentTarget);
$("skill-copy").onclick = (event) =>
  act(async () => {
    if (!(await canChangeSkill())) return;
    const value = readSkill();
    value.metadata.id = "user-" + Date.now();
    value.metadata.name += "（我的版本）";
    setSkillPackage(value);
    markSkill();
    $("skill-name").focus();
    toast("副本已放入编辑区，修改后点击保存。");
  }, event.currentTarget);
$("skill-new").onclick = (event) =>
  act(async () => {
    if (!(await canChangeSkill())) return;
    setSkillPackage({
      metadata: {
        id: "user-" + Date.now(),
        name: "我的创作规则",
        stage: "outline",
        version: "1.0",
      },
      files: {
        "SKILL.md":
          "# 我的创作规则\n\n视觉风格：{{style}}。按程序 JSON 结构输出。",
      },
    });
    markSkill();
    $("skill-name").focus();
  }, event.currentTarget);
$("skill-export").onclick = (event) =>
  act(
    () => download((readSkill().metadata.id || "skill") + ".json", readSkill()),
    event.currentTarget,
  );
$("skill-import").onchange = (event) =>
  act(async () => {
    const file = event.target.files[0];
    if (!file) return;
    if (!(await canChangeSkill())) return;
    let value;
    try {
      value = JSON.parse(await file.text());
    } catch {
      throw Error("导入的 Skill 文件不是合法 JSON。");
    }
    if (!value.metadata?.stage || typeof value.files?.["SKILL.md"] !== "string")
      throw Error("Skill 包需要 metadata 和 files.SKILL.md。");
    setSkillPackage(value);
    markSkill();
    event.target.value = "";
    toast("规则已载入编辑区，请检查后保存。");
  });
$("personal-select").onchange = (event) => {
  const preset = presets.personal[event.target.value];
  if (!preset) return;
  readNew = optionsEditor(
    $("new-options"),
    config,
    presets.builtin,
    skills,
    preset.options,
    schedulePreview,
  );
  newFormTouched = true;
  setPage("create");
  previewDuration(readNew());
  toast("个人预设已应用，故事内容仍保留。");
};
$("transfer-import").onchange = (event) =>
  act(async () => {
    const file = event.target.files[0];
    if (!file) return;
    if (!(await workspace.canLeave())) return;
    const body = new FormData();
    body.append("file", file);
    let response;
    try {
      response = await fetch("/api/import", { method: "POST", body });
    } catch {
      throw Error("导入连接失败，请稍后重试。");
    }
    const result = await response.json();
    if (!response.ok) throw Error(result.error || "项目导入失败。");
    await refresh();
    if (result.projects.length) await openProject(result.projects[0], true);
    toast(
      `已导入 ${result.projects.length} 个项目。提供商认证需要在本机配置。`,
    );
    event.target.value = "";
  });
await act(boot);
poll();
