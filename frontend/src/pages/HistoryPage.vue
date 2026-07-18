<template>
  <div class="page-history">
    <h2>方案分享站</h2>
    <p class="subtitle">其他访客分享的行程方案，点击可直接查看完整规划。</p>

    <div v-if="loading" class="loading">加载中...</div>

    <div v-else-if="items.length === 0" class="empty">
      <p>暂无分享的方案。</p>
      <router-link to="/" class="btn btn-primary">去规划</router-link>
    </div>

    <template v-else>
      <div class="history-list">
        <div v-for="r in items" :key="r.id" class="history-card" @click="viewRecord(r)">
          <div class="h-main">
            <span class="h-city">{{ r.city }}</span>
            <span class="h-days">{{ r.n_days }} 天</span>
            <span v-if="r.cost != null" class="h-cost">成本 {{ r.cost.toFixed(1) }}</span>
            <span v-if="r.spot_count != null" class="h-spots">{{ r.spot_count }} 个景点</span>
          </div>
          <div class="h-meta">
            <span v-if="r.hotel">{{ r.hotel }}</span>
            <span v-if="r.note" class="h-note">{{ r.note }}</span>
            <span>{{ formatTime(r.created_at) }}</span>
          </div>
          <button class="btn-delete" @click.stop="deleteRecord(r)">×</button>
        </div>
      </div>

      <div v-if="totalPages > 1" class="pagination">
        <button :disabled="page <= 1" @click="goPage(page - 1)">‹ 上一页</button>
        <span>{{ page }} / {{ totalPages }}</span>
        <button :disabled="page >= totalPages" @click="goPage(page + 1)">下一页 ›</button>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { usePlanStore } from '@/stores/plan'
import { getHistoryList, getHistoryDetail, deleteHistory, getDeviceId } from '@/services/api'
import type { HistorySummary } from '@/services/api'

const router = useRouter()
const route = useRoute()
const store = usePlanStore()

const items = ref<HistorySummary[]>([])
const loading = ref(true)
const page = ref(1)
const total = ref(0)
const pageSize = 20

const totalPages = computed(() => Math.ceil(total.value / pageSize) || 1)

function formatTime(iso: string) {
  if (!iso) return ''
  const d = new Date(iso)
  return d.toLocaleString()
}

async function loadList() {
  loading.value = true
  try {
    const res = await getHistoryList(page.value, pageSize)
    items.value = res.items
    total.value = res.total
  } catch {
    items.value = []
  } finally {
    loading.value = false
  }
}

function goPage(p: number) {
  page.value = p
  loadList()
}

async function viewRecord(r: HistorySummary) {
  try {
    const detail = await getHistoryDetail(r.id)
    store.planResult = detail.plan_result as any
    store.historyRecordId = r.id
    store.historyRequestParams = detail.request_params as Record<string, unknown> | null
    router.push('/plan')
  } catch {
    alert('加载方案详情失败，请稍后重试。')
  }
}

async function deleteRecord(r: HistorySummary) {
  if (!confirm(`确定删除 ${r.city} ${r.n_days} 日游的分享？`)) return
  try {
    await deleteHistory(r.id, getDeviceId())
    items.value = items.value.filter(x => x.id !== r.id)
    total.value--
  } catch {
    alert('删除失败，可能不是你分享的方案。')
  }
}

watch(() => route.path, (path) => {
  if (path === '/history') loadList()
}, { immediate: true })
</script>

<style scoped>
.page-history { max-width: 800px; margin: 0 auto; }
.subtitle { font-size: 13px; color: #888; margin-top: -8px; margin-bottom: 20px; }
.loading { text-align: center; padding: 60px 0; color: #999; }
.empty { text-align: center; padding: 60px 0; color: #999; }
.empty .btn { display: inline-block; margin-top: 16px; text-decoration: none; }
.history-list { display: flex; flex-direction: column; gap: 8px; }
.history-card {
  position: relative;
  background: #fff; border: 1px solid #e0e0e0; border-radius: 8px;
  padding: 14px 18px; cursor: pointer; transition: box-shadow .15s;
}
.history-card:hover { box-shadow: 0 2px 8px rgba(0,0,0,.08); }
.h-main { display: flex; gap: 16px; align-items: center; }
.h-city { font-size: 16px; font-weight: 700; color: #1a73e8; }
.h-days { background: #e8f0fe; color: #1a73e8; padding: 2px 8px; border-radius: 4px; font-size: 12px; }
.h-cost { font-size: 14px; color: #333; }
.h-spots { font-size: 12px; color: #888; }
.h-meta { margin-top: 4px; font-size: 11px; color: #aaa; display: flex; gap: 12px; flex-wrap: wrap; }
.h-note { font-style: italic; color: #888; }
.btn-delete {
  position: absolute; top: 8px; right: 10px;
  background: none; border: none; font-size: 18px; color: #ccc; cursor: pointer;
  line-height: 1; padding: 0 4px;
}
.btn-delete:hover { color: #e74c3c; }
.pagination {
  display: flex; justify-content: center; align-items: center; gap: 16px;
  margin-top: 20px; font-size: 13px; color: #666;
}
.pagination button {
  padding: 6px 14px; border: 1px solid #d0d0d0; border-radius: 4px;
  background: #fff; cursor: pointer; font-size: 13px;
}
.pagination button:disabled { opacity: 0.4; cursor: default; }
.btn { padding: 10px 28px; border: none; border-radius: 6px; cursor: pointer; font-size: 14px; font-weight: 600; text-decoration: none; display: inline-block; }
.btn-primary { background: #1a73e8; color: #fff; }
</style>
