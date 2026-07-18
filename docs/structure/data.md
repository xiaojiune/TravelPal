# 统一数据字典

## 修改记录

| 日期 | 变更 |
|------|------|
| 2026-07-18 | 从引擎内部 5 种类型扩展为全链路数据字典（API → 引擎 → 前端） |

## 单位约定

| 量 | 单位 | 说明 |
|----|------|------|
| 距离 | km | 行驶距离 |
| 时间 | min | 旅行耗时、时间窗、停留时长 |
| 速度 | km/h | 旅行速度（默认 1.0——仅测试实验集使用，真实数据由高德驾车 API 提供，不依赖此值） |
| 经纬度 | GCJ-02 | 高德坐标系，x=经度，y=纬度 |
| 索引 | 0=depot | 0 索引始终为酒店，景点从 1 开始 |
| 时间窗 | (start, end) | 距午夜分钟数，0=00:00，1440=24:00 |

## 一、POI 与地图数据

### POIItem（API 请求）

前端传给后端的单个景点参数。定义见 [`backend/api/schemas.py:6`](../backend/api/schemas.py#L6)。

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `name` | `str` | — | 景点名称 |
| `lon` | `float` | — | GCJ-02 经度 |
| `lat` | `float` | — | GCJ-02 纬度 |
| `tw_start` | `float` | 480 | 营业开始（8:00） |
| `tw_end` | `float` | 1020 | 营业结束（17:00） |
| `stay` | `float` | 0 | 建议停留时长 |
| `expected_arrival` | `float\|None` | None | 用户期望到达时间 |

### POILookupResponse（API 响应）

POI 查询结果。定义见 [`backend/api/schemas.py:54`](../backend/api/schemas.py#L54)。

```
{
  items: POILookupItem[],    // 查询成功列表
  failed: string[]           // 未找到的名称
}

POILookupItem:
  name, lon, lat, address
  tw_start: int | None       // LLM 解析结果，None 表示解析失败
  tw_end: int | None
```

> `tw_start/tw_end` 为 `int | None`：若 LLM 无法从高德 `opentime2` 解析出营业时间，返回 None。前端暂未处理此情况。

### PoiCache / PoiCacheItem（引擎内存缓存）

后端内部映射，见 [`backend/typedefs.py:27`](../backend/typedefs.py#L27)。

```
PoiCache:
  hotel: PoiCacheItem
  spots: PoiCacheItem[]

PoiCacheItem:
  name, lon, lat
  tw: (float, float)       // 与 API 不同，这里为元组 (start, end)
  stay: float
```

### SpotDict（引擎求解器核心类型）

引擎内部景点类型，求解器和聚类算法直接使用。定义见 [`backend/typedefs.py:11`](../backend/typedefs.py#L11)。

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `name` | `str` | ✅ | 景点名称 |
| `x` | `float` | ✅ | GCJ-02 经度 |
| `y` | `float` | ✅ | GCJ-02 纬度 |
| `tw` | `(float, float)` | ✅ | 有效时间窗 `(start, end)`，经 `effective_start` / `effective_end` 收缩后的最终值 |
| `stay` | `float` | ✅ | 停留时长（分钟） |
| `original_tw` | `(float, float)` | ✅ | 原始营业时间窗，来自 POI 查询结果，用于对照 |
| `lon` | `float` | ❌ | 与 x 重复的兼容字段 |
| `lat` | `float` | ❌ | 与 y 重复的兼容字段 |
| `expected_arrival` | `float` | ❌ | 期望到达时间，影响 `effective_start` 计算 |

> `tw` 的收缩规则在 [`pipeline.py:97-117`](../backend/engine/pipeline.py#L97)：
> `effective_start = max(tw_start, expected_arrival, day_start)`
> `effective_end = tw_end - stay`

## 二、规划请求

### PlanRequest（统一请求体）

适用于 `/api/suggest` 和 `/api/plan` 两个端点。定义见 [`backend/api/schemas.py:67`](../backend/api/schemas.py#L67)。

```
{
  city: string              // 城市名
  hotel_name, hotel_lon, hotel_lat, hotel_tw_start: 0, hotel_tw_end: 1440
  spots: POIItem[]          // 至少 1 个
  n_days: int | null        // null → 建议模式，有值 → 规划模式
  mode: "fast" | "deep"     // fast=CA求解器，deep=VNS求解器
  day_start: float          // 启程时间，默认 0=午夜
  min_days: int | null      // 建议模式的最小天数，null 时引擎自动推断

  // 矩阵复用（来自 suggest 响应）：
  cost_matrix: number[][] | null
  dist_matrix: number[][] | null

  // 惩罚权重：
  penalty_weight: 100       // 迟到惩罚
  early_wait_weight: 0.1    // 早到等待
  late_return_weight: 50    // 晚归
}
```

### PlanAdjustRequest（规划调整）

重新规划请求，见 [`backend/api/schemas.py:130`](../backend/api/schemas.py#L130)。

```
{
  spots: dict               // 当前景点字典
  cost_matrix: number[][]
  dist_matrix: number[][]
  routes: list
  adjustments: {            // 调整指令
    balance?: true,         // 均衡天数
    change_days?: 3,        // 改天数
    remove_poi?: "故宫",     // 移除景点
    add_poi?: {...}         // 添加景点
  }
}
```

## 三、规划结果

### RouteResult（求解器原始输出）

`solve_groups` 的返回，定义见 [`backend/typedefs.py:44`](../backend/typedefs.py#L44)。

| 字段 | 类型 | 说明 |
|------|------|------|
| `routes` | `list[list[int]]` | 每组 `[0, 3, 1, 0]`（首尾 depot） |
| `histories` | `list[list[float]]` | 收敛历史（可选） |
| `total_cost` | `float` | 总成本 min，`= total_dist + wait + late + penalty` |
| `total_dist` | `float` | 总行驶距离 km |
| `wait` | `float` | 总等待时间 min |
| `late` | `float` | 总迟到时间 min |
| `valid` | `bool` | 是否覆盖全部景点 |

### ScheduleItem（每日行程单条）

重建行程的产物，定义见 [`backend/typedefs.py:63`](../backend/typedefs.py#L63) 和 [`frontend/src/types.ts`](../frontend/src/types.ts)。

```
{
  name: string              // 景点名称
  arrival: int              // 到达时间（距午夜分钟数）
  departure: int            // 离开时间（距午夜分钟数）
  tw: string                // 营业时间窗 "HH:MM - HH:MM"
  stay: string              // 停留时长 "X min"
  arrival_status: string    // "正常到达" / "早到 X 分钟" / "迟到 X 分钟"
  departure_status: string  // "正常离开" / "迟到 X 分钟离开"
}
```

> 后端 `stay` 为 `str`（含单位），前端 `types.ts` 中为 `number`（纯数值）。

### PlanResult（完整规划结果）

`run_planning` 的最终返回，定义见 [`backend/typedefs.py:74`](../backend/typedefs.py#L74) 和 [`frontend/src/types.ts`](../frontend/src/types.ts)。

```
{
  type: string              // "suggestion" 或 "solution"
  solution?: {
    routes, total_cost, total_dist, wait, late, valid
  }
  best_days: int            // 建议天数
  best_m: string            // 最优方法名称
  spots: {                  // 景点字典，key=索引
    "1": { name, x, y, tw, stay, original_tw, ... }
  }
  daily_schedules: [        // 每日行程
    [ScheduleItem, ...],    // Day 1（首尾为酒店出发/返回）
    [ScheduleItem, ...],    // Day 2
  ]
  commentary: string        // AI 评语（仅 solution 模式有）
  cost_matrix: number[][]   // N+1 × N+1 成本矩阵（分钟）
  dist_matrix: number[][]   // N+1 × N+1 距离矩阵（km）
  polylines: {              // 真实路径坐标
    "0_3": "116.39,39.91;116.40,39.92;..."
  }
  amap_api_key: string
  amap_security_code: string
  algo_time: float          // 算法耗时（秒）
}
```

> `suggestion` 模式会为每条建议调用 `_rebuild_schedule`，返回 `daily_schedules`。`type="solution"` 时额外包含 `commentary`。

### SuggestionItem（建议列表条目）

`POST /api/suggest` 响应中 `suggestions[]` 的元素类型，见 [`frontend/src/types.ts`](../frontend/src/types.ts)。

```
{
  n_days: int
  method: string
  cost: number, total_dist: number, wait: number, late: number
  routes: number[][]
  daily_schedules?: ScheduleItem[][]
}
```

## 四、历史记录

### HistoryCreate（创建请求）

保存方案到分享站，定义见 [`backend/api/schemas.py:147`](../backend/api/schemas.py#L147)。

```
{
  device_id: string | null  // 匿名设备标识，用于删除时鉴权
  note: string | null       // 用户备注
  city: string
  hotel: string | null
  n_days: int
  cost: float | null
  spot_count: int | null
  plan_result: dict         // 完整 PlanResult（JSONB 存储）
  request_params: dict|null // 原始请求参数（buildRequest 产物）
}
```

### HistorySummary（列表项）

分页列表的每条摘要，见 [`backend/api/schemas.py:165`](../backend/api/schemas.py#L165)。

```
{
  id: string, city: string, hotel: string|null, n_days: int
  cost: float|null, spot_count: int|null, note: string|null
  created_at: string        // ISO 8601
}
```

### HistoryDetail（完整详情）

单条历史完整数据，见 [`backend/api/schemas.py:177`](../backend/api/schemas.py#L177)。

```
{
  id, city, hotel, n_days, cost, spot_count, note, created_at
  plan_result: dict         // 全量 PlanResult
  request_params: dict|null
}
```

## 五、数据流映射

### 前后端类型对应

| 逻辑概念 | API（schemas.py） | 后端引擎（typedefs.py） | 前端（types.ts） |
|---------|-------------------|----------------------|----------------|
| 景点参数 | `POIItem` | `SpotDict` | `POIItem`（生成） |
| POI 查询 | `POILookupResponse` | `PoiCache` | `POILookupResponse`（生成） |
| 规划请求 | `PlanRequest` | — | `PlanRequestPayload` |
| 求解结果 | — | `RouteResult` | `PlanResultSolution` |
| 行程项 | — | `ScheduleItem` | `ScheduleItem` |
| 完整结果 | — | `PlanResult` | `PlanResult` |
| 建议项 | — | — | `SuggestionItem` |
| 历史摘要 | `HistorySummary` | ORM 行 | `HistorySummary` |
| 历史详情 | `HistoryDetail` | ORM 行 | `HistoryDetail` |

### 索引约定

- 所有数组和字典的 **0 索引固定为酒店（depot）**
- `routes` 序列：`[0, 3, 1, 0]` 意为酒店 → 景点3 → 景点1 → 酒店
- 前端构建 PlanResult 时，`best_days` 与 `daily_schedules.length` 一致
- `polylines` 的 key 格式为 `"{fromIdx}_{toIdx}"`，如 `"0_3"`：depot 到景点3

### 边界与约束

| 约束 | 值 | 来源 |
|------|-----|------|
| 景点数下限 | 1 | `PlanRequest.spots` |
| 天数范围 | [min_days, n_spots] | `ca_suggest` 循环 |
| 天数下界（默认） | `max(1, n_spots // 8 + 1)` | `search.py:174` |
| 聚类方法数 | 6 | `clustering.py` |
| 成本矩阵形状 | (N+1, N+1) | N=景点数 |
| VNS 精英池容量 | 3 | `vns.py` |
