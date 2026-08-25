# 统一数据字典

## 修改记录

| 日期 | 变更 | 动机 |
|------|------|------|
| 2026-08-25 | 重写：对齐 typedefs.py / schemas.py 实际定义，去掉失效行号锚点，补充异步任务/PlanTask 字段 | 旧文档引用行号已漂移，且缺异步任务数据模型 |
| 2026-07-18 | 从引擎内部 5 种类型扩展为全链路数据字典（API → 引擎 → 前端） | 建立统一数据字典 |

## 读者指南

| 列 | 内容 |
|----|------|
| 面向读者 | 后端与前端开发者 |
| 阅读前置 | [backend.md](backend.md)、[frontend.md](frontend.md) |
| 阅读目标 | 掌握全链路数据模型与索引约定，避免前后端字段错位 |

## 单位约定

| 量 | 单位 | 说明 |
|----|------|------|
| 距离 | km | 行驶距离 |
| 时间 | min | 耗时、时间窗、停留时长 |
| 经纬度 | GCJ-02 | 高德坐标系，x=经度，y=纬度 |
| 索引 | 0=depot | 0 索引恒为酒店，景点从 1 开始 |
| 时间窗 | (start, end) | 距午夜分钟数，0=00:00，1440=24:00 |

## 数据模型边界

后端分两套模型：**API 边界用 Pydantic**（`backend/api/schemas.py`，自动生成 OpenAPI），**引擎内部用 TypedDict**（`backend/typedefs.py`，零运行时开销）。前端类型由 OpenAPI 生成（`api/types.generated.ts`）并辅以手工 `types.ts`。

## API 模型（schemas.py）

### 景点请求项 POIItem

| 字段 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `name` | `str` | — | 景点名称 |
| `lon` / `lat` | `float` | — | GCJ-02 坐标 |
| `tw_start` | `float` | 480 | 营业开始（8:00） |
| `tw_end` | `float` | 1020 | 营业结束（17:00） |
| `stay` | `float` | 0 | 建议停留时长 |
| `expected_arrival` | `float \| None` | None | 期望到达时间 |

### 规划请求 PlanRequest

统一适用于 `/api/suggest` 与 `/api/plan`：

```
{ city, hotel_name, hotel_lon, hotel_lat, hotel_tw_start, hotel_tw_end,
  min_days, spots: POIItem[], n_days, mode: 'fast'|'deep', day_start,
  cost_matrix?, dist_matrix?, penalty_weight, early_wait_weight, late_return_weight }
```

`n_days=None` → 建议模式（ca_suggest）；`n_days` 有值 + `mode='deep'` → VNS 深度规划。

### POI 查询

- 请求 `POILookupRequest { city, names[] }`
- 响应 `POILookupResponse { items: POILookupItem[], failed: string[] }`
- `POILookupItem { name, lon, lat, address, tw_start?, tw_end? }`：`tw_*` 由 LLM 解析 opentime2，失败为 `None`。

### 异步任务（suggest / plan 通用）

- 提交响应 `TaskSubmitResponse { task_id }`
- 状态详情 `TaskDetail { task_id, task_type, status: pending/running/done/failed, result?, error? }`
- `result` 仅 done 存在：`SuggestResult` 或 `PlanResult`。

`SuggestResult`：`{ type:'suggestion', suggestions: SuggestionItem[], algo_time, spots, polylines, amap_api_key, amap_security_code }`（不再含 cost_matrix，矩阵由后端驾车快照缓存托管）。

`PlanResult`：`{ solution, mode?, best_days, best_m, spots, dataset_name?, algo_time, daily_schedules, cost_matrix?, dist_matrix?, polylines, commentary?, amap_api_key?, amap_security_code? }`。

### 历史与反馈

- `HistoryCreate`：device_id/note/city/hotel/n_days/cost/spot_count/plan_result/request_params。
- `HistorySummary`、`HistoryDetail`：列表/详情字段（后者含全量 plan_result）。
- `FeedbackCreate`：name?/contact?/content(必填)/rating?/page?。

## 引擎内部模型（typedefs.py）

### SpotDict

求解器核心景点类型：`{ name, x, y, tw:(start,end), stay, original_tw:(start,end), lon?, lat?, expected_arrival? }`。`tw` 为收缩后的有效时间窗，`original_tw` 为原始营业窗。

### RouteResult

`solve_groups` 输出：`{ routes, histories?, total_cost, total_dist, wait, late, valid }`。

### ScheduleItem

单日行程项：`{ name, arrival, departure, tw, stay, arrival_status, departure_status }`。注意后端 `stay` 为展示字符串（如 `"180 min"`），前端 `types.ts` 中为 `number`。

### PlanResult（typed）

`{ solution, mode, best_days, best_m, spots: dict[int, SpotDict], dataset_name, algo_time, daily_schedules, cost_matrix, dist_matrix, polylines, commentary, amap_api_key?, amap_security_code? }`。对应 API 层 Pydantic `PlanResult`，但因序列化差异 `spots` 的 key 变为字符串、`tw/original_tw` 变为数组。

## 索引约定

- 数组与字典 **0 索引固定为酒店（depot）**。
- `routes` 序列 `[0, 3, 1, 0]` = 酒店 → 景点3 → 景点1 → 酒店。
- `polylines` key 格式 `"{fromIdx}_{toIdx}"`，如 `"0_3"`。
- `best_days` 与 `daily_schedules.length` 一致。

## 边界与约束

| 约束 | 值 | 来源 |
|------|-----|------|
| 景点数下限 | 1 | PlanRequest.spots |
| 天数范围 | [min_days, n_spots] | ca_suggest 循环 |
| 天数下界（默认） | `max(1, n_spots // 8 + 1)` | search.py |
| 聚类方法数 | 6 | clustering.py |
| 成本矩阵形状 | (N+1, N+1) | N=景点数 |
| 任务状态 | pending/running/done/failed | tasks/worker.py |

## 术语表

| 术语 | 定义 |
|------|------|
| GCJ-02 | 高德坐标系（x=经度，y=纬度） |
| plan_tasks | 异步规划任务表（PlanTask ORM） |
| original_tw | 原始营业时间窗（标注 tw 收缩前） |
| polyline | 真实路径坐标串（"lat,lng;lat,lng"） |

## 维护契约

修改数据模型时必须同步：

- **改 schemas.py**：跑 `make gen-api` 重新生成前端 `api/types.generated.ts`，同步 [backend.md](backend.md)、[frontend.md](frontend.md)。
- **改 typedefs.py**：同步 [engine 调用点](../backend/engine/) 与 [data.md](data.md) 本节。
- **改 ORM 模型**（data/model/models.py）：同步异步任务/历史/反馈字段，见 [backend.md](backend.md)。
- **改前后端字段语义**（如 stay 字符串 vs 数值）：同时更新本页与 [frontend.md](frontend.md) 注释。