<template>
  <div class="page-history">
    <h2>方案分享站</h2>
    <p class="subtitle">其他访客分享的行程方案，点击可直接查看完整规划。</p>

    <div v-if="loading" class="loading">
      <n-spin size="small" />
      <span>加载中...</span>
    </div>

    <div v-else-if="items.length === 0" class="empty">
      <n-empty description="暂无分享的方案">
        <template #extra>
          <router-link to="/"><n-button type="primary">去规划</n-button></router-link>
        </template>
      </n-empty>
    </div>

    <template v-else>
      <div class="history-list">
        <div v-for="r in items" :key="r.id" class="history-card" @click="viewRecord(r)">
          <n-button text :focusable="false" class="btn-delete" @click.stop="deleteRecord(r)"
            >×</n-button
          >
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
        </div>
      </div>

      <div class="pagination">
        <n-pagination :page="page" :page-count="totalPages" @update:page="goPage" />
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
/** 历史记录页：方案分享站，支持分页列表、查看详情、删除（device_id 鉴权）。 */
import { ref, computed, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useMessage, useDialog } from 'naive-ui'
import { usePlanStore } from '@/stores/plan'
import { getHistoryList, getHistoryDetail, deleteHistory, getDeviceId } from '@/services/api'
import type { HistorySummary } from '@/services/api'

const router = useRouter()
const route = useRoute()
const store = usePlanStore()
const message = useMessage()
const dialog = useDialog()

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
    message.error('加载方案详情失败，请稍后重试。')
  }
}

function deleteRecord(r: HistorySummary) {
  dialog.warning({
    title: '删除分享',
    content: `确定删除 ${r.city} ${r.n_days} 日游的分享？`,
    positiveText: '删除',
    negativeText: '取消',
    onPositiveClick: async () => {
      try {
        await deleteHistory(r.id, getDeviceId())
        items.value = items.value.filter((x) => x.id !== r.id)
        total.value--
      } catch {
        message.error('删除失败，可能不是你分享的方案。')
      }
    },
  })
}

watch(
  () => route.path,
  (path) => {
    if (path === '/history') loadList()
  },
  { immediate: true },
)
</script>

<style scoped>
.page-history {
  max-width: 800px;
  margin: 0;
}
.subtitle {
  font-size: 13px;
  color: var(--tp-text-3);
  margin-top: -8px;
  margin-bottom: 20px;
}
.loading {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 60px 0;
  color: var(--tp-text-3);
}
.empty {
  display: flex;
  justify-content: center;
  padding: 60px 0;
}
.history-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.history-card {
  position: relative;
  background: var(--tp-bg-card);
  border: 1px solid var(--tp-card-border);
  border-radius: 8px;
  padding: 14px 18px;
  cursor: pointer;
  box-shadow: var(--tp-card-shadow);
  transition: box-shadow 0.15s, transform 0.15s;
}
.history-card:hover {
  box-shadow: var(--tp-card-shadow-hover);
  transform: translateY(-1px);
}
.h-main {
  display: flex;
  gap: 16px;
  align-items: center;
}
.h-city {
  font-size: 16px;
  font-weight: 700;
  color: var(--tp-primary);
}
.h-days {
  background: var(--tp-primary-soft);
  color: var(--tp-primary);
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
}
.h-cost {
  font-size: 14px;
  color: var(--tp-text);
}
.h-spots {
  font-size: 12px;
  color: var(--tp-text-3);
}
.h-meta {
  margin-top: 4px;
  font-size: 11px;
  color: var(--tp-text-3);
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}
.h-note {
  font-style: italic;
  color: var(--tp-text-3);
}
.btn-delete {
  position: absolute;
  top: 4px;
  right: 8px;
  color: var(--tp-text-3);
}
.btn-delete:hover {
  color: var(--tp-error);
}
.pagination {
  display: flex;
  justify-content: center;
  margin-top: 20px;
}
</style>
