import { el, field } from "./api.js?v=3.9.0";

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
    this.render();
  }
  async change(items) {
    if (items.length > this.maxItems) throw Error(`当前模型最多添加 ${this.maxItems} 张参考图。`);
    await this.onChange(items);
    this.items = items;
    this.render();
  }
  async addItems(items) {
    const seen = new Set(this.items.map(item => item.id));
    const fresh = items.filter(item => !seen.has(item.id) && seen.add(item.id));
    if (fresh.length) await this.change([...this.items, ...fresh]);
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
      onchange: event => {
        const files = [...event.target.files];
        this.run(async () => {
          if (files.length + this.items.length > this.maxItems) throw Error(`当前模型最多添加 ${this.maxItems} 张参考图。`);
          if (files.some(file => file.size > 8_000_000)) throw Error("单张参考图最多 8MB。");
          for (const file of files) await this.addItems([await this.upload(file)]);
        });
      } });
    this.root.replaceChildren(field(this.maxItems > 1 ? "上传参考图（可多选）" : "上传重绘原图（单张）", input),
      el("p", { class: "field-help" }, this.busy ? "正在保存参考图……" : this.maxItems === 1 ? "支持 PNG / JPEG / WebP，每张最多 8MB。原图会作为初始潜空间，重绘强度越低通常保留越多。" : "支持 PNG / JPEG / WebP，每张最多 8MB。按顺序用 <image1>、<image2> 引用；编辑原图时第一张是要修改的图片。"));
    const grid = el("div", { class: "image-input-grid" });
    for (const [index, item] of this.items.entries()) {
      const action = (label, work, unavailable = false) => el("button", { disabled: blocked || unavailable, onclick: () => this.run(work) }, label);
      grid.append(el("figure", { class: "image-input-card" }, el("img", { src: item.url, alt: `参考图 ${index + 1}：${item.name}` }),
        el("figcaption", {}, `<image${index + 1}> · ${item.name}`),
        el("div", { class: "actions" },
          action(`移除参考图 ${index + 1}`, () => this.change(this.items.filter((_, i) => i !== index))),
          action(`上移参考图 ${index + 1}`, () => { const items = [...this.items]; [items[index - 1], items[index]] = [items[index], items[index - 1]]; return this.change(items); }, index === 0))));
    }
    this.root.append(grid);
    if (this.items.length > 3) this.root.append(el("p", { class: "notice warning" }, "多图会增加显存和耗时。16GB 显存建议先用 1～3 张、512 或 768 档。"));
  }
}
