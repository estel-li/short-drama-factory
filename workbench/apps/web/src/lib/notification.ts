import axios from "axios";
import type { DesktopRuntime } from "@toonflow/server/desktop";
import { generalSettings } from "@/stores/settings";
import { actualPlatform } from "./platform";

export function getNotificationPermission(): NotificationPermission | "unsupported" | "insecure" {
  if (actualPlatform.isDesktop) return "granted";
  if (!window.isSecureContext) return "insecure";
  if (!("Notification" in window)) return "unsupported";
  return Notification.permission;
}

export async function requestNotificationPermission() {
  const permission = getNotificationPermission();
  // ACT: 仅由设置中的点击事件请求授权，Agent 的后台事件不会弹出权限请求。
  return permission === "default" ? Notification.requestPermission() : permission;
}

export async function showNotification(options: Parameters<DesktopRuntime["showNotification"]>[0]): Promise<void> {
  if (!generalSettings.value.agentNotificationsEnabled) return;
  if (document.visibilityState === "visible" && document.hasFocus()) return;
  if (actualPlatform.isDesktop) {
    const { data } = await axios.post<{ code: number; message: string }>("/api/desktop/notification", options, {
      headers: { "x-toonflow-desktop": "1" },
    });
    if (data.code !== 200) throw new Error(data.message || "发送系统通知失败");
    return;
  }
  if (getNotificationPermission() !== "granted") return;
  new Notification(options.title, { body: options.body, silent: options.silent });
}
