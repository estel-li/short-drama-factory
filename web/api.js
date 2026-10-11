export class ApiError extends Error {
  constructor(message, status = 0) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

export async function api(path, body, { signal } = {}) {
  let response;
  try {
    response = await fetch(path, {
      signal,
      ...(body === undefined
        ? {}
        : {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body),
          }),
    });
  } catch (error) {
    if (error.name === "AbortError") throw error;
    throw new ApiError("无法连接工作台。请确认应用正在运行，然后重试。");
  }
  let data;
  try {
    data = await response.json();
  } catch {
    throw new ApiError(
      `服务返回了异常响应（HTTP ${response.status}），请稍后重试。`,
      response.status,
    );
  }
  if (!response.ok) {
    const detail = data.detail;
    const message =
      data.error ||
      (Array.isArray(detail)
        ? detail
            .map(
              (item) =>
                `${item.loc?.filter((x) => x !== "body").join(" / ")}：${item.msg}`,
            )
            .join("\n")
        : detail) ||
      `请求失败（HTTP ${response.status}）。`;
    throw new ApiError(String(message), response.status);
  }
  return data;
}

export function el(tag, props = {}, ...children) {
  const node = document.createElement(tag);
  if (tag === "button") node.type = "button";
  for (const [key, value] of Object.entries(props)) {
    if (value === undefined || value === null) continue;
    if (key.startsWith("on"))
      node.addEventListener(key.slice(2).toLowerCase(), value);
    else if (key === "class") node.className = value;
    else if (key in node) node[key] = value;
    else node.setAttribute(key, value);
  }
  for (const child of children.flat())
    if (child !== null && child !== undefined)
      node.append(
        child instanceof Node ? child : document.createTextNode(String(child)),
      );
  return node;
}

let fieldId = 0;
export function field(text, input, help = "") {
  const control = input.matches?.("input,select,textarea")
    ? input
    : input.querySelector?.("input,select,textarea");
  if (control && !control.id) control.id = `field-${++fieldId}`;
  const hint = help
    ? el("small", { class: "field-help", id: `hint-${++fieldId}` }, help)
    : null;
  if (control && hint) control.setAttribute("aria-describedby", hint.id);
  return el(
    "div",
    { class: "field" },
    el("label", { htmlFor: control?.id }, text),
    input,
    hint,
  );
}

export function select(items, value) {
  return el(
    "select",
    {},
    items.map((item) => {
      const option =
        typeof item === "string" ? { value: item, label: item } : item;
      return el(
        "option",
        {
          value: option.value,
          selected: String(option.value) === String(value),
        },
        option.label,
      );
    }),
  );
}

export function download(name, value) {
  const url = URL.createObjectURL(
    new Blob([JSON.stringify(value, null, 2)], { type: "application/json" }),
  );
  const link = el("a", { href: url, download: name });
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
