<template>
  <div v-if="formState.rules.length" class="modelForm">
    <form-create :key="formState.key" v-model="other" :rule="formState.rules" :option="formOptions" />
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import formCreate, { type Options } from "@form-create/element-ui";
import {
  ElForm, ElFormItem, ElRow, ElCol, ElInput, ElInputNumber, ElSwitch,
  ElSelect, ElOption, ElCheckbox, ElCheckboxGroup, ElRadio, ElRadioGroup,
} from "element-plus";
import type { NodeMediaModel } from "@toonflow/nodes-scaffold/runtime";

const props = defineProps<{ rules?: NodeMediaModel["rules"]; disabled?: boolean }>();
const other = defineModel<Record<string, unknown>>({ required: true });
const formState = computed(() => ({ rules: formCreate.copyRules(props.rules ?? []), key: Symbol() }));
const formOptions = computed<Options>(() => ({
  form: { labelPosition: "top", size: "small", disabled: props.disabled },
  appendValue: false,
  submitBtn: false,
  resetBtn: false,
}));

for (const [name, component] of Object.entries({
  "el-form": ElForm, "el-form-item": ElFormItem, "el-row": ElRow, "el-col": ElCol,
  "el-input": ElInput, "el-input-number": ElInputNumber, "el-switch": ElSwitch,
  "el-select": ElSelect, "el-option": ElOption, "el-checkbox": ElCheckbox,
  "el-checkbox-group": ElCheckboxGroup, "el-radio": ElRadio, "el-radio-group": ElRadioGroup,
})) formCreate.component(name, component);
</script>

<style scoped lang="scss">
.modelForm {
  margin-top: 14px;
  padding-top: 14px;
  border-top: 1px solid var(--el-border-color-lighter);

  :deep(.el-form-item) {
    margin-bottom: 14px;

    .el-form-item__label {
      margin-bottom: 8px;
      padding: 0;
      color: var(--el-text-color-secondary);
      font-size: 12px;
      font-weight: 500;
    }

    .el-select, .el-input-number { width: 100%; }
  }

  :deep(.el-row > .el-col:last-child .el-form-item) { margin-bottom: 0; }
}
</style>
