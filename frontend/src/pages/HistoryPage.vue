<template>
  <div class="page-history">
    <h2>历史记录</h2>
    <div v-if="records.length === 0" class="empty">
      <p>暂无历史规划记录。</p>
      <router-link to="/" class="btn btn-primary">去规划</router-link>
    </div>
    <div v-else class="history-list">
      <div v-for="r in records" :key="r.id" class="history-card" @click="viewRecord(r)">
        <div class="h-main">
          <span class="h-city">{{ r.city }}</span>
          <span class="h-days">{{ r.n_days }} 天</span>
          <span class="h-cost">成本 {{ r.cost?.toFixed(1) }}</span>
          <span class="h-spots">{{ r.spots }} 个景点</span>
        </div>
        <div class="h-meta">
          <span>{{ r.hotel }}</span>
          <span>{{ r.time }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
/** 历史记录页：从 localStorage 读取摘要列表，点击后跳转首页重新搜索。 */
import { ref } from 'vue'

/** 从 localStorage 读取历史规划记录列表。完整规划结果不在此处存储（避免大对象溢出）。 */
function loadRecords() {
  const raw = localStorage.getItem('travelpal_history')
  return raw ? JSON.parse(raw) : []
}
const records = ref(loadRecords())

/** 查看某条历史记录：清空当前状态后跳转首页，提示用户重新搜索。 */
function viewRecord(r: { city: string; n_days: number; cost: number; hotel: string; spots: number; time: string }) {
  if (confirm(`查看 ${r.city} ${r.n_days} 日游的方案？\n建议先返回首页重新搜索。`)) {
    localStorage.removeItem('travelpal_history_record')
    window.location.href = '/'
  }
}
</script>

<style scoped>
.page-history { max-width: 800px; margin: 0 auto; }
.empty { text-align: center; padding: 60px 0; color: #999; }
.empty .btn { display: inline-block; margin-top: 16px; text-decoration: none; }
.history-list { display: flex; flex-direction: column; gap: 8px; }
.history-card {
  background: #fff; border: 1px solid #e0e0e0; border-radius: 8px;
  padding: 14px 18px; cursor: pointer; transition: box-shadow .15s;
}
.history-card:hover { box-shadow: 0 2px 8px rgba(0,0,0,.08); }
.h-main { display: flex; gap: 16px; align-items: center; }
.h-city { font-size: 16px; font-weight: 700; color: #1a73e8; }
.h-days { background: #e8f0fe; color: #1a73e8; padding: 2px 8px; border-radius: 4px; font-size: 12px; }
.h-cost { font-size: 14px; color: #333; }
.h-spots { font-size: 12px; color: #888; }
.h-meta { margin-top: 4px; font-size: 11px; color: #aaa; display: flex; gap: 12px; }
.btn { padding: 10px 28px; border: none; border-radius: 6px; cursor: pointer; font-size: 14px; font-weight: 600; text-decoration: none; display: inline-block; }
.btn-primary { background: #1a73e8; color: #fff; }
</style>
