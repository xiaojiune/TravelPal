<template>
  <div class="tool-result-card">
    <!-- 错误型：工具调用失败 -->
    <div v-if="isError" class="trc-error">
      ⚠️ {{ data.error }}
    </div>

    <!-- 任务型：异步任务提交（get_plan/add_poi/remove_poi 等），返回 task_id 待轮询 -->
    <div v-else-if="isTask" class="trc-task">
      <div class="trc-title">⏳ 任务已提交</div>
      <div class="trc-row">ID：{{ data.task_id }}</div>
      <div class="trc-row">状态：{{ data.status }}</div>
    </div>

    <!-- POI 型：查询到单个/多个 POI（poi_lookup 批量返回数组） -->
    <div v-else-if="isPoi" class="trc-poi">
      <div v-for="(item, i) in poiItems" :key="i" class="trc-poi-item">
        <div class="trc-poi-header">
          <n-tag :type="item.poi_type === 'hotel' ? 'success' : item.poi_type === 'facility' ? 'warning' : 'primary'" size="small">
            {{ typeLabel(item.poi_type) }}
          </n-tag>
          <span class="trc-poi-name">{{ item.name }}</span>
        </div>
        <div class="trc-poi-detail">📍 {{ item.address }}</div>
        <div class="trc-poi-detail">
          {{ item.lon?.toFixed(4) }}, {{ item.lat?.toFixed(4) }}
          <template v-if="item.tw_start != null && item.tw_end != null">
            · {{ fmtClock(item.tw_start!) }}~{{ fmtClock(item.tw_end!) }}
          </template>
        </div>
      </div>
    </div>

    <!-- 路程型：get_driving 两点间驾车距离/耗时 -->
    <div v-else-if="isDriving" class="trc-driving">
      <div class="trc-title">🚗 驾车路线</div>
      <div v-if="data.origin_name && data.destination_name" class="trc-row trc-route">
        {{ data.origin_name }} → {{ data.destination_name }}
      </div>
      <div class="trc-row">
        距离 {{ data.distance_km }} km · 耗时约 {{ data.duration_min }} 分钟
      </div>
    </div>

    <!-- 兜底型：结构未知，JSON 直出 -->
    <div v-else class="trc-raw">
      <pre>{{ rawJson }}</pre>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * 通用工具结果卡片：按 tool_result 数据结构判别渲染四种类型。
 *
 * 类型判别（顺序敏感）：
 * - 错误型：含 error 字段
 * - 任务型：含 task_id 字段（异步任务提交，待轮询 get_plan_result）
 * - POI 型：单对象含 name/poi_type 或数组元素含 poi_type（poi_lookup 批量）
 * - 路程型：含 distance_km 且含 duration_min（get_driving）
 * - 兜底型：结构未知，JSON 原样展示
 *
 * Props:
 *   data: unknown — tool_result 事件数据
 */
import { computed } from 'vue'

const props = defineProps<{ data: unknown }>()

/** 分钟 → "H:MM" 时钟格式。 */
function fmtClock(m: number): string {
  return `${Math.floor(m / 60)}:${String(m % 60).padStart(2, '0')}`
}

/** POI 类型中文标签。 */
function typeLabel(t?: string): string {
  if (t === 'hotel') return '🏨 酒店'
  if (t === 'facility') return '🍴 设施'
  return '🏛️ 景点'
}

const data = computed<Record<string, unknown>>(() =>
  props.data && typeof props.data === 'object' ? (props.data as Record<string, unknown>) : {}
)

const isError = computed(() => 'error' in data.value && !!data.value.error)
const isTask = computed(() => !isError.value && 'task_id' in data.value)
const isDriving = computed(
  () => !isError.value && !isTask.value && 'distance_km' in data.value && 'duration_min' in data.value
)
const isPoi = computed(() => {
  if (isError.value || isTask.value || isDriving.value) return false
  const d = data.value
  if (Array.isArray(d)) return d.length > 0 && typeof d[0] === 'object' && d[0] !== null && 'poi_type' in (d[0] as Record<string, unknown>)
  return typeof d === 'object' && d !== null && ('poi_type' in d || 'name' in d)
})
const poiItems = computed<Array<Record<string, any>>>(() => {
  const d = data.value
  if (Array.isArray(d)) return d as Array<Record<string, any>>
  return [d]
})
const rawJson = computed(() => JSON.stringify(props.data, null, 2))
</script>

<style scoped>
.tool-result-card {
  border: 1px solid var(--tp-card-border);
  border-radius: 8px;
  background: var(--tp-bg-card);
  padding: 10px 12px;
  font-size: 12px;
  line-height: 1.7;
  max-width: 100%;
}
.trc-error {
  color: var(--tp-error);
}
.trc-title {
  font-weight: 600;
  margin-bottom: 4px;
}
.trc-row {
  color: var(--tp-text-2);
}
.trc-route {
  font-weight: 500;
  color: var(--tp-text);
  margin-bottom: 2px;
}
.trc-poi-item + .trc-poi-item {
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px dashed var(--tp-border);
}
.trc-poi-header {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 2px;
  flex-wrap: wrap;
}
.trc-poi-name {
  font-weight: 600;
  color: var(--tp-text);
}
.trc-poi-detail {
  color: var(--tp-text-2);
}
.trc-raw pre {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-all;
  color: var(--tp-text-2);
}
</style>
