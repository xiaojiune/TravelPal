# 前端结构

## 修改记录

| 日期 | 变更 |
|------|------|
| 2026-07-18 | 全量重写：同步实际代码结构，新增数据流图与交叉引用 |

## 1. 架构总览

前端为 **Vue 3 + TypeScript + Vite** SPA，状态管理使用 **Pinia**（setup 语法），HTTP 客户端使用 **Axios**，路由使用 **Vue Router**（hash-free history 模式）。

架构特点：

- **全量 TypeScript**：frontend/src 下全部为 .ts / .vue 文件，API 类型由 openapi-typescript 从后端 OpenAPI 规范生成
- **Composable 模式**：将 POI 搜索、编辑表格、打字机效果等分离为独立 composable
- **SSE 流式渲染**：Agent 聊天使用 EventSource 实现打字机效果
- **模块化组件**：地图（AmapMap）、行程（SchedulePanel）、聊天（ChatMessage）互相独立

## 2. 目录结构

```
frontend/
├── index.html                    # SPA 入口 HTML
├── vite.config.js                # Vite 构建配置 + /api 代理
├── tsconfig.json                 # TypeScript 配置
├── eslint.config.js              # ESLint 扁平化配置
├── package.json                  # 依赖与脚本
├── .npmrc                        # npm 镜像配置
├── .prettierrc                   # Prettier 格式化配置
│
├── public/                       # 公共静态资源
├── dist/                         # 构建产物（gitignored）
│
└── src/
    ├── main.ts                   # Vue 应用入口（挂载 Pinia + Router）
    ├── App.vue                   # 根组件：全局导航栏 + <router-view>
    ├── style.css                 # 全局样式
    │
    ├── pages/                    # 页面级组件（5 个路由页面）
    │   ├── HomePage.vue          首页：城市输入 + 参数配置
    │   ├── SuggestPage.vue       方案建议列表（ca_suggest 结果展示）
    │   ├── PlanPage.vue          核心规划展示页（地图 + 行程 + 评语）
    │   ├── AgentPage.vue         LLM Agent 聊天页（SSE 流式对话）
    │   └── HistoryPage.vue       历史记录分享站（API 分页列表）
    │
    ├── components/               # 可复用组件
    │   ├── AmapMap.vue           高德 2D 地图（路线 + 景点标记）
    │   ├── SchedulePanel.vue     每日行程表（折叠 + 高显联动）
    │   └── ChatMessage.vue       单条聊天消息（打字机效果）
    │
    ├── composables/              # 组合式函数
    │   ├── useEditTable.ts       规划点编辑表格（增删改 + 确认）
    │   ├── usePoiSearch.ts       POI 搜索（自动确认、无需勾选）
    │   └── useTypewriter.ts      打字机效果（逐字 + 追加模式）
    │
    ├── router/
    │   └── index.ts              Vue Router 路由表（5 条懒加载路由）
    │
    ├── services/
    │   └── api.ts                Axios 封装（7 个后端 API 函数 + History 类型）
    │
    ├── stores/
    │   └── plan.ts               Pinia store（输入参数 + 方案 + 结果状态）
    │
    ├── types.ts                  # 手工维护的类型定义
    │
    └── api/
        └── types.generated.ts    # openapi-typescript 自动生成（OpenAPI 驱动）
```

## 3. 页面组件

全部路由使用懒加载（`() => import(...)`），5 个页面组件：

- **HomePage.vue**（`/`）
  城市输入、酒店选择、景点编辑、参数配置（惩罚/起程时间/最小天数），触发 `/api/suggest`。

- **SuggestPage.vue**（`/suggest`）
  展示 ca_suggest 多方案卡片（按天数分组）。
  fast 模式前端合成 PlanResult 跳转 /plan；deep 模式调 `/api/plan` 后跳转。

- **PlanPage.vue**（`/plan`）
  纯展示页：指标栏（成本/距离/等待）、评语、AmapMap 地图、SchedulePanel 行程表、原始请求参数折叠面板。

- **AgentPage.vue**（`/agent`）
  LLM Agent 对话：输入框 + SSE 流式消息列表 + 打字机效果。

- **HistoryPage.vue**（`/history`）
  历史记录分页列表，点击拉取完整数据跳转 /plan。

## 4. 可复用组件

- **AmapMap.vue**（PlanPage）
  高德 2D 地图渲染：展示 routes 路线、spots 景点标记、真实 polylines 轨迹。
  支持多日高显（`highlightDays`）和景点高亮（`highlightSpot`）。

- **SchedulePanel.vue**（PlanPage）
  每日行程表：按天折叠/展开，行程项含到达/离开时间及状态。
  高显联动展开，地图点击高亮对应景点。

- **ChatMessage.vue**（AgentPage）
  单条消息渲染组件：支持打字机逐字效果（`useTypewriter`），区分用户/助手角色样式。

## 5. Composables

- **useEditTable**
  管理 HomePage 规划点编辑表格（酒店 + N 景点），维护 `editRows` 临时数组，确认时同步 store。
  关键方法：`editRows`, `editHint`, `confirmEdit`, `deleteRow`。

- **usePoiSearch**
  POI 搜索逻辑：根据城市+名称列表调 `postPoiLookup`，自动填充坐标和时间窗。
  关键方法：`searchHotel`, `searchSpots`, `loading`。

- **useTypewriter**
  打字机效果：`start(text)` 逐字播放，`append(chunk)` SSE 流式追加，`reset()` 清空。
  关键方法：`displayText`, `start`, `append`, `reset`。

## 6. 状态管理

单一 Pinia store `plan`（setup 语法），三组状态：

### 输入状态

| 字段 | 类型 | 说明 |
|------|------|------|
| `city` / `hotelName` / `hotelLon` / `hotelLat` | `string` / `number` | 城市及酒店 |
| `dayStart` | `number` | 每日启程时间（距午夜分钟数） |
| `spots` | `SpotFormItem[]` | 景点列表（名称/坐标/时间窗/停留） |
| `penaltyWeight` / `earlyWaitWeight` / `lateReturnWeight` | `number` | 惩罚权重参数 |
| `minDays` | `number \| null` | 最小天数（null 为引擎自动推断） |
| `isParamsSaved` | `boolean` | 用户是否已完成参数确认 |

### 方案状态

| 字段 | 类型 | 说明 |
|------|------|------|
| `suggestions` | `SuggestionItem[]` | ca_suggest 返回到多组方案 |
| `suggestSpots` | `Record<string, SpotDictItem>` | suggest 返回的景点字典（含 original_tw） |
| `suggestCostMatrix` / `suggestDistMatrix` | `number[][]` | 成本/距离矩阵，deep 模式复用 |
| `suggestPolylines` | `Record<string, string>` | 真实路径坐标字典 |

### 结果状态

| 字段 | 类型 | 说明 |
|------|------|------|
| `planResult` | `PlanResult \| null` | 当前展示的规划结果 |
| `deepResults` | `PlanResult[]` | 深度模式生成的规划结果列表 |
| `historyRecordId` | `string \| null` | 从历史加载的记录 ID（防重复分享） |
| `historyRequestParams` | `Record \| null` | 历史记录原始请求参数 |

关键方法：`buildRequest(nDays)` 构造请求体，`reset()` 清空全部状态。

## 7. API 层

后端 API base URL 由 Vite 代理（`/api` → `localhost:8000`）。

### 核心 API

| 函数 | 端点 | 用途 |
|------|------|------|
| `postPoiLookup(city, names)` | `POST /api/poi-lookup` | 批量查询 POI 坐标 / 营业时间 |
| `postSuggest(data)` | `POST /api/suggest` | 获取多组候选方案（ca_suggest） |
| `postPlan(data)` | `POST /api/plan` | 指定天数执行深度规划（VNS） |
| `postChat(message, sessionId)` | `POST /api/chat` | Agent SSE 流式对话 |

### 历史记录 API

| 函数 | 端点 | 用途 |
|------|------|------|
| `getHistoryList(page, pageSize)` | `GET /api/history` | 分页获取历史记录摘要 |
| `getHistoryDetail(id)` | `GET /api/history/{id}` | 获取完整规划结果及请求参数 |
| `postHistory(data)` | `POST /api/history` | 保存当前方案到分享站 |
| `deleteHistory(id, deviceId)` | `DELETE /api/history/{id}` | 删除记录（device_id 鉴权） |
| `getDeviceId()` | 纯前端 | 生成/读取匿名设备标识 |

## 8. 类型定义

类型体系分两层：

```
api/types.generated.ts     ← openapi-typescript 自动生成（后端 schema 驱动）
types.ts                   ← 手工补充（前端专用类型 + 生成类型的扩展）
```

| 类型 | 来源 | 说明 |
|------|------|------|
| `PlanRequestPayload` | types.ts | 扩展生成的 PlanRequest，增加 cost_matrix/dist_matrix |
| `POILookupItem` | types.ts | 从 generated 重新导出 |
| `SuggestionItem` | types.ts | 手工维护（ca_suggest 返回结构） |
| `PlanResult` | types.ts | 完整规划结果（含 solution/schedules/commentary/polylines） |
| `PlanResultSolution` | types.ts | routes / total_cost / total_dist / valid |
| `ScheduleItem` | types.ts | 单日行程项（到达/离开/状态） |
| `SpotFormItem` | types.ts | 纯前端表单景点项（twStart/twEnd/expectedArrival） |
| `SpotDictItem` | types.ts | 后端返回的景点字典项（x/y/tw/original_tw） |
| `ChatMessage` | types.ts | 聊天消息（user/assistant） |

## 9. 构建与配置

| 配置文件 | 说明 |
|---------|------|
| `vite.config.js` | Vite 构建：Vue 插件、@ 别名、devServer → `/api` 代理到 localhost:8000 |
| `tsconfig.json` | TypeScript 严格模式配置 |
| `eslint.config.js` | ESLint 扁平化配置（Flat Config） |
| `.prettierrc` | Prettier 格式化规则 |
| `.npmrc` | npm registry 镜像配置 |

开发命令（通过根目录 Makefile）：

```bash
make dev      # 启动 Vite 开发服务器（port 5173）
make build    # 生产构建到 dist/
make lint     # ESLint 检查
make typecheck # vue-tsc 类型检查
```

## 10. 数据流图

### 页面间数据流转

```
HomePage                          SuggestPage                     PlanPage
   |                                  |                              |
   |-- POST /api/suggest -----------> |                              |
   |   ← suggestions + spots          |                              |
   |   + cost_matrix + dist_matrix    |                              |
   |   + polylines + amap keys        |                              |
   |                                  |                              |
   |-- router.push(/suggest) -------> |                              |
   |                                  |                              |
   |                                  |--- fast: 点击卡片 ---------> |
   |                                  |   onCardClick(s)             |
   |                                  |   buildPlanResult(s)         |
   |                                  |   store.planResult = ...     |
   |                                  |   router.push(/plan)         |
   |                                  |                              |
   |                                  |--- deep: 点"获取规划" ----> |
   |                                  |   POST /api/plan (mode=deep) |
   |                                  |   ← PlanResult               |
   |                                  |   store.deepResults.push(r)  |
   |                                  |   再点卡片 → router.push     |
   |                                  |                              |
   |                                  |                   PlanPage  |
   |                                  |                   只读 store |
   |                                  |                   不调 API   |
   |                                  |                              |
HistoryPage                           |                              |
   |                                  |                              |
   |-- GET /api/history --------------|                              |
   |-- 点击: GET /api/history/{id} --|                              |
   |   store.planResult = detail      |                              |
   |   router.push(/plan) ----------->|                              |
```

### 状态流向

```
buildRequest() → POST /api/suggest → store.suggestions + suggestSpots
                                            + suggestCostMatrix + suggestPolylines
                                                    ↓
                                     SuggestPage 分组展示卡片
                                                    ↓
                                     onCardClick → buildPlanResultFromSuggestion
                                         + store.suggestSpots  ← sugget 响应缓存
                                         + store.suggestPolylines
                                                    ↓
                                          store.planResult
                                                    ↓
                                          PlanPage 渲染
```

详见 [`backend.md`](./backend.md) 第 8 章的引擎链路与规划流程。

## 11. 与后端交叉引用

- **HomePage → POST /api/suggest**
  `routes.py suggest` → `pipeline.run_planning(n_days=None)`
  后端参考：[`backend.md#7.3`](./backend.md#73)

- **SuggestPage → POST /api/plan**
  `routes.py plan` → `pipeline.run_planning(n_days` 指定`)`
  后端参考：[`backend.md#7.4`](./backend.md#74)

- **AgentPage → POST /api/chat**
  `routes.py chat` → `agent.planner.PlannerAgent`
  后端参考：[`backend.md#5`](./backend.md#5)

- **PlanPage 渲染数据**
  `pipeline.run_planning` 返回 `PlanResult`
  后端参考：[`backend.md#8.3`](./backend.md#83)

- **历史记录 POST /api/history**
  `routes.py create_history`
  后端参考：[`backend.md#7.5`](./backend.md#75)
