import test from "node:test";
import assert from "node:assert/strict";
import {
  ProjectDraft,
  projectStatus,
  isBusy,
  continuationIssue,
  finishingPayload,
} from "../web/state.js";
import { api, ApiError, el } from "../web/api.js";

const project = () => ({
  id: "story",
  busy: false,
  settings: { seed: 12 },
  state: { status: "ready" },
  story: {
    title: "original",
    shots: [{ uid: "one", scene: "study", summary: "original" }],
  },
  outline_result: {
    title: "outline",
    premise: "story",
    beats: [{ description: "beat" }],
  },
});
test("editing settings survive polling and participate in save/discard protection", () => {
  const draft = new ProjectDraft(project());
  draft.data.quality.notes = '[{"start":0,"end":1.2,"text":"说明"}]';
  draft.data.quality.interval = 0.25;
  draft.mark("quality");
  const snapshot = draft.snapshot("quality");
  draft.ingest(project());
  assert.equal(draft.dirty.has("quality"), true);
  const payload = finishingPayload(draft.data.quality);
  assert.equal(payload.notes[0].text, "说明");
  assert.equal(payload.review_interval, 0.25);
  const saved = { ...project(), finishing_settings: payload };
  draft.commit("quality", snapshot.revision, saved);
  assert.equal(draft.dirty.size, 0);
  assert.deepEqual(finishingPayload(new ProjectDraft(saved).data.quality), payload);
  draft.data.quality.notes = "{broken";
  draft.mark("quality");
  assert.throws(() => finishingPayload(draft.data.quality), /原输入已保留/);
  draft.discard();
  assert.equal(finishingPayload(draft.data.quality).notes[0].text, "说明");
});
test("an unchanged poll preserves object references used by live input handlers", () => {
  const draft = new ProjectDraft(project()),
    boundShot = draft.data.story.shots[0];
  const next = project();
  next.state.message = "progress update";
  draft.ingest(next);
  assert.equal(draft.data.story.shots[0], boundShot);
  boundShot.summary = "typed after polling";
  draft.mark("story");
  assert.equal(
    draft.snapshot("story").value.shots[0].summary,
    "typed after polling",
  );
});

test("polling preserves all unsaved scopes and updates runtime progress", () => {
  const original = project(),
    draft = new ProjectDraft(original);
  draft.data.story.shots[0].summary = "unsaved";
  draft.mark("story");
  draft.data.settings.seed = 99;
  draft.mark("settings");
  draft.data.outline = "unsaved outline";
  draft.mark("outline");
  const next = project();
  next.state.status = "rendering";
  next.story.shots[0].summary = "server update";
  next.settings.seed = 200;
  draft.ingest(next);
  assert.equal(draft.data.story.shots[0].summary, "unsaved");
  assert.equal(draft.data.settings.seed, 99);
  assert.equal(draft.data.outline, "unsaved outline");
  assert.equal(draft.project.state.status, "rendering");
  assert.equal(original.story.shots[0].summary, "original");
});
test("saving one scope does not clear or replace other drafts", () => {
  const draft = new ProjectDraft(project());
  draft.data.story.title = "new title";
  draft.mark("story");
  draft.data.settings.seed = 88;
  draft.mark("settings");
  const saved = draft.snapshot("story"),
    next = project();
  next.story = saved.value;
  draft.commit("story", saved.revision, next);
  assert.deepEqual([...draft.dirty], ["settings"]);
  assert.equal(draft.data.settings.seed, 88);
  assert.equal(draft.data.story.title, "new title");
});
test("edits during a save remain dirty after the older response arrives", () => {
  const draft = new ProjectDraft(project());
  draft.data.story.title = "first edit";
  draft.mark("story");
  const saved = draft.snapshot("story");
  draft.data.story.title = "newer edit";
  draft.mark("story");
  const next = project();
  next.story = saved.value;
  draft.commit("story", saved.revision, next);
  assert.equal(draft.data.story.title, "newer edit");
  assert.equal(draft.dirty.has("story"), true);
});
test("discard uses the latest server snapshot", () => {
  const draft = new ProjectDraft(project());
  draft.data.settings.seed = 90;
  draft.mark("settings");
  const next = project();
  next.settings.seed = 55;
  draft.ingest(next);
  draft.discard();
  assert.equal(draft.data.settings.seed, 55);
  assert.equal(draft.dirty.size, 0);
});
test("queue status takes precedence and works when recent jobs are truncated", () => {
  const p = project();
  p.state.status = "complete";
  assert.equal(
    projectStatus(p, [{ project_id: p.id, status: "queued" }]),
    "queued",
  );
  p.busy = true;
  assert.equal(projectStatus(p, []), "queued");
  assert.equal(isBusy("retrying"), true);
  assert.equal(isBusy("paused"), false);
});
test("first-frame guidance follows the same scene and continuity boundaries", () => {
  const shots = [
    { scene: "study", continuity_group: "day" },
    { scene: "study", continuity_group: "day" },
  ];
  assert.match(continuationIssue(shots, 0), /第一镜/);
  assert.equal(continuationIssue(shots, 1), "");
  shots[1].scene = "street";
  assert.match(continuationIssue(shots, 1), /场景/);
  shots[1].scene = "study";
  shots[1].continuity_group = "night";
  assert.match(continuationIssue(shots, 1), /连续段/);
});
test("API network, invalid JSON, and validation failures are readable", async () => {
  const previous = globalThis.fetch;
  try {
    globalThis.fetch = async () => {
      throw Error("network");
    };
    await assert.rejects(
      api("/test"),
      (error) =>
        error instanceof ApiError && /无法连接工作台/.test(error.message),
    );
    globalThis.fetch = async () => ({
      status: 502,
      ok: false,
      json: async () => {
        throw Error("HTML");
      },
    });
    await assert.rejects(api("/test"), /HTTP 502/);
    globalThis.fetch = async () => ({
      status: 422,
      ok: false,
      json: async () => ({
        detail: [{ loc: ["body", "seed"], msg: "invalid seed" }],
      }),
    });
    await assert.rejects(api("/test"), /seed：invalid seed/);
    globalThis.fetch = async () => ({
      status: 200,
      ok: true,
      json: async () => ({ ok: true }),
    });
    assert.deepEqual(await api("/test"), { ok: true });
  } finally {
    globalThis.fetch = previous;
  }
});
test("ordinary buttons cannot accidentally submit a surrounding form", () => {
  const previousDocument = globalThis.document,
    previousNode = globalThis.Node;
  class Node {
    constructor(tag) {
      this.tag = tag;
      this.type = "submit";
      this.children = [];
    }
    append(child) {
      this.children.push(child);
    }
    setAttribute() {}
    addEventListener() {}
  }
  globalThis.Node = Node;
  globalThis.document = {
    createElement: (tag) => new Node(tag),
    createTextNode: (text) => new Node(text),
  };
  try {
    assert.equal(el("button", {}, "save").type, "button");
    assert.equal(el("button", { type: "submit" }, "create").type, "submit");
    assert.equal(el("div", {}, null, undefined, "text").children.length, 1);
  } finally {
    globalThis.document = previousDocument;
    globalThis.Node = previousNode;
  }
});
import { ImageWorkspace } from '../web/images.js';

test('offline engine with local models proceeds without a download dialog', async () => {
  const previousFetch = globalThis.fetch;
  const calls = [], sessions = [];
  const workspace = new ImageWorkspace({}, { toast() {} });
  workspace.optimizeButton = {}; workspace.generateButton = {};
  workspace.read = () => ({ prompt: 'local models', optimize: false, variant: 'auto', models: {} });
  workspace.refresh = async () => {};
  workspace.showProgress = session => sessions.push(session);
  globalThis.fetch = async (path, options) => {
    calls.push({ path, body: JSON.parse(options.body) });
    return { ok: true, status: 200, json: async () => path.endsWith('/plan')
      ? { ready: false, local_download: true, requires_confirmation: false, download_bytes: 0, confirmation_token: 'local' }
      : { id: 'one', job_id: 'one-job' } };
  };
  try {
    // No document/DOM exists here: a download dialog would fail the test.
    await workspace.submit(false);
    assert.deepEqual(calls.map(c => c.path), ['/api/images/environment/plan', '/api/images']);
    assert.equal(calls[1].body.download_confirmation, 'local');
    assert.deepEqual(sessions, [{ imageId: 'one' }]);
    assert.equal(workspace.draftId, 'one');
  } finally { globalThis.fetch = previousFetch; }
});

test('optimized image continues the original record and retains edited prompt', async () => {
  const previousFetch = globalThis.fetch;
  const calls = [];
  let request = { prompt: 'a room', optimize: true, optimized_prompt: '', variant: 'auto', models: {}, seed: null };
  const workspace = new ImageWorkspace({}, { toast() {} });
  workspace.optimizeButton = {}; workspace.generateButton = {};
  workspace.read = () => ({ ...request });
  workspace.refresh = async () => { workspace.draftBusy = false; };
  globalThis.fetch = async (path, options) => {
    calls.push({ path, body: options.body && JSON.parse(options.body) });
    const result = path === '/api/images/original'
      ? { id: 'original', status: 'ready', busy: false, optimized_prompt: 'machine output' }
      : path === '/api/images/environment/plan' ? { ready: true, confirmation_token: 'plan' }
      : { id: 'original', job_id: 'same-job' };
    return { ok: true, status: 200, json: async () => result };
  };
  try {
    await workspace.submit(true);
    assert.equal(workspace.draftId, 'original');
    request.optimized_prompt = 'edited by user';
    await workspace.submit(false);
    assert.equal(calls.filter(c => c.path === '/api/images').length, 1);
    const continued = calls.find(c => c.path === '/api/images/original/generate');
    assert.equal(continued.body.request.optimized_prompt, 'edited by user');
    assert.equal(continued.body.optimize_only, false);
    assert.equal(workspace.draftId, 'original');
  } finally { globalThis.fetch = previousFetch; }
});

test('double-click optimization sends once and retains the revision submitted', async () => {
  const previousFetch = globalThis.fetch;
  let finish, writes = 0;
  const workspace = new ImageWorkspace({}, { toast() {} });
  workspace.optimizeButton = {}; workspace.generateButton = {};
  workspace.read = () => ({ prompt: 'old draft', optimize: true });
  workspace.refresh = async () => {};
  globalThis.fetch = async () => {
    writes++;
    await new Promise(resolve => { finish = resolve; });
    return { ok: true, status: 200, json: async () => ({ id: 'original', job_id: 'job' }) };
  };
  try {
    const first = workspace.submit(true);
    await workspace.submit(true);
    workspace.revision++;
    finish(); await first;
    assert.equal(writes, 1);
    assert.equal(workspace.pendingOptimize.revision, 0);
    assert.equal(workspace.revision, 1);
    assert.equal(workspace.generateButton.disabled, true);
    await workspace.submit(false);
    assert.equal(writes, 1);
  } finally { globalThis.fetch = previousFetch; }
});
