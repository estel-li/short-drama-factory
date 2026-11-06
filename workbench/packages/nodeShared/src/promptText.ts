import type { AnyTagProps } from "x-sender";

export function getPromptText(value: AnyTagProps[][], resolveReference?: (id: string) => string) {
  return value.map(line => line.map(tag => {
    if (tag.type === "Write") return tag.text;
    if (tag.type === "Input") return tag.text || tag.placeholder;
    if (tag.type !== "Custom") {
      const prefix = tag.type === "Mention" ? "@" : tag.type === "Trigger" ? tag.key : "";
      return prefix + tag.name;
    }
    const content = document.createElement("template");
    content.innerHTML = tag.html;
    for (const reference of content.content.querySelectorAll<HTMLElement>(".imageReference[data-value]")) {
      const id = reference.dataset.referenceId;
      reference.replaceWith(id && resolveReference ? resolveReference(id) : reference.dataset.value ?? "");
    }
    return content.content.textContent ?? "";
  }).join("")).join("\n");
}
