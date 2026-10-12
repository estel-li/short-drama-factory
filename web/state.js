export const STATUS = {
  new: ["草稿", "neutral"],
  ready: ["待生成", "neutral"],
  queued: ["排队中", "running"],
  running: ["执行中", "running"],
  planning: ["规划中", "running"],
  rendering: ["生成中", "running"],
  retrying: ["重试中", "running"],
  assembling: ["合片中", "running"],
  complete: ["已完成", "success"],
  done: ["已完成", "success"],
  review: ["待检查", "warning"],
  paused: ["已暂停", "warning"],
  error: ["遇到问题", "error"],
  cancelled: ["已停止", "neutral"],
  planned: ["已规划", "neutral"],
  unplanned: ["待规划", "neutral"],
  downloading: ["下载中", "running"],
  extracting: ["解压中", "running"],
  verifying: ["校验中", "running"],
};
export const STAGES = {
  finishing: "质检与后期",
  finish: "质检与后期",
  "rebuild-edit": "重建后期版本",
  settings: "项目设置",
  prompts: "提示词版本",
  "generated-storyboard": "AI 分镜",
  "storyboard-before-edit": "分镜修改前",
  "outline-before-edit": "大纲修改前",
  "outline-change": "大纲重新生成前",
  "outline-edited-storyboard": "大纲修改前的分镜",
  "series-plan-batch": "分集规划",
  all: "完整流程",
  plan: "文字规划",
  outline: "大纲",
  storyboard: "分镜",
  prompt: "提示词",
  first_frame: "首帧接续",
  encoding: "素材编码",
  sampling: "视频采样",
  decoding: "音画解码",
  decode: "音画解码",
  render: "视频生成",
  assembling: "合片",
  done: "完成",
  install: "环境安装",
  "series-plan": "分集规划",
};
export function statusInfo(value) {
  return STATUS[value] || ["等待开始", "neutral"];
}
export function isBusy(status) {
  return [
    "queued",
    "running",
    "planning",
    "rendering",
    "retrying",
    "assembling",
  ].includes(status);
}
export function projectStatus(project, jobs = []) {
  const job = jobs.find((item) => item.project_id === project.id);
  if (job && ["queued", "running"].includes(job.status)) return job.status;
  if (
    job &&
    ["paused", "error", "review"].includes(job.status) &&
    (job.updated_at || "") > (project.state?.updated_at || "")
  )
    return job.status;
  if (project.busy && !isBusy(project.state?.status)) return "queued";
  return project.state?.status || "new";
}
export function shotRecord(project, shot) {
  return (
    project.state?.shots_by_uid?.[shot.uid] ||
    project.state?.shots?.[String(shot.id)] ||
    {}
  );
}

/** Independent drafts survive polling, partial saves, and edits during an in-flight save. */
export class ProjectDraft {
  constructor(project) {
    this.dirty = new Set();
    this.revisions = { story: 0, settings: 0, outline: 0 };
    this.data = {};
    this.ingest(project);
  }
  ingest(project) {
    this.project = structuredClone(project);
    const data = {
      story: project.story,
      settings: project.settings,
      outline: project.outline_result
        ? JSON.stringify(project.outline_result, null, 2)
        : project.outline || "",
    };
    for (const [scope, value] of Object.entries(data)) {
      if (this.dirty.has(scope)) continue;
      // DOM handlers hold references to the editable objects. An unchanged poll
      // must preserve those references, or later typing would edit an old object.
      if (
        !(scope in this.data) ||
        JSON.stringify(this.data[scope]) !== JSON.stringify(value)
      )
        this.data[scope] = structuredClone(value);
    }
  }
  mark(scope) {
    this.dirty.add(scope);
    this.revisions[scope]++;
  }
  snapshot(scope) {
    return {
      value: structuredClone(this.data[scope]),
      revision: this.revisions[scope],
    };
  }
  commit(scope, revision, project) {
    if (this.revisions[scope] === revision) this.dirty.delete(scope);
    this.ingest(project);
  }
  discard() {
    this.dirty.clear();
    this.ingest(this.project);
  }
}

export function continuationIssue(shots, index) {
  if (!index) return "第一镜没有上一分镜，无法接续。";
  const current = shots[index],
    previous = shots[index - 1],
    text = (shot, key) => String(shot[key] || "").trim();
  if (
    text(previous, "continuity_group") &&
    text(current, "continuity_group") &&
    text(previous, "continuity_group") !== text(current, "continuity_group")
  )
    return "与上一镜头属于不同连续段。";
  for (const key of ["scene_id", "scene"])
    if (text(previous, key) && text(current, key))
      return text(previous, key) === text(current, key)
        ? ""
        : "与上一镜头的场景不同。";
  return text(previous, "continuity_group") &&
    text(previous, "continuity_group") === text(current, "continuity_group")
    ? ""
    : "请先填写与上一镜一致的场景或连续段。";
}
