import { el, field } from "./api.js?v=3.9.0";

export function referenceCapabilities(modelId, spec = {}) {
  const qwen = isQwenModel(modelId, spec);
  return {
    maxItems: spec.max_reference_images ?? (qwen ? 10 : 1),
    modes: spec.reference_modes ?? (qwen ? ["reference", "edit"] : ["edit"]),
  };
}

export function isQwenModel(modelId, spec = {}) {
  return spec.architecture === "qwen_image_21" || ["qwen-image-2.1", "qwen-image-2.1-ud"].includes(modelId);
}

export async function imageFileData(file) {
  if (file.size > 8_000_000) throw Error("单张参考图最多 8MB，请缩小后上传。");
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result).split(",")[1]);
    reader.onerror = () => reject(Error("读取参考图失败，请重新选择。"));
    reader.readAsDataURL(file);
  });
}

export class ImageInputPicker {
  constructor({ items = [], upload, onChange, act, disabled = false, onBusy = () => {}, maxItems = 10 }) {
    Object.assign(this, { items, upload, onChange, act, disabled, onBusy, maxItems, busy: false });
    this.root = el("section", { class: "image-input-picker", "aria-label": "生成参考图" });
    this.root.addEventListener("dragover", event => {
      if (![...(event.dataTransfer?.types || [])].includes("Files")) return;
      event.preventDefault();
      event.dataTransfer.dropEffect = this.busy || this.disabled ? "none" : "copy";
    });
    this.root.addEventListener("drop", event => {
      event.preventDefault();
      this.addFiles(event.dataTransfer?.files || []);
    });
    this.root.addEventListener("paste", event => {
      const files = [...(event.clipboardData?.files || [])].filter(file => file.type.startsWith("image/"));
      if (!files.length) return;
      event.preventDefault();
      this.addFiles(files);
    });
    this.render();
  }
  async change(items) {
    if (items.length > this.maxItems && items.length >= this.items.length) throw Error(`当前模型最多添加 ${this.maxItems} 张参考图。`);
    await this.onChange(items);
    this.items = items;
    this.render();
  }
  async addItems(items) {
    const seen = new Set(this.items.map(item => item.id));
    const fresh = items.filter(item => !seen.has(item.id) && seen.add(item.id));
    if (fresh.length) await this.change([...this.items, ...fresh]);
  }
  addFiles(selected) {
    const files = [...selected];
    if (!files.length) return;
    return this.run(async () => {
      if (files.some(file => !["image/png", "image/jpeg", "image/webp"].includes(file.type))) throw Error("参考图支持 PNG、JPEG、WebP，请重新选择图片。");
      if (files.some(file => file.size > 8_000_000)) throw Error("单张参考图最多 8MB。");
      if (files.length + this.items.length > this.maxItems) throw Error(`当前模型最多添加 ${this.maxItems} 张参考图，已添加 ${this.items.length} 张。`);
      // Save each successful input so a later upload failure cannot discard it.
      for (const file of files) await this.addItems([await this.upload(file)]);
    });
  }
  move(index, offset) {
    const target = index + offset;
    if (target < 0 || target >= this.items.length) return;
    const items = [...this.items];
    [items[index], items[target]] = [items[target], items[index]];
    return this.change(items);
  }
  run(task) {
    if (this.busy || this.disabled) return;
    return this.act(async () => {
      this.busy = true; this.onBusy(true); this.render();
      try { await task(); }
      finally { this.busy = false; this.onBusy(false); this.render(); }
    });
  }
  render() {
    const blocked = this.disabled || this.busy;
    const input = el("input", { type: "file", accept: "image/png,image/jpeg,image/webp", multiple: this.maxItems > 1, disabled: blocked,
      onchange: event => this.addFiles(event.target.files) });
    const dropzone = el("div", { class: "image-input-dropzone", tabIndex: blocked ? -1 : 0, "aria-label": "拖入或粘贴参考图", "aria-disabled": String(blocked) },
      field(this.maxItems > 1 ? "添加参考图（可一次选择多张）" : "添加重绘原图（单张）", input),
      el("p", { class: "field-help" }, this.maxItems > 1 ? "也可将多张图片拖到此处，或点击此区域后粘贴图片；可分次追加。" : "也可拖入图片，或点击此区域后粘贴图片。"));
    this.root.replaceChildren(dropzone,
      el("p", { class: "image-input-count", role: "status", "aria-live": "polite" }, `已添加 ${this.items.length} / ${this.maxItems} 张参考图`),
      el("p", { class: "field-help" }, this.busy ? "正在保存参考图……" : this.maxItems === 1 ? "支持 PNG / JPEG / WebP，每张最多 8MB。原图会作为初始潜空间，重绘强度越低通常保留越多。" : "支持 PNG / JPEG / WebP，每张最多 8MB。按顺序用 <image1>、<image2> 引用；编辑原图时第一张是要修改的图片。"));
    if (this.items.length > this.maxItems) this.root.append(el("p", { class: "notice warning", role: "alert" }, `当前模型最多使用 ${this.maxItems} 张参考图。已保留全部图片，请切换多图模型或移除多余图片后生成。`));
    const grid = el("div", { class: "image-input-grid" });
    for (const [index, item] of this.items.entries()) {
      const action = (label, work, unavailable = false) => el("button", { disabled: blocked || unavailable, onclick: () => this.run(work) }, label);
      grid.append(el("figure", { class: "image-input-card" }, el("img", { src: item.url, alt: `参考图 ${index + 1}：${item.name}` }),
        el("figcaption", {}, `<image${index + 1}> · ${item.name}`),
        el("div", { class: "actions" },
          action(`移除参考图 ${index + 1}`, () => this.change(this.items.filter((_, i) => i !== index))),
          action(`上移参考图 ${index + 1}`, () => this.move(index, -1), index === 0),
          action(`下移参考图 ${index + 1}`, () => this.move(index, 1), index === this.items.length - 1))));
    }
    this.root.append(grid);
    if (this.items.length > 3) this.root.append(el("p", { class: "notice warning" }, "多图会增加显存和耗时。16GB 显存建议先用 1～3 张、512 或 768 档。"));
  }
}
