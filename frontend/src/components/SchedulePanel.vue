<template>
  <div class="schedule-panel">
    <h3>每日行程</h3>
    <div v-if="!dailySchedules?.length" class="empty">暂无行程数据</div>
    <div v-for="(day, di) in dailySchedules" v-else :key="di" class="day-section">
      <h4 class="day-title" :class="{ 'day-active': activeDay === di }" @click="toggleDay(di)">第 {{ di + 1 }} 天<span class="day-hint">{{ collapsedDays.has(di) ? '展开' : '收起' }}{{ activeDay === di ? ' (当前)' : '' }}</span></h4>
      <table v-show="!collapsedDays.has(di)" class="schedule-table">
        <thead>
          <tr>
            <th>景点</th>
            <th>到达</th>
            <th>离开</th>
            <th>营业时间</th>
            <th>停留</th>
            <th>到达状态</th>
            <th>离开状态</th>
            <th v-if="onRemovePoi"></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(item, ii) in day" :key="ii" :class="{ 'depot-row': item.name === '酒店（返回）' || item.name === '酒店（出发）' }" :style="{ cursor: item.name !== '酒店（返回）' && item.name !== '酒店（出发）' ? 'pointer' : '' }" @click="item.name !== '酒店（返回）' && item.name !== '酒店（出发）' && emit('select-spot', item.name)">
            <td>{{ item.name }}</td>
            <td>{{ fmt(item.arrival) }}</td>
            <td>{{ fmt(item.departure) }}</td>
            <td>{{ item.tw || '-' }}</td>
            <td>{{ item.stay ?? '-' }}</td>
            <td :class="statusColor(item.arrival_status)">{{ statusClass(item.arrival_status) }}</td>
            <td :class="statusColor(item.departure_status)">{{ statusClass(item.departure_status) }}</td>
            <td v-if="onRemovePoi && item.name !== '酒店（返回）'">
              <button class="btn-remove" title="移除景点" @click="onRemovePoi(item.name)">✕</button>
            </td>
            <td v-else-if="onRemovePoi"></td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * 每日行程面板组件。
 * 以表格形式展示每日景点到达/离开/状态。
 *
 * Props:
 *   dailySchedules: ScheduleItem[][]  — 每日行程，每项含 name/arrival/departure/tw/stay/status
 *   onRemovePoi: ((name: string) => void) | null  — 移除景点回调，null 时不显示移除按钮
 */
import { ref, watch } from 'vue'
import type { ScheduleItem } from '@/types'

// ====== 工具函数 ======

const props = defineProps<{
  dailySchedules?: ScheduleItem[][]
  onRemovePoi?: ((name: string) => void) | null
  /** 当前高亮日索引，-1 表示全部显示。用于在标题上标记选中状态。 */
  activeDay?: number
}>()

const emit = defineEmits<{
  (e: 'select-day', dayIndex: number): void
  (e: 'select-spot', spotName: string): void
}>()

/** 已折叠的天数集合，默认展开第 1 天。 */
const collapsedDays = ref<Set<number>>(new Set())

function resetCollapsed() {
  const n = props.dailySchedules?.length || 0
  collapsedDays.value = new Set(Array.from({ length: n }, (_, i) => i).filter(i => i !== 0))
}
resetCollapsed()
watch(() => props.dailySchedules, resetCollapsed)

function toggleDay(di: number) {
  const next = new Set(collapsedDays.value)
  if (next.has(di)) { next.delete(di) } else { next.add(di) }
  collapsedDays.value = next
  emit('select-day', activeDay === di ? -1 : di)
}

/**
 * 将分钟数转换为 HH:MM 格式。
 * @param {number} m - 距午夜分钟数
 * @returns {string} 格式如 "8:30"
 */
function fmt(m: number | null | undefined) {
  if (m == null || m <= 0) return '-'
  const h = Math.floor(m / 60)
  const min = Math.floor(m % 60)
  return `${h}:${String(min).padStart(2, '0')}`
}

/**
 * 将到达/离开状态文本加上违规标记。
 * 准时/等待直接返回，违规行为加 ⚠️ 前缀。
 * @param {string} s - 状态文本
 * @returns {string}
 */
function statusClass(s: string | null | undefined) {
  if (!s) return '-'
  return s
}

function statusColor(s: string | null | undefined) {
  if (!s) return ''
  if (s.includes('迟到')) return 'status-late'
  if (s.includes('早到')) return 'status-early'
  return 'status-normal'
}
</script>

<style scoped>
.schedule-panel { background: #fff; border: 1px solid #e0e0e0; border-radius: 8px; padding: 16px; max-height: 600px; overflow-y: auto; }
.schedule-panel h3 { margin-bottom: 12px; font-size: 15px; }
.empty { color: #999; font-size: 13px; padding: 20px 0; text-align: center; }
.day-section { margin-bottom: 16px; }
.day-title { font-size: 14px; color: #1a73e8; margin-bottom: 8px; padding-bottom: 4px; border-bottom: 1px solid #e8f0fe; cursor: pointer; user-select: none; }
.day-title:hover { opacity: 0.7; }
.day-title.day-active { background: #e8f0fe; margin: -4px -8px 8px; padding: 4px 8px; border-radius: 4px; }
.day-hint { font-size: 11px; color: #999; font-weight: 400; margin-left: 6px; }
.schedule-table { width: 100%; border-collapse: collapse; font-size: 12px; }
.schedule-table th { text-align: left; padding: 4px 6px; border-bottom: 1px solid #e0e0e0; color: #888; font-weight: 600; }
.schedule-table td { padding: 4px 6px; border-bottom: 1px solid #f5f5f5; }
.depot-row td { color: #999; font-style: italic; }
.schedule-table tbody tr:not(.depot-row):hover { background: #f0f7ff; }
.schedule-table tbody tr:not(.depot-row).row-highlight { background: #e8f0fe; }
.status-normal { color: #27ae60; }
.status-early { color: #e67e22; }
.status-late { color: #e74c3c; font-weight: 600; }
.btn-remove {
  background: none; border: 1px solid #e0e0e0; border-radius: 4px;
  cursor: pointer; color: #d32f2f; font-size: 12px; width: 22px; height: 22px;
  display: inline-flex; align-items: center; justify-content: center;
  line-height: 1; padding: 0;
}
.btn-remove:hover { background: #ffebee; border-color: #d32f2f; }
</style>
