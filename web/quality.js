import { api, el, field, select, download } from "./api.js?v=3.0.0";
import { finishingPayload } from "./state.js?v=3.0.0";
const PRESET_LABELS = {
  original: "原始节奏",
  gentle: "保守收紧",
  compact: "紧凑剪辑",
};

const seconds = (value) =>
  Number.isFinite(value) ? value.toFixed(2) + " 秒" : "—";
const percent = (value) =>
  Number.isFinite(value) ? Math.round(value * 100) + "%" : "未检测";
const url = (pid, file) =>
  "/media/" + pid + "/" + file.split("/").map(encodeURIComponent).join("/");

function timeline(spans, duration, label, style) {
  return el(
    "div",
    { class: "quality-timeline-row" },
    el("span", {}, label),
    el(
      "div",
      {
        class: "quality-timeline",
        role: "img",
        "aria-label":
          label +
          "：" +
          spans
            .map(([a, b]) => `${a.toFixed(2)}～${b.toFixed(2)} 秒`)
            .join("、"),
      },
      spans.map(([a, b]) =>
        el("i", {
          class: style,
          style: `left:${(100 * a) / duration}%;width:${(100 * (b - a)) / duration}%`,
          title: `${a.toFixed(2)}～${b.toFixed(2)} 秒`,
        }),
      ),
    ),
  );
}

function noteEditor(draft, change, disabled) {
  const root = el("div", { class: "note-editor" });
  const render = () => {
    let items;
    try {
      items = JSON.parse(draft.notes);
      if (
        !Array.isArray(items) ||
        items.some((item) => !item || typeof item !== "object")
      )
        throw Error();
    } catch {
      root.replaceChildren(
        el(
          "p",
          { class: "notice warning" },
          "注释 JSON 暂时无法读取，请在高级设置修正后继续。",
        ),
      );
      return;
    }
    const update = () => change(JSON.stringify(items, null, 2));
    root.replaceChildren(
      ...items.map((note, index) => {
        const start = el("input", {
          type: "number",
          min: 0,
          max: 1200,
          step: 0.01,
          required: true,
          disabled,
          value: note.start,
          oninput: (event) => {
            note.start = event.target.valueAsNumber;
            update();
          },
        });
        const end = el("input", {
          type: "number",
          min: 0,
          max: 1200,
          step: 0.01,
          required: true,
          disabled,
          value: note.end,
          oninput: (event) => {
            note.end = event.target.valueAsNumber;
            update();
          },
        });
        const text = el("textarea", {
          rows: 2,
          required: true,
          maxLength: 2000,
          disabled,
          value: note.text || "",
          oninput: (event) => {
            note.text = event.target.value;
            update();
          },
        });
        return el(
          "div",
          { class: "note-row" },
          field(`注释 ${index + 1} 开始（秒）`, start),
          field(`注释 ${index + 1} 结束（秒）`, end),
          field(`注释 ${index + 1} 文字`, text),
          el(
            "button",
            {
              disabled,
              "aria-label": `删除注释 ${index + 1}`,
              onclick: () => {
                items.splice(index, 1);
                update();
                render();
              },
            },
            "删除",
          ),
        );
      }),
      el(
        "button",
        {
          disabled: disabled || items.length >= 100,
          onclick: () => {
            const start = Math.min(1199, Number(items.at(-1)?.end) || 0);
            items.push({ start, end: Math.min(1200, start + 2), text: "" });
            update();
            render();
            root.querySelector(".note-row:last-of-type textarea")?.focus();
          },
        },
        "添加成片注释",
      ),
    );
  };
  render();
  return { root, render };
}

export async function renderQuality(ws, box) {
  box.classList.add("quality-panel");
  const pid = ws.current.id;
  box.append(el("p", { class: "muted" }, "正在读取预检与后期记录…"));
  let data;
  try {
    data = await api(`/api/projects/${pid}/quality`);
  } catch (error) {
    if (ws.current?.id === pid && box.isConnected)
      box.replaceChildren(el("p", { class: "notice error" }, error.message));
    return;
  }
  if (ws.current?.id !== pid || ws.panel !== "quality" || !box.isConnected)
    return;
  box.replaceChildren();
  const draft = ws.draft.data.quality;
  const edit = (key, value) => {
    draft[key] = value;
    ws.mark("quality");
    save.disabled = ws.busy;
  };
  box.append(
    el("h2", {}, "出片预检"),
    el(
      "p",
      { class: "field-help" },
      "先检查对白预算与角色设定，再用一个待生成镜头试听、看人物和多句连说效果。",
    ),
  );
  const issues = data.preflight?.issues || [];
  box.append(
    issues.length
      ? el(
          "div",
          { class: "quality-issues" },
          issues.map((issue) =>
            el(
              "div",
              {
                class:
                  "notice " +
                  (issue.severity === "error" ? "error" : "warning"),
              },
              issue.message,
            ),
          ),
        )
      : el(
          "p",
          { class: "notice" },
          data.preflight?.ready
            ? "对白预算与出场关系检查通过。"
            : data.preflight?.message || "请先生成分镜。",
        ),
  );
  box.append(
    ws.button(
      "先试生成一个待生成镜头",
      async () => {
        if (ws.draft.dirty.size && !(await ws.saveAll())) return;
        await api(`/api/projects/${pid}/stage/render`, {
          force: false,
          limit: 1,
        });
        ws.services.toast("试跑已排队，只新增一个待生成镜头；试听后再继续。");
        await ws.services.refresh();
      },
      false,
      { disabled: ws.busy || !data.preflight?.ready },
    ),
  );
  const preset = select(
    [
      { value: "original", label: "保留原始节奏" },
      { value: "gentle", label: "保守收紧（推荐）" },
      { value: "compact", label: "紧凑剪辑" },
    ],
    draft.preset,
  );
  preset.disabled = ws.busy;
  preset.onchange = () => edit("preset", preset.value);
  const interval = select(
    [
      { value: "0.75", label: "0.75 秒（默认）" },
      { value: "0.25", label: "0.25 秒（短句复查）" },
      { value: "0.1", label: "0.10 秒（密集复查）" },
      { value: "1.5", label: "1.50 秒（快速总览）" },
    ],
    String(draft.interval),
  );
  interval.disabled = ws.busy;
  interval.onchange = () => edit("interval", Number(interval.value));
  const notes = el("textarea", {
    class: "code-editor",
    rows: 5,
    value: draft.notes,
    "aria-label": "成片注释 JSON",
    disabled: ws.busy,
    oninput: (e) => {
      edit("notes", e.target.value);
      notesForm.render();
    },
  });
  const masks = el("textarea", {
    class: "code-editor",
    rows: 6,
    value: draft.masks,
    "aria-label": "逐帧遮罩 JSON",
    disabled: ws.busy,
    oninput: (e) => edit("masks", e.target.value),
  });
  const save = ws.button("保存后期设置", () => ws.saveAll(), false, {
    disabled: ws.busy || !ws.draft.dirty.has("quality"),
  });
  const notesForm = noteEditor(
    draft,
    (value) => {
      edit("notes", value);
      notes.value = value;
    },
    ws.busy,
  );
  box.append(
    el("h2", {}, "无重渲后期"),
    el(
      "p",
      { class: "notice " + (data.finishing?.ready ? "" : "warning") },
      data.finishing?.message || "请先完成所有镜头生成。",
    ),
    el(
      "p",
      { class: "field-help" },
      "读取已完成且与当前剧本一致的原镜头，在 CPU 上检测人声、重剪和生成字幕。每次保留独立版本，原片不改动。",
    ),
    field("剪辑强度", preset),
    field("审核抽帧间隔", interval),
    el(
      "p",
      { class: "field-help" },
      "后期设置可先保存，之后继续编辑。0.10 秒抽帧适合短片复查；长片会生成更多审核图并占用更多磁盘。",
    ),
    el("h3", {}, "成片注释"),
    el(
      "p",
      { class: "field-help" },
      "使用剪辑后成片的秒数，显示在对白上方。调整剪辑强度后，请重新核对开始和结束时间。",
    ),
    notesForm.root,
    el(
      "details",
      {
        class: "option-section",
        open: ws.openDetails.has("quality-annotations"),
        ontoggle: (event) => {
          if (event.target.open) ws.openDetails.add("quality-annotations");
          else ws.openDetails.delete("quality-annotations");
        },
      },
      el("summary", {}, "高级：逐帧遮罩与注释 JSON"),
      el(
        "p",
        { class: "field-help" },
        "注释使用最终成片的 start / end 秒数和 text，显示在对白上方。遮罩按 shot_uid 使用规范化原镜头坐标：多边形关键帧 time / points，另可提供 protect 人物保护轨迹。请用审核图检查残字和遮挡。",
      ),
      field("成片注释 JSON", notes),
      field("逐帧遮罩 JSON", masks),
      el(
        "small",
        { class: "field-help" },
        "可用镜头编号：" +
          (ws.current.story?.shots || [])
            .map((s) => `镜头 ${s.id} = ${s.uid}`)
            .join("；"),
      ),
    ),
    save,
    ws.button(
      "运行质检并生成新版本",
      async () => {
        if (ws.draft.dirty.size && !(await ws.saveAll())) return;
        await api(
          `/api/projects/${pid}/finish`,
          finishingPayload(ws.draft.data.quality),
        );
        ws.services.toast("CPU 后期已排队，原镜头和旧成片会保留。");
        await ws.services.refresh();
      },
      true,
      { disabled: ws.busy || !data.finishing?.ready },
    ),
  );
  const report = data.report;
  if (report?.version === 1) {
    box.append(
      el("h2", {}, "最近完成版本的检测结果"),
      !data.current_edit
        ? el(
            "p",
            { class: "notice warning" },
            "项目内容已调整，下方是历史版本结果。更新镜头并重新后期后，才会成为当前成片。",
          )
        : document.createDocumentFragment(),
      el(
        "div",
        { class: "quality-stats" },
        [
          ["原始时长", seconds(report.original_seconds)],
          ["剪辑后", seconds(report.edited_seconds)],
          ["原片检测人声占比", percent(report.original_speech_density)],
          ["剪后检测人声占比", percent(report.edited_speech_density)],
        ].map(([name, value]) =>
          el("div", {}, el("strong", {}, value), el("span", {}, name)),
        ),
      ),
      el(
        "p",
        { class: "field-help" },
        `检测人声保护区间被切入：${report.detected_speech_cut_count} 个镜头。VAD 不识别台词字词；字幕句内按字数估算，仍需试听核对。可在分镜 JSON 的 dialogue_timings 标注每句原片 start / end，后期会优先使用。`,
      ),
    );
    for (const shot of report.shots || []) {
      const speech = shot.analysis?.relaxed_speech_intervals || [],
        keep = (shot.plan?.keep_frames || []).map(([a, b]) => [a / 24, b / 24]);
      const voice = (shot.analysis?.speech_intervals || []).reduce(
        (sum, [a, b]) => sum + b - a,
        0,
      );
      const rate =
        voice && shot.spoken_units
          ? `${(shot.spoken_units / voice).toFixed(2)} 字 / 检测人声秒`
          : "—";
      box.append(
        el(
          "article",
          { class: "quality-shot" },
          el("h3", {}, `镜头 ${shot.shot_id}`),
          el(
            "p",
            { class: "field-help" },
            `原片 ${seconds(shot.source.duration)} → 后期 ${seconds(shot.edited.duration)} · 台词密度 ${rate}`,
          ),
          timeline(speech, shot.source.duration, "人声保护", "speech-span"),
          timeline(keep, shot.source.duration, "保留区间", "keep-span"),
          (shot.plan?.reasons || []).map((text) =>
            el("small", { class: "muted" }, text),
          ),
          el(
            "details",
            {},
            el("summary", {}, "RMS 阈值复查"),
            el(
              "p",
              { class: "field-help" },
              `较严能量活动 ${percent(shot.analysis?.energy?.strict_activity_density)}；放松阈值后 ${percent(shot.analysis?.energy?.relaxed_activity_density)}。能量活动不等于人声，自动裁剪使用语音检测。`,
            ),
          ),
        ),
      );
    }
    box.append(
      ws.button("下载质检报告", () => download("媒体验收.json", report)),
    );
    const pages = report.review?.pages || [];
    if (pages.length)
      box.append(
        el("h2", {}, "总览、跳切与密集抽帧"),
        el(
          "div",
          { class: "review-pages" },
          pages.map((page) =>
            el(
              "a",
              {
                href: url(pid, `edits/${report.edit_id}/${page.file}`),
                target: "_blank",
                rel: "noopener",
              },
              el("img", {
                src: url(pid, `edits/${report.edit_id}/${page.file}`),
                loading: "lazy",
                alt:
                  {
                    overview: "镜头总览",
                    cuts: "切前切后对照",
                    frames: "时间标记审核帧",
                  }[page.kind] || "审核图",
              }),
              el(
                "span",
                {},
                {
                  overview: "镜头总览",
                  cuts: "跳切对照",
                  frames: "密集审核帧",
                }[page.kind] || page.kind,
              ),
            ),
          ),
        ),
      );
  }
  box.append(el("h2", {}, "后期版本"));
  if (!data.versions?.length)
    box.append(
      el(
        "p",
        { class: "muted" },
        "还没有后期版本。首次运行后会保留配方、原片快照与检查报告。",
      ),
    );
  for (const version of data.versions || [])
    box.append(
      el(
        "div",
        { class: "quality-version" },
        el(
          "div",
          {},
          el(
            "strong",
            {},
            `${PRESET_LABELS[version.preset] || "后期版本"}${data.current_edit?.id === version.id ? " · 当前成片" : ""}`,
          ),
          el(
            "small",
            { class: "muted" },
            `${version.created_at || version.id} · ${seconds(version.seconds)}`,
          ),
        ),
        el(
          "a",
          {
            class: "button",
            href: url(
              pid,
              `edits/${version.id}/${version.subtitled ? "成片_字幕版.mp4" : "成片.mp4"}`,
            ),
            target: "_blank",
            rel: "noopener",
          },
          "播放此版本",
        ),
        ws.button(
          "从冻结原片重建",
          async () => {
            if (ws.draft.dirty.size && !(await ws.saveAll())) return;
            await api(`/api/projects/${pid}/edits/${version.id}/rebuild`, {});
            ws.services.toast(
              "按该版本的旧剧本、冻结区间和原片重建，完成后更新当前播放版本。",
            );
            await ws.services.refresh();
          },
          false,
          { disabled: ws.busy },
        ),
      ),
    );
}
