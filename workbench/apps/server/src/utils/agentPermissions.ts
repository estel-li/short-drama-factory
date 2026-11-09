import { agentPermissionsSchema } from "@/lib/agentPermissions";
import conf from "@/utils/conf";
import { currentIdentity } from "@/utils/multiTenant/context";
import { isEnabled } from "@/utils/multiTenant/mode";

export function getAgentPermissions() {
  // 独立本机实例的开发选项不扩大多租户身份权限。
  if (isEnabled() || currentIdentity()) return agentPermissionsSchema.parse({});
  const value = agentPermissionsSchema.safeParse(conf.get("settings", {}).agentDeveloperPermissions ?? {});
  return value.success ? value.data : agentPermissionsSchema.parse({});
}
