<template>
  <div class="gpuLimits">
    <p class="hint">生成 NVIDIA 显卡限功率或核心频率命令。请在运行 ComfyUI 的电脑上，以管理员身份打开 PowerShell，粘贴执行；网页只生成命令，复制不代表已生效。</p>
    <el-form labelPosition="top" @submit.prevent>
      <div class="fields">
        <el-form-item label="GPU 编号">
          <el-input v-model="gpuIndex" aria-label="GPU 编号" inputmode="numeric" placeholder="查询结果中的 index，从 0 开始" />
        </el-form-item>
        <el-form-item label="限制方式">
          <el-select v-model="mode" aria-label="限制方式">
            <el-option label="限制功率（W）" value="power" />
            <el-option label="限制核心频率（MHz）" value="clock" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="mode === 'power'" label="功率上限（W）">
          <el-input v-model="powerLimit" aria-label="功率上限（W）" inputmode="decimal" placeholder="按查询结果填写" />
        </el-form-item>
        <el-form-item v-else label="核心频率上限（MHz）">
          <el-input v-model="clockLimit" aria-label="核心频率上限（MHz）" inputmode="numeric" placeholder="按显卡支持的频率填写" />
        </el-form-item>
      </div>
    </el-form>
    <p class="hint" v-if="mode === 'power'">先查询显卡编号及默认、最小、最大功率。填写范围内的瓦数；想降低功耗，请选低于默认功率的值。</p>
    <p class="hint" v-else>先查询支持的频率，再填写目标上限。命令使用 0 到目标值的核心频率范围，由驱动选择接近的可用频率；不调整显存频率。</p>
    <el-alert v-if="validationMessage" :title="validationMessage" type="info" :closable="false" />
    <div v-for="item in commands" :key="item.title" class="commandCard">
      <div class="commandHeading">
        <strong>{{ item.title }}</strong>
        <el-button size="small" :disabled="!item.command" @click="copyCommand(item.command)">复制{{ item.title }}</el-button>
      </div>
      <el-input :modelValue="item.command" type="textarea" readonly :autosize="{ minRows: 2, maxRows: 6 }" :aria-label="item.title" placeholder="填写有效参数后显示命令" />
    </div>
    <p class="hint">设置影响所选整张显卡上的所有程序，可能降低生成速度。具体支持情况取决于显卡和驱动；返回 N/A 或 Not Supported 时，该项不可用。执行后用查询命令复核，重启后重新检查。恢复命令只恢复当前所选的功率或核心频率。</p>
    <el-link href="https://docs.nvidia.com/deploy/nvidia-smi/index.html" target="_blank" rel="noopener noreferrer">NVIDIA 官方命令说明</el-link>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from "vue";
import { ElMessage } from "element-plus";
import { translate } from "@toonflow/i18n/vue";
import { writeClipboardText } from "@/lib/clipboard";

const gpuIndex = ref("0");
const mode = ref<"power" | "clock">("power");
const powerLimit = ref("");
const clockLimit = ref("");
const validGpu = computed(() => /^(0|[1-9]\d*)$/.test(gpuIndex.value) && Number.isSafeInteger(Number(gpuIndex.value)));
const validLimit = computed(() => {
  const value = mode.value === "power" ? powerLimit.value : clockLimit.value;
  const pattern = mode.value === "power" ? /^\d+(\.\d{1,2})?$/ : /^\d+$/;
  return pattern.test(value) && Number(value) > 0 && Number(value) <= Number.MAX_SAFE_INTEGER;
});
const validationMessage = computed(() => {
  if (!validGpu.value) return translate("GPU 编号必须是从 0 开始的整数");
  if (!validLimit.value) return translate(mode.value === "power" ? "请填写大于 0 的功率，最多两位小数" : "请填写大于 0 的整数频率");
  return "";
});
const commands = computed(() => {
  const prefix = `nvidia-smi -i ${Number(gpuIndex.value)}`;
  const query = "nvidia-smi --query-gpu=index,name,power.limit,power.default_limit,power.min_limit,power.max_limit,clocks.gr --format=csv";
  const setting = mode.value === "power" ? `${prefix} -pl ${Number(powerLimit.value)}` : `${prefix} -lgc 0,${Number(clockLimit.value)}`;
  const reset = mode.value === "clock" ? `${prefix} -rgc`
    : `$gpuDefaultPower = ${prefix} --query-gpu=power.default_limit --format=csv,noheader,nounits; if ($LASTEXITCODE -eq 0 -and $gpuDefaultPower -match '^\\d+(\\.\\d+)?$') { ${prefix} -pl $gpuDefaultPower } else { Write-Error 'Cannot read default GPU power limit.' }`;
  return [
    { title: translate("查询命令"), command: query + (mode.value === "clock" && validGpu.value ? `\n${prefix} -q -d SUPPORTED_CLOCKS` : "") },
    { title: translate("设置命令"), command: validGpu.value && validLimit.value ? setting : "" },
    { title: translate("恢复默认命令"), command: validGpu.value ? reset : "" },
  ];
});
async function copyCommand(command: string) {
  if (!command) return;
  try {
    await writeClipboardText(command);
    ElMessage.success(translate("命令已复制，请在管理员 PowerShell 中执行"));
  } catch {
    ElMessage.error(translate("复制失败，请手动选择命令文本复制"));
  }
}
</script>

<style scoped lang="scss">
.gpuLimits {
  display: flex;
  flex-direction: column;
  gap: 12px;
  .hint { margin: 0; color: var(--el-text-color-secondary); line-height: 1.7; }
  .fields { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; .el-form-item { margin: 0; } }
  .commandCard {
    padding: 12px;
    border: 1px solid var(--el-border-color);
    border-radius: 8px;
    .commandHeading { display: flex; align-items: center; justify-content: space-between; gap: 8px; margin-bottom: 10px; }
    :deep(textarea) { font-family: monospace; overflow-wrap: anywhere; }
  }
  .el-link { align-self: flex-start; }
  @media (max-width: 700px) { .fields { grid-template-columns: 1fr; } }
}
</style>
