import test from "node:test";
import assert from "node:assert/strict";
import { ImageInputPicker, referenceCapabilities } from "../web/image-inputs.js";
import { ImageWorkspace } from "../web/images.js";

// Small DOM fixture for upload events and the rendered input controls.
class Element {
  constructor(tag, text = "") {
    Object.assign(this, { tag, text, children: [], listeners: {}, disabled: false, multiple: false, type: "", className: "", tabIndex: 0 });
  }
  append(child) { this.children.push(child); }
  replaceChildren(...children) { this.children = children; }
  setAttribute(key, value) { this[key] = value; }
  addEventListener(name, fn) { this.listeners[name] = fn; }
  matches(tags) { return tags.split(",").includes(this.tag); }
  querySelector(tags) { return this.children.find(child => child.matches(tags)) || this.children.map(child => child.querySelector(tags)).find(Boolean); }
  get textContent() { return this.text + this.children.map(child => child.textContent).join(""); }
}

function fixture(t, options = {}) {
  const previous = { document: globalThis.document, Node: globalThis.Node };
  globalThis.Node = Element;
  globalThis.document = { createElement: tag => new Element(tag), createTextNode: text => new Element("text", text) };
  t.after(() => Object.assign(globalThis, previous));
  const uploads = [], changes = [], busy = [];
  let pending;
  const picker = new ImageInputPicker({
    upload: async file => { uploads.push(file.name); return { id: file.name, name: file.name, url: "/" + file.name }; },
    onChange: async items => changes.push(items.map(item => item.id)),
    onBusy: value => busy.push(value), act: work => (pending = work()), ...options,
  });
  return { picker, uploads, changes, busy, pending: () => pending };
}
const file = name => ({ name, type: "image/png", size: 100 });

test("multi-file upload appends in order, removes duplicates, and reorders both ways", async t => {
  const { picker, uploads, changes, busy } = fixture(t);
  assert.equal(picker.root.querySelector("input").multiple, true);
  await picker.addFiles([file("actor"), file("outfit"), file("scene")]);
  await picker.addFiles([file("style")]);
  await picker.addItems([{ id: "actor" }, { id: "style" }]);
  assert.deepEqual(uploads, ["actor", "outfit", "scene", "style"]);
  assert.deepEqual(changes.at(-1), uploads);
  await picker.move(2, -1);
  assert.deepEqual(changes.at(-1), ["actor", "scene", "outfit", "style"]);
  await picker.move(0, 1);
  assert.deepEqual(changes.at(-1), ["scene", "actor", "outfit", "style"]);
  assert.match(picker.root.textContent, /已添加 4 \/ 10/);
  assert.match(picker.root.textContent, /<image1> · scene/);
  assert.deepEqual(busy, [true, false, true, false]);
});

test("drop and clipboard images use the same ordered multi-file uploader", async t => {
  const f = fixture(t);
  let prevented = 0;
  f.picker.root.listeners.drop({ preventDefault: () => prevented++, dataTransfer: { files: [file("actor"), file("scene")] } });
  await f.pending();
  f.picker.root.listeners.paste({ preventDefault: () => prevented++, clipboardData: { files: [file("outfit")] } });
  await f.pending();
  assert.deepEqual(f.changes.at(-1), ["actor", "scene", "outfit"]);
  assert.equal(prevented, 2);
  f.picker.root.listeners.paste({ preventDefault: () => assert.fail("text pastes must not be intercepted"), clipboardData: { files: [] } });
});

test("limits and unsupported files fail before upload; ten references remain supported", async t => {
  const { picker, uploads } = fixture(t);
  await assert.rejects(picker.addFiles([file("valid"), { ...file("large"), size: 8_000_001 }]), /8MB/);
  await assert.rejects(picker.addFiles([{ ...file("bad"), type: "image/gif" }]), /PNG/);
  await assert.rejects(picker.addFiles(Array.from({ length: 11 }, (_, i) => file(String(i)))), /最多添加 10/);
  assert.equal(uploads.length, 0);
  await picker.addFiles(Array.from({ length: 10 }, (_, i) => file(String(i))));
  assert.equal(picker.items.length, 10);
  await assert.rejects(picker.addFiles([file("overflow")]), /已添加 10/);
  assert.equal(uploads.length, 10);
});

test("upload failure retains earlier references and releases busy controls", async t => {
  const { picker, busy } = fixture(t, { upload: async f => {
    if (f.name === "fail") throw Error("upload failed");
    return { id: f.name, name: f.name };
  } });
  await assert.rejects(picker.addFiles([file("kept"), file("fail"), file("not-sent")]), /upload failed/);
  assert.deepEqual(picker.items.map(item => item.id), ["kept"]);
  assert.equal(picker.busy, false);
  assert.equal(picker.root.querySelector("input").disabled, false);
  assert.deepEqual(busy, [true, false]);
});

test("disabled and busy uploaders do not accept concurrent batches", async t => {
  let finish;
  const { picker } = fixture(t, { upload: f => new Promise(resolve => { finish = () => resolve({ id: f.name }); }) });
  const first = picker.addFiles([file("first")]);
  await picker.addFiles([file("ignored")]);
  finish(); await first;
  picker.disabled = true;
  await picker.addFiles([file("disabled")]);
  assert.deepEqual(picker.items.map(item => item.id), ["first"]);
});

test("switching to a single-image model preserves inputs and allows removing one at a time", async t => {
  const { picker } = fixture(t);
  await picker.addFiles([file("one"), file("two"), file("three")]);
  picker.maxItems = 1; picker.render();
  assert.equal(picker.root.querySelector("input").multiple, false);
  assert.match(picker.root.textContent, /已保留全部图片/);
  await picker.change(picker.items.slice(1));
  await picker.change(picker.items.slice(1));
  assert.deepEqual(picker.items.map(item => item.id), ["three"]);
  assert.doesNotMatch(picker.root.textContent, /已保留全部图片/);
});

test("model capabilities gate generation without dropping selected references", () => {
  assert.deepEqual(referenceCapabilities("future", { max_reference_images: 4, reference_modes: ["reference"] }), { maxItems: 4, modes: ["reference"] });
  const workspace = new ImageWorkspace(null, {});
  workspace.modelCatalog = { "sdxl-base": { name: "SDXL", max_reference_images: 1, reference_modes: ["edit"] } };
  workspace.controls = { image_model: { value: "sdxl-base" }, variant: {}, transparent: {}, ratio: {},
    reference_mode: { value: "reference", options: [{ value: "reference" }, { value: "edit" }] } };
  workspace.optimizeButton = {}; workspace.generateButton = {};
  workspace.references = [{ id: "one" }, { id: "two" }, { id: "three" }];
  workspace.syncReferenceMode();
  assert.equal(workspace.generateButton.disabled, true);
  assert.equal(workspace.controls.reference_mode.value, "edit");
  assert.equal(workspace.references.length, 3);
  workspace.controls.image_model.value = "qwen-image-2.1";
  workspace.syncReferenceMode();
  assert.equal(workspace.generateButton.disabled, false);
  assert.equal(workspace.references.length, 3);
});
