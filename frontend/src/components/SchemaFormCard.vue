<template>
  <div class="schema-form-card">
    <div v-if="title" class="form-title">{{ title }}</div>
    <div class="form-fields">
      <div v-for="(prop, name) in schema.properties" :key="name" class="form-item">
        <label class="form-label">
          {{ name }}
          <span v-if="isRequired(name)" class="req-star">*</span>
        </label>
        <!-- 字符串 / 整数 / 数字 / 布尔 / 数组 / 对象 六型分发 -->
        <n-input
          v-if="prop.type === 'string'"
          v-model:value="form[name]"
          :placeholder="prop.description"
          :disabled="disabled"
          @update:value="emitChange"
        />
        <n-input-number
          v-else-if="prop.type === 'integer' || prop.type === 'number'"
          v-model:value="form[name]"
          :placeholder="prop.description"
          :disabled="disabled"
          style="width: 100%"
          @update:value="emitChange"
        />
        <n-switch
          v-else-if="prop.type === 'boolean'"
          v-model:value="form[name]"
          :disabled="disabled"
          @update:value="emitChange"
        />
        <n-input
          v-else-if="prop.type === 'array'"
          v-model:value="arrayText[name]"
          :placeholder="prop.description || 'JSON 数组'"
          :disabled="disabled"
          @update:value="onArrayChange(name)"
        />
        <n-input
          v-else
          v-model:value="objectText[name]"
          type="textarea"
          :rows="2"
          :placeholder="prop.description || 'JSON 对象'"
          :disabled="disabled"
          @update:value="onObjectChange(name)"
        />
        <div v-if="prop.description && !isSimple(prop.type)" class="form-desc">{{ prop.description }}</div>
      </div>
    </div>
    <div v-if="hint" class="form-hint">{{ hint }}</div>
  </div>
</template>

<script setup lang="ts">
/**
 * Schema 驱动表单卡片（ADR-009 §5 路线 A：JSON Schema 驱动表单）。
 *
 * 输入为 OpenAI function parameters 片段（properties + required），按字段
 * type 分发渲染 Naive UI 控件（string→n-input / integer|number→n-input-number
 * / boolean→n-switch / array→JSON 输入 / object→textarea JSON），required 标星。
 *
 * 当前仅组件就绪态：2b 阶段不接触发场景（Agent 尚未按 schema 产出表单事件），
 * 待 v1.1 接入 add_poi/get_plan 等工具的 Form Card 触发后启用。
 *
 * Props:
 *   schema: ToolSchema — parameters 结构 {type:'object', properties, required}
 *   title: string?     — 卡片标题（工具名），可选
 *   disabled: boolean  — 是否禁用编辑，默认 false
 *   hint: string?      — 底部提示文案，可选
 * ModelValue:
 *   Record<string, unknown> — 表单提交结果（仅含已填字段）
 */
import { reactive, ref, watch } from 'vue'

export interface ToolSchemaProperty {
  type: string
  description?: string
  items?: { type: string }
}
export interface ToolSchema {
  type: 'object'
  properties: Record<string, ToolSchemaProperty>
  required?: string[]
}

const props = withDefaults(
  defineProps<{
    schema: ToolSchema
    title?: string
    disabled?: boolean
    hint?: string
    modelValue?: Record<string, unknown>
  }>(),
  { title: '', disabled: false, hint: '', modelValue: () => ({}) },
)
const emit = defineEmits<{ (e: 'update:modelValue', value: Record<string, unknown>): void }>()

// 原始表单值：简单类型直接存，复杂类型（array/object）存文本由解析回填
const form = reactive<Record<string, unknown>>({})
const arrayText = reactive<Record<string, string>>({})
const objectText = reactive<Record<string, string>>({})

function isRequired(name: string): boolean {
  return !!props.schema.required?.includes(name)
}
/** 简单类型（无需 textarea 辅助描述）：string/integer/number/boolean */
function isSimple(type: string): boolean {
  return type === 'string' || type === 'integer' || type === 'number' || type === 'boolean'
}

/** 文本输入变更：解析 JSON 数组回填 form 并 emit */
function onArrayChange(name: string) {
  try {
    form[name] = JSON.parse(arrayText[name])
  } catch {
    form[name] = undefined
  }
  emitChange()
}
/** 文本输入变更：解析 JSON 对象回填 form 并 emit */
function onObjectChange(name: string) {
  try {
    form[name] = JSON.parse(objectText[name])
  } catch {
    form[name] = undefined
  }
  emitChange()
}

/** 汇总非空字段并 emit 到父组件 */
function emitChange() {
  const result: Record<string, unknown> = {}
  for (const [k, v] of Object.entries(form)) {
    if (v !== undefined && v !== '') result[k] = v
  }
  emit('update:modelValue', result)
}

// schema 或外部 modelValue 变化时重建表单（外部回填 / 重置）
watch(
  () => [props.schema, props.modelValue] as const,
  () => {
    for (const name of Object.keys(props.schema.properties)) {
      const incoming = props.modelValue?.[name]
      if (incoming !== undefined) {
        form[name] = incoming
        if (Array.isArray(incoming)) arrayText[name] = JSON.stringify(incoming)
        else if (typeof incoming === 'object') objectText[name] = JSON.stringify(incoming)
        else if (typeof incoming === 'string') arrayText[name] = incoming
      }
    }
  },
  { immediate: true, deep: true },
)
</script>

<style scoped>
.schema-form-card {
  border: 1px solid var(--tp-border);
  border-radius: 8px;
  padding: 12px;
  background: var(--tp-surface);
}
.form-title {
  font-size: 13px;
  font-weight: 600;
  margin-bottom: 10px;
  color: var(--tp-text);
}
.form-fields {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.form-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.form-label {
  font-size: 12px;
  color: var(--tp-text-2);
}
.req-star {
  color: var(--tp-error);
  margin-left: 2px;
}
.form-desc {
  font-size: 11px;
  color: var(--tp-text-3);
}
.form-hint {
  margin-top: 10px;
  font-size: 11px;
  color: var(--tp-text-3);
}
</style>
