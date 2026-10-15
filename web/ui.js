import { el } from "./api.js?v=2.4.1";
import { statusInfo } from "./state.js?v=2.4.1";

const paths = {
  film: ["M4 3h16v18H4z", "M4 7h16M4 17h16M8 3v18M16 3v18"],
  projects: ["M3 4h7l2 3h9v13H3z"],
  plus: ["M12 5v14M5 12h14"],
  series: ["M4 4h16v5H4zM4 12h16v8H4z"],
  settings: ["M4 7h16M4 17h16M8 4v6M16 14v6"],
  spark: ["m12 3 2.5 6.5L21 12l-6.5 2.5L12 21l-2.5-6.5L3 12l6.5-2.5z"],
  clock: ["M12 8v5l3 2", "M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0"],
  search: ["M21 21l-5-5", "M18 10a8 8 0 1 1-16 0 8 8 0 0 1 16 0"],
  play: ["m8 5 11 7-11 7z"],
  check: ["m5 12 4 4L19 6"],
  arrow: ["M5 12h14m-5-5 5 5-5 5"],
  close: ["m6 6 12 12M18 6 6 18"],
  save: ["M4 3h14l3 3v15H3V3zM7 3v6h10V3M7 21v-8h10v8"],
  upload: ["M12 16V3m-5 5 5-5 5 5M4 15v6h16v-6"],
  alert: ["m12 3 10 18H2zM12 9v5M12 17h.01"],
  image: ["M3 3h18v18H3zM3 16l5-5 5 5 3-3 5 5", "M9 7h.01"],
  trash: ["M3 6h18M9 6V3h6v3M5 6l1 15h12l1-15M10 10v7M14 10v7"],
};
export function icon(name) {
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  for (const [key, value] of Object.entries({
    viewBox: "0 0 24 24",
    fill: "none",
    stroke: "currentColor",
    "stroke-width": "1.7",
    "stroke-linecap": "round",
    "stroke-linejoin": "round",
    "aria-hidden": "true",
    class: "icon",
  }))
    svg.setAttribute(key, value);
  for (const d of paths[name] || paths.spark) {
    const path = document.createElementNS(svg.namespaceURI, "path");
    path.setAttribute("d", d);
    svg.append(path);
  }
  return svg;
}
export function badge(value) {
  const [label, tone] = statusInfo(value);
  return el(
    "span",
    { class: `badge ${tone}` },
    el("i", { "aria-hidden": "true" }),
    label,
  );
}
export function empty(title, description, action) {
  return el(
    "div",
    { class: "empty" },
    el("div", { class: "empty-icon" }, icon("film")),
    el("h2", {}, title),
    el("p", { class: "muted" }, description),
    action,
  );
}
export function tabs(items, selected, change, name = "内容分区") {
  const bar = el("div", { class: "tabs", role: "tablist", "aria-label": name });
  items.forEach((item) => {
    const node = el(
      "button",
      {
        role: "tab",
        "aria-selected": item.id === selected,
        tabIndex: item.id === selected ? 0 : -1,
        onclick: () => change(item.id),
      },
      item.label,
    );
    node.addEventListener("keydown", (event) => {
      if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key))
        return;
      event.preventDefault();
      const index = items.findIndex((value) => value.id === item.id);
      const next =
        event.key === "Home"
          ? 0
          : event.key === "End"
            ? items.length - 1
            : (index + (event.key === "ArrowRight" ? 1 : -1) + items.length) %
              items.length;
      change(items[next].id);
      queueMicrotask(() =>
        document
          .querySelector(
            `[role="tablist"][aria-label="${name}"] [role="tab"][aria-selected="true"]`,
          )
          ?.focus(),
      );
    });
    bar.append(node);
  });
  return bar;
}
export function dialog(title, description, choices) {
  return new Promise((resolve) => {
    const focus = document.activeElement,
      modal = el(
        "dialog",
        { class: "dialog", "aria-label": title },
        el("h2", {}, title),
        el("p", {}, description),
      );
    const close = (value) => {
      modal.close();
      modal.remove();
      focus?.focus();
      resolve(value);
    };
    modal.append(
      el(
        "div",
        { class: "actions" },
        choices.map((choice) =>
          el(
            "button",
            {
              class: choice.primary ? "primary" : choice.danger ? "danger" : "",
              onclick: () => close(choice.value),
            },
            choice.label,
          ),
        ),
      ),
    );
    modal.addEventListener("cancel", (event) => {
      event.preventDefault();
      close(null);
    });
    document.body.append(modal);
    modal.showModal();
  });
}
