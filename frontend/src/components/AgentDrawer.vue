<template>
  <n-drawer v-model:show="show" placement="left" :width="820">
    <n-drawer-content body-content-style="padding: 0">
      <div class="agent-drawer">
        <aside class="pending-panel">
          <h3 class="panel-title">📋 待选</h3>
          <div v-if="pendingPois.length === 0" class="pending-empty">
            对话中查询的 POI 将出现在这里
          </div>
          <n-button
            v-if="pendingPois.length > 0"
            size="small"
            type="primary"
            block
            class="pending-add-all"
            @click="addAllPois"
          >
            ➕ 全部加入行程
          </n-button>
          <div v-for="(poi, i) in pendingPois" :key="i" class="pending-card">
            <div class="pending-header">
              {{ poi.name }}
              <n-tag :type="poi.poi_type === 'hotel' ? 'success' : 'primary'" size="small">
                {{ poi.poi_type === 'hotel' ? '🏨 酒店' : '🏛️ 景点' }}
              </n-tag>
            </div>
            <div class="pending-detail">📍 {{ poi.address }}</div>
            <div class="pending-detail">
              {{ poi.lon?.toFixed(4) }}, {{ poi.lat?.toFixed(4) }}
              <template v-if="poi.tw_start != null && poi.tw_end != null">
                · {{ Math.floor(poi.tw_start! / 60) }}:{{ String(poi.tw_start! % 60).padStart(2, '0') }}~{{ Math.floor(poi.tw_end! / 60) }}:{{ String(poi.tw_end! % 60).padStart(2, '0') }}
              </template>
            </div>
            <div class="pending-actions">
              <n-button size="tiny" type="primary" @click="addPoiToForm(poi)">
                {{ poi.poi_type === 'hotel' ? '🏨 设为酒店' : '➕ 添加' }}
              </n-button>
              <n-button size="tiny" quaternary @click="removePoi(i)">
                ✕ 取消
              </n-button>
            </div>
          </div>
        </aside>
        <ChatStream class="chat-stream-area" @tool-result="onToolResult" />
      </div>
    </n-drawer-content>
  </n-drawer>
</template>

<script setup lang="ts">
/**
 * 全局 Agent 抽屉：对话流（ChatStream）+ 左侧待选栏（POI 查询结果暂存）。
 *
 * 挂在 App.vue 全局（router-view 外），由右下角浮动按钮唤起。
 * 待选栏监听 ChatStream 的 tool-result 事件，去重后暂存，供添加到首页表单。
 */
import { ref } from 'vue'
import ChatStream from '@/components/ChatStream.vue'
import { usePlanStore } from '@/stores/plan'

interface PoiItem {
  name?: string; lon?: number; lat?: number; address?: string
  tw_start?: number; tw_end?: number; poi_type?: string
}

defineOptions({ name: 'AgentDrawer' })

const show = defineModel<boolean>({ default: false })

const store = usePlanStore()
/** 待选栏：对话中查询到的 POI 暂存列表。 */
const pendingPois = ref<PoiItem[]>([])

/** 接收 ChatStream 抛出的工具查询结果，去重后加入待选栏。 */
function onToolResult(poi: PoiItem) {
  if (!poi.name) return
  if (!pendingPois.value.some(p => p.name === poi.name)) {
    pendingPois.value.push(poi)
  }
}

/** 将待选 POI 添加到首页输入列表，然后从待选栏移除。 */
function addPoiToForm(poi: PoiItem) {
  if (!poi.name || poi.lon == null || poi.lat == null) return
  store.addSpot({
    name: poi.name,
    lon: poi.lon,
    lat: poi.lat,
    twStart: poi.tw_start ?? 480,
    twEnd: poi.tw_end ?? 1020,
    stay: 0,
    address: poi.address,
    poi_type: poi.poi_type,
  })
  const idx = pendingPois.value.findIndex(p => p.name === poi.name)
  if (idx !== -1) pendingPois.value.splice(idx, 1)
}

/** 从待选栏移除（不做其他操作）。 */
function removePoi(index: number) {
  pendingPois.value.splice(index, 1)
}

/** 一键将全部待选 POI 加入首页表单（addPoiToForm 会逐个 splice，需遍历副本）。 */
function addAllPois() {
  const all = pendingPois.value.slice()
  for (const poi of all) addPoiToForm(poi)
}
</script>

<style scoped>
.agent-drawer {
  display: flex;
  height: 100%;
}
.pending-panel {
  width: 260px;
  min-width: 260px;
  border-right: 1px solid var(--tp-border);
  padding: 16px;
  overflow-y: auto;
  background: var(--tp-bg);
}
.panel-title {
  font-size: 14px;
  margin: 0 0 12px 0;
  color: var(--tp-text);
}
.pending-empty {
  font-size: 13px;
  color: var(--tp-text-3);
  text-align: center;
  margin-top: 40px;
}
.pending-add-all {
  margin-bottom: 10px;
}
.pending-card {
  padding: 10px;
  margin-bottom: 8px;
  border: 1px solid var(--tp-border);
  border-radius: 8px;
  background: var(--tp-surface);
}
.pending-header {
  font-weight: 600;
  font-size: 13px;
  margin-bottom: 4px;
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}
.pending-detail {
  font-size: 12px;
  color: var(--tp-text-2);
  margin-bottom: 2px;
}
.pending-actions {
  display: flex;
  gap: 6px;
  margin-top: 6px;
}
.chat-stream-area {
  flex: 1;
  height: 100%;
}
</style>
