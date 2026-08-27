# 前端架构详解

## 修改记录

| 日期 | 变更 | 动机 |
|------|------|------|
| 2026-08-25 | 重写：异步任务轮询取代同步 suggest/plan，Agent 全局化浮动面板，新增 About/反馈与 ToolPanel 等，对齐 structure 模板 | 前端已演化，旧文档路径/组件过时 |
| 2026-07-18 | 全量重写：同步实际代码结构，新增数据流图与交叉引用 | 建立前端独立文档 |

## 读者指南

| 列 | 内容 |
|----|------|
| 面向读者 | 前端开发者 |
| 阅读前置 | [data.md](data.md)、[backend.md](backend.md) |
| 阅读目标 | 读懂前端分层、页面路由、状态管理与 API 封装 |

## 架构总览

前端为 **Vue 3 + TypeScript + Vite** SPA，状态管理 Pinia（setup 语法），HTTP 客户端 Axios（统一实例 `services/http.ts`），路由 Vue Router（hash-free history，懒加载）。API 类型由 openapi-typescript 从后端 OpenAPI 生成（`api/types.generated.ts`）。

架构特点：

- **全量 TypeScript**：`src/` 下全部为 .ts / .vue，类型由后端 schema 驱动。
- **Agent 全局化**：Agent 聊天不是独立页面，而是 `App.vue` 里的浮动抽屉（`AgentPanel`），配 `ToolPanel` / `ToolRail` 工具面板。
- **异步任务**：suggest / plan 立即返回 `task_id`，前端轮询 `GET /api/tasks/{id}`（`useTaskPolling`）。
- **Composable 模式**：POI 搜索、编辑表格、打字机、任务轮询等分离为 composable。
- **SSE 流式渲染**：Agent 对话用 EventSource 打字机效果。

## 目录结构

```
frontend/
├── index.html / vite.config.js / tsconfig.json / eslint.config.js / package.json
├── static/  公共静态资源
└── src/
    ├── main.ts          Vue 挂载：Pinia + Router + 注入品牌色 CSS 变量
    ├── App.vue          根组件：导航 + 全局 Agent 抽屉 + 移动端降级提示
    ├── theme.ts         品牌色主题变量（applyThemeVars，防首帧 FOUC）
    ├── style.css        全局样式
    ├── amap.d.ts        高德地图类型声明
    │
    ├── pages/           页面组件（5 个路由页面）
    │   ├── HomePage.vue     首页：城市/酒店/景点输入 + 参数配置
    │   ├── SuggestPage.vue  方案建议列表（异步任务结果）
    │   ├── PlanPage.vue     规划结果展示（地图 + 行程 + 评语）
    │   ├── SharePage.vue  方案分享分享站
    │   └── AboutPage.vue    关于页面 + 用户反馈问卷
    │
    ├── components/       可复用组件
    │   ├── AmapMap.vue      高德 2D 地图
    │   ├── SchedulePanel.vue 每日行程表
    │   ├── ChatMessage.vue  单条聊天消息（打字机）
    │   ├── ChatStream.vue   SSE 流式消息列表
    │   ├── AgentPanel.vue   全局 Agent 浮动抽屉
    │   ├── ToolPanel.vue    工具查询结果面板（POI 待选 + 其它结果）
    │   ├── ToolRail.vue     工具面板切换导航
    │   ├── ToolResultCard.vue 工具结果卡片
    │   ├── SchemaFormCard.vue  Agent-driven UI 表单卡片
    │   └── FeedbackModal.vue  反馈弹窗
    │
    ├── composables/      组合式函数
    │   ├── useEditTable.ts   规划点编辑表格
    │   ├── usePoiSearch.ts   POI 搜索
    │   ├── useTypewriter.ts  打字机效果
    │   ├── useSuggestCache.ts suggest 结果缓存（矩阵快照）
    │   └── useTaskPolling.ts 异步任务轮询
    │
    ├── router/index.ts      路由表（5 条懒加载路由）
    ├── services/
    │   ├── http.ts          Axios 统一实例（baseURL /api + 错误规范化）
    │   └── api.ts           类型化 API 调用（POI/任务/历史/反馈）
    ├── stores/plan.ts       Pinia store（输入/建议/结果/Agent 对话状态）
    ├── types.ts             手工类型定义
    ├── api/types.generated.ts  openapi-typescript 自动生成
    ├── utils/time.ts        时间格式化工具
    └── content/faq.md       FAQ 内容（markdown）
```

## 数据流

### 页面路由（Agent 已全局化，无独立路由）

| 路径 | 页面 | 用途 |
|------|------|------|
| `/` | HomePage | 输入参数，触发 suggest 任务 |
| `/suggest` | SuggestPage | 展示方案建议（异步任务轮询），可触发布局 |
| `/plan` | PlanPage | 只读展示规划结果 |
| `/shares` | SharePage | 方案分享分享站 |
| `/about` | AboutPage | 关于 + 反馈问卷 |

### suggest / plan 异步流程

HomePage 提交输入 → `store.buildRequest()` → `api.submitTask('suggest', data)` 返回 `task_id` → `useTaskPolling` 轮询 `GET /api/tasks/{id}` → 完成后写入 `store.suggestions` / `store.planResult`。

### Agent 对话（SSE）

`AgentPanel` → `POST /api/chat` → SSE 流式事件 → `ChatMessage`/`ChatStream` 打字机渲染；工具查询结果经 `store.addQueryResult` 汇总到 `ToolPanel`，POI 可加入首页表单（`addPoiToForm`）。

## 术语表

| 术语 | 定义 |
|------|------|
| Pinia store | 全局状态（plan）：输入/建议/结果/Agent 对话 |
| Composable | 组合式函数（useTaskPolling 等） |
| TaskDetail | 异步任务状态（OpenAPI 类型） |
| Agent-driven UI | 由后端 schema 驱动表单渲染（SchemaFormCard） |
| 打字机 | useTypewriter 逐字 + SSE 追加渲染 |

## 维护契约

修改前端时必须同步：

- **改 API 契约**：`schemas.py` 变更需跑 `make gen-api` 重新生成 `api/types.generated.ts`，同步 [data.md](data.md)。
- **加路由页面**：更新 `router/index.ts` + 本页「页面路由」表。
- **加组件**：在 `components/` 下实现，按需更新本页「目录结构」。
- **改 store 字段**：同步 [data.md](data.md) 数据字典与 [backend.md](backend.md) 接口约定。
- **改 Agent 面板**：同步 [agent.md](agent.md) 的 SSE 协议与工具行为。