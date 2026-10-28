import test from "node:test";
import assert from "node:assert/strict";
import { ImageWorkspace } from "../web/images.js";
import { referenceCapabilities, isQwenModel } from "../web/image-inputs.js";

const ud = "qwen-image-2.1-ud";
const plan = { image_model: ud, ready: false, local_download: true, variant: "quality-int8",
  selection: {}, requires_confirmation: true, confirmation_token: "ud-download-plan" };

function fixture(t, selected = ud) {
  const before = globalThis.fetch, calls = [], progress = [];
  t.after(() => { globalThis.fetch = before; });
  globalThis.fetch = async (path, options) => {
    calls.push({ path, body: JSON.parse(options.body) });
    return { ok: true, status: 200, json: async () => ({ job_id: "ud-preparation" }) };
  };
  const workspace = new ImageWorkspace(null, {});
  workspace.controls = { image_model: { value: selected } };
  workspace.modelCatalog = { [ud]: { auto_prepare_on_select: true } };
  workspace.refreshEnvironment = async () => plan;
  workspace.showProgress = session => progress.push(session);
  return { workspace, calls, progress };
}

test("selecting UD queues only preparation with the reviewed plan and opens progress", async t => {
  const { workspace, calls, progress } = fixture(t);
  await workspace.prepareSelectedModel();
  assert.deepEqual(calls, [{ path: "/api/images/environment/prepare", body: {
    image_model: ud, variant: "quality-int8", models: {}, download_confirmation: "ud-download-plan",
  } }]);
  assert.deepEqual(progress, [{ environment: true, jobId: "ud-preparation" }]);
  assert.equal(workspace.autoPreparing, false);
  assert.equal(isQwenModel(ud), true);
  assert.deepEqual(referenceCapabilities(ud), { maxItems: 10, modes: ["reference", "edit"] });
});

test("ready UD and other model selections do not start downloads", async t => {
  const { workspace, calls } = fixture(t);
  workspace.refreshEnvironment = async () => ({ ...plan, ready: true });
  await workspace.prepareSelectedModel();
  workspace.controls.image_model.value = "qwen-image-2.1";
  workspace.refreshEnvironment = async () => plan;
  await workspace.prepareSelectedModel();
  assert.deepEqual(calls, []);
});

test("switching models while checking does not download the abandoned selection", async t => {
  const { workspace, calls } = fixture(t);
  let resolve;
  workspace.refreshEnvironment = () => new Promise(done => { resolve = done; });
  const pending = workspace.prepareSelectedModel();
  workspace.controls.image_model.value = "sdxl-base";
  resolve(plan); await pending;
  assert.deepEqual(calls, []);
});

test("invalid or remote plans fail without starting a local download", async t => {
  const { workspace, calls } = fixture(t);
  workspace.refreshEnvironment = async () => ({ ...plan, selection_errors: ["missing model"] });
  await assert.rejects(workspace.prepareSelectedModel(), /missing model/);
  workspace.refreshEnvironment = async () => ({ ...plan, local_download: false });
  await assert.rejects(workspace.prepareSelectedModel(), /远端/);
  assert.deepEqual(calls, []);
});

test("a repeated selection cannot submit twice while preparation is being queued", async t => {
  const { workspace, progress } = fixture(t);
  let finish, count = 0;
  globalThis.fetch = async () => {
    count++;
    await new Promise(resolve => { finish = resolve; });
    return { ok: true, status: 200, json: async () => ({ job_id: "one" }) };
  };
  const first = workspace.prepareSelectedModel();
  await workspace.prepareSelectedModel();
  finish(); await first;
  assert.equal(count, 1);
  assert.equal(progress.length, 1);
});
