/** 核心全局状态：管理输入参数、方案建议、规划结果、Agent 对话、异步任务集合。Pinia setup 语法。 */
import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { getTask } from '@/services/api'
import { useSuggestCache } from '@/composables/useSuggestCache'
import type {
  SpotFormItem,
  PlanRequestPayload,
  SuggestionItem,
  PlanResult,
  PoiItem,
  ChatMessage as ChatMessageType,
} from '@/types'

/** 单次工具查询结果（供左侧查询面板分节展示）。 */
export interface QueryResult {
  tool: string
  result: unknown
  city?: string
  time?: string
}

/** 异步任务集合条目（工具栏面板展示 + 生命周期单点维护）。 */
export interface TaskItem {
  task_id: string
  task_type: string
  status: string
  created_at: string
}

/** 登录用户任务集合的 localStorage 键（游客不持久化）。 */
const TASKS_LOCAL_KEY = 'travelpal_task_items'

/** 判定工具是否为 POI 查询（其结果数组可加入待选栏）。 */
export function isPoiQuery(tool: string): boolean {
  return tool === 'poi_lookup'
}

/** 左侧面板其它查询结果（非 POI 型）最多保留条数，超出自动裁剪最旧。 */
const MAX_OTHER_RESULTS = 5

/** 时间 → HH:MM（工具查询结果时间戳展示用）。 */
function formatClock(d: Date): string {
  const hh = String(d.getHours()).padStart(2, '0')
  const mm = String(d.getMinutes()).padStart(2, '0')
  return `${hh}:${mm}`
}

export const usePlanStore = defineStore('plan', () => {
  // ====== 输入状态 ======
  const city = ref('')
  const hotelName = ref('')
  const hotelLon = ref(0)
  const hotelLat = ref(0)
  const hotelAddress = ref('')
  const hotelTwStart = ref(0)
  const hotelTwEnd = ref(1440)
  const dayStart = ref(0)
  const spots = ref<SpotFormItem[]>([])
  const penaltyWeight = ref(100)
  const earlyWaitWeight = ref(0.1)
  const lateReturnWeight = ref(50)
  const minDays = ref<number | null>(null)

  /** 从 Agent 页面添加一个酒店到输入表单。 */
  function addHotel(poi: SpotFormItem) {
    hotelName.value = poi.name
    hotelLon.value = poi.lon
    hotelLat.value = poi.lat
    hotelAddress.value = poi.address ?? ''
    hotelTwStart.value = poi.twStart ?? 0
    hotelTwEnd.value = poi.twEnd ?? 1440
  }

  /** 从 Agent 页面添加一个景点到输入列表（重复名称去重）。 */
  function addSpot(poi: SpotFormItem) {
    if (spots.value.some((s) => s.name === poi.name)) return
    spots.value.push({
      name: poi.name,
      lon: poi.lon,
      lat: poi.lat,
      twStart: poi.twStart ?? 480,
      twEnd: poi.twEnd ?? 1020,
      stay: poi.stay ?? 0,
      address: poi.address,
    })
  }

  // ====== Agent 待选栏状态（全局共享，面板与左侧静态栏共用） ======
  /** 工具查询结果暂存列表（含工具名/结果/城市，供左侧查询面板分节展示）。 */
  const queryResults = ref<QueryResult[]>([])

  /** 对话中暂存的 POI 待选列表（由 poi 型查询结果派生，供加入首页表单）。 */
  const pendingPois = computed(() =>
    queryResults.value.filter((q) => isPoiQuery(q.tool)).flatMap((q) => q.result as PoiItem[]),
  )

  /** 接收 Agent 工具查询结果：入队 queryResults；并尝试自动填充城市（仅一次）。 */
  function addQueryResult(tool: string, result: unknown, cityFromTool?: string) {
    queryResults.value.push({ tool, result, city: cityFromTool, time: formatClock(new Date()) })
    // 城市基于工具参数自动填充一次（store.city 空才填）
    if (cityFromTool && !city.value) {
      city.value = cityFromTool
    }
    // 数据层裁剪：非 POI 型结果只保留最新 N 条（单次 push 最多超 1 条），POI 待选不受影响
    const others = queryResults.value.filter((q) => !isPoiQuery(q.tool))
    if (others.length > MAX_OTHER_RESULTS) {
      const oldest = others[0]
      queryResults.value = queryResults.value.filter((q) => isPoiQuery(q.tool) || q !== oldest)
    }
  }

  /** 从待选栏移除指定 POI（元素级删除：只从所属数组剔除该 name，其余项保留）。 */
  function removePendingPoi(poi: PoiItem) {
    for (const q of queryResults.value) {
      if (!isPoiQuery(q.tool)) continue
      const arr = q.result as PoiItem[]
      if (!Array.isArray(arr)) continue
      const kept = arr.filter((p) => p.name !== poi.name)
      if (kept.length === arr.length) continue // 本条不含目标，跳过
      if (kept.length === 0) {
        // 数组删空 → 移除整条
        queryResults.value = queryResults.value.filter((x) => x !== q)
      } else {
        q.result = kept
      }
      return
    }
  }

  /** 从 queryResults 按索引移除一条（左侧其它结果卡删除按钮用）。 */
  function removeQueryResult(index: number) {
    queryResults.value.splice(index, 1)
  }

  // ====== Agent 对话状态（上提 store，面板 v-if 卸载后会话仍保留） ======
  /** 对话消息列表（user/assistant/tool 富卡片形态）。 */
  const chatMessages = ref<ChatMessageType[]>([])

  /** 是否处于 SSE 流式响应中（驱动输入禁用/发送按钮 loading）。 */
  const chatLoading = ref(false)

  /** 当前会话 id（后端懒建，SSE conversation 事件回填；用于跨轮次续接历史）。 */
  const chatConversationId = ref<string | null>(null)

  /** 将待选 POI 添加到首页输入列表，然后从待选栏移除。 */
  function addPoiToForm(poi: PoiItem) {
    if (!poi.name || poi.lon == null || poi.lat == null) return
    // TODO：此处与 usePoiSearch.searchSpots 共用 PoiItem(tw_start/tw_end)→SpotFormItem(twStart/twEnd)
    // 映射，第 3 次出现时抽取公共 toSpotForm() 纯函数（Rule of Three）。
    const base: SpotFormItem = {
      name: poi.name,
      lon: poi.lon,
      lat: poi.lat,
      twStart: poi.tw_start ?? 480,
      twEnd: poi.tw_end ?? 1020,
      stay: 0,
      address: poi.address,
    }
    if (poi.poi_type === 'hotel') {
      addHotel(base)
    } else {
      addSpot(base)
    }
    removePendingPoi(poi)
  }

  /** 一键将全部待选 POI 加入首页表单（addPoiToForm 会逐个 splice，需遍历副本）。 */
  function addAllPendingPois() {
    const all = pendingPois.value.slice()
    for (const poi of all) addPoiToForm(poi)
  }

  // ====== 历史记录与 Agent 状态 ======
  /** 从历史记录加载的记录 ID，非空时 PlanPage 应禁用「分享此方案」。 */
  const historyRecordId = ref<string | null>(null)
  /** 从历史记录加载的原始请求参数，用于 PlanPage 展示。 */
  const historyRequestParams = ref<Record<string, unknown> | null>(null)

  // ====== 方案状态 ======
  const suggestions = ref<SuggestionItem[]>([])
  const selectedNDays = ref<number | null>(null)
  const selectedMethod = ref('')

  // ====== 结果状态 ======
  const planResult = ref<PlanResult | null>(null)
  /** 深度模式生成的规划结果卡片列表（首页传来新参数时不清除）。 */
  const deepResults = ref<PlanResult[]>([])
  const amapApiKey = ref('')
  const loading = ref(false)
  /** 高德 JS API 安全密钥 */
  const amapSecurityCode = ref('')

  // ====== 方法 ======

  /** 构建 POST /api/or-vns 或 /api/or-ca 请求体。nDays=null 时引擎端自动推断。 */
  function buildRequest(
    nDays: number | null,
    extra?: { cost_matrix?: number[][]; dist_matrix?: number[][] },
  ): PlanRequestPayload {
    return {
      city: city.value,
      hotel_name: hotelName.value,
      hotel_lon: hotelLon.value,
      hotel_lat: hotelLat.value,
      hotel_tw_start: hotelTwStart.value,
      hotel_tw_end: hotelTwEnd.value,
      day_start: dayStart.value,
      min_days: minDays.value ?? null,
      spots: spots.value.map((s) => ({
        name: s.name,
        lon: Number(s.lon),
        lat: Number(s.lat),
        tw_start: Number(s.twStart),
        tw_end: Number(s.twEnd),
        stay: Number(s.stay),
        expected_arrival: Number(s.expectedArrival ?? s.twStart),
      })),
      n_days: nDays,
      mode: 'fast',
      penalty_weight: penaltyWeight.value,
      early_wait_weight: earlyWaitWeight.value,
      late_return_weight: lateReturnWeight.value,
      ...(extra?.cost_matrix
        ? { cost_matrix: extra.cost_matrix, dist_matrix: extra.dist_matrix }
        : {}),
    }
  }

  // ====== 异步任务集合（生命周期单点：工具栏展示 + 后台轮询） ======
  const taskItems = ref<TaskItem[]>([])
  /** 是否将任务集合持久化到 localStorage；仅登录用户 true（游客只存内存，刷新即清）。 */
  const persistTasks = ref(false)
  let tasksTimer: number | null = null

  function readLocalTasks(): TaskItem[] {
    try {
      return JSON.parse(localStorage.getItem(TASKS_LOCAL_KEY) ?? '[]') as TaskItem[]
    } catch {
      return []
    }
  }
  function writeLocalTasks(items: TaskItem[]) {
    localStorage.setItem(TASKS_LOCAL_KEY, JSON.stringify(items))
  }
  /** 是否为终态（不再轮询、不显示取消按钮）。 */
  function isTaskTerminal(status: string): boolean {
    return status === 'done' || status === 'failed' || status === 'canceled'
  }

  /** 登记一个已提交任务（提交页在 submitTask 成功后调用）。 */
  function registerTask(task: { task_id: string; task_type: string }) {
    if (taskItems.value.some((t) => t.task_id === task.task_id)) return
    const item: TaskItem = {
      task_id: task.task_id,
      task_type: task.task_type,
      status: 'pending',
      created_at: new Date().toISOString(),
    }
    taskItems.value = [item, ...taskItems.value]
    if (persistTasks.value) writeLocalTasks(taskItems.value)
    ensurePolling()
  }

  /** 后台轮询一次：更新非终态任务状态，无活动任务即停。 */
  async function pollOnce() {
    const items = taskItems.value
    if (items.length === 0) return
    let hasActive = false
    for (const t of items) {
      if (isTaskTerminal(t.status)) continue
      try {
        const detail = await getTask(t.task_id)
        const idx = taskItems.value.findIndex((x) => x.task_id === t.task_id)
        if (idx >= 0) {
          taskItems.value[idx] = { ...taskItems.value[idx], status: detail.status }
        }
        if (!isTaskTerminal(detail.status)) hasActive = true
      } catch {
        // 网络抖动：跳过本次，下轮再试（终态兜底由后端 status 决定）
      }
    }
    if (persistTasks.value) writeLocalTasks(taskItems.value)
    if (!hasActive) stopPolling()
  }

  function ensurePolling() {
    if (tasksTimer !== null) return
    tasksTimer = window.setInterval(() => void pollOnce(), 5000)
  }
  function stopPolling() {
    if (tasksTimer !== null) {
      clearInterval(tasksTimer)
      tasksTimer = null
    }
  }

  /** 外部（App.vue）设置是否持久化；置 false 时同步清空（切游客/登出）。 */
  function setPersistTasks(persist: boolean) {
    persistTasks.value = persist
    if (!persist) clearTasks()
  }

  /** 刷新/登录后从 localStorage 唤回任务集合；有活动任务则启动后台轮询。 */
  function hydrateTasks() {
    taskItems.value = readLocalTasks()
    ensurePolling()
  }

  /** 登出/切换账号：清空任务集合（内存 + localStorage）并停后台轮询。 */
  function clearTasks() {
    stopPolling()
    taskItems.value = []
    localStorage.removeItem(TASKS_LOCAL_KEY)
  }

  /** 更新单个任务状态（取消等即时反馈；pollOnce 也会轮询更新）。 */
  function setTaskStatus(task_id: string, status: string) {
    const idx = taskItems.value.findIndex((t) => t.task_id === task_id)
    if (idx >= 0) taskItems.value[idx] = { ...taskItems.value[idx], status }
    if (persistTasks.value) writeLocalTasks(taskItems.value)
  }

  /** 重置全部状态至初始值。用于开始新规划或清空当前会话。 */
  function reset() {
    useSuggestCache().clear()
    city.value = ''
    hotelName.value = ''
    hotelLon.value = 0
    hotelLat.value = 0
    hotelAddress.value = ''
    hotelTwStart.value = 0
    hotelTwEnd.value = 1440
    dayStart.value = 0
    spots.value = []
    minDays.value = null
    historyRecordId.value = null
    historyRequestParams.value = null
    suggestions.value = []
    selectedNDays.value = null
    selectedMethod.value = ''
    planResult.value = null
    deepResults.value = []
    amapApiKey.value = ''
    amapSecurityCode.value = ''
    queryResults.value = []
    chatMessages.value = []
    chatLoading.value = false
    chatConversationId.value = null
    loading.value = false
    penaltyWeight.value = 100
    earlyWaitWeight.value = 0.1
    lateReturnWeight.value = 50
  }

  return {
    city,
    hotelName,
    hotelLon,
    hotelLat,
    hotelAddress,
    hotelTwStart,
    hotelTwEnd,
    dayStart,
    spots,
    penaltyWeight,
    earlyWaitWeight,
    lateReturnWeight,
    minDays,
    historyRecordId,
    historyRequestParams,
    suggestions,
    selectedNDays,
    selectedMethod,
    planResult,
    deepResults,
    amapApiKey,
    amapSecurityCode,
    loading,
    pendingPois,
    queryResults,
    chatMessages,
    chatLoading,
    chatConversationId,
    addQueryResult,
    removePendingPoi,
    removeQueryResult,
    addPoiToForm,
    addAllPendingPois,
    buildRequest,
    reset,
    addHotel,
    addSpot,
    taskItems,
    registerTask,
    hydrateTasks,
    clearTasks,
    setPersistTasks,
    setTaskStatus,
  }
})
