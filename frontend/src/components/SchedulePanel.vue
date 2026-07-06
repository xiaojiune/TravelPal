<template>
  <div class="schedule-panel">
    <h3>每日行程</h3>
    <div v-if="!dailySchedules?.length" class="empty">暂无行程数据</div>
    <div v-else v-for="(day, di) in dailySchedules" :key="di" class="day-section">
      <h4 class="day-title">第 {{ di + 1 }} 天</h4>
      <table class="schedule-table">
        <thead>
          <tr>
            <th>景点</th>
            <th>到达</th>
            <th>离开</th>
            <th>营业时间</th>
            <th>停留</th>
            <th>到达状态</th>
            <th>离开状态</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(item, ii) in day" :key="ii" :class="{ 'depot-row': item.name === '酒店（返回）' }">
            <td>{{ item.name }}</td>
            <td>{{ fmt(item.arrival) }}</td>
            <td>{{ fmt(item.departure) }}</td>
            <td>{{ item.tw || '-' }}</td>
            <td>{{ item.stay ?? '-' }}</td>
            <td>{{ statusClass(item.arrival_status) }}</td>
            <td>{{ statusClass(item.departure_status) }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup>
/**
 * 每日行程面板组件。
 * 接收 dailySchedules 数据，以表格形式展示每日景点到达/离开/状态。
 *
 * @param {Array} dailySchedules - 每日行程数组，每项含
 *   name/arrival/departure/tw/stay/arrival_status/departure_status
 */
defineProps({ dailySchedules: { type: Array, default: () => [] } })

/**
 * 将分钟数转换为 HH:MM 格式。
 * @param {number} m - 距午夜分钟数
 * @returns {string} 格式如 "8:30"
 */
function fmt(m) {
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
function statusClass(s) {
  if (!s) return '-'
  return s.includes('准时') || s.includes('等待') ? s : `⚠️ ${s}`
}
</script>

<style scoped>
.schedule-panel { background: #fff; border: 1px solid #e0e0e0; border-radius: 8px; padding: 16px; max-height: 600px; overflow-y: auto; }
.schedule-panel h3 { margin-bottom: 12px; font-size: 15px; }
.empty { color: #999; font-size: 13px; padding: 20px 0; text-align: center; }
.day-section { margin-bottom: 16px; }
.day-title { font-size: 14px; color: #1a73e8; margin-bottom: 8px; padding-bottom: 4px; border-bottom: 1px solid #e8f0fe; }
.schedule-table { width: 100%; border-collapse: collapse; font-size: 12px; }
.schedule-table th { text-align: left; padding: 4px 6px; border-bottom: 1px solid #e0e0e0; color: #888; font-weight: 600; }
.schedule-table td { padding: 4px 6px; border-bottom: 1px solid #f5f5f5; }
.depot-row td { color: #999; font-style: italic; }
</style>
