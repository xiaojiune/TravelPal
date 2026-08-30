---
task: "TravelPal 架构收敛到六边形(domain 端口+核心 / infra 实现) + P1 想法20 取消回滚 + 端点语义化(or-ca/or-vns、/or /show) + 任务生命周期统一；下一步=更新 travelpal-architecture skill / 接入层归位 / P1 剩余项"
status: "continue"
date: "2026-08-31"
version: "0.1.0"
range: "2026-08-30..2026-08-31"
git: "7200d8c..HEAD"
---
# 代码会话交接

## 上一段进行到哪

本会话完成并提交（均在 dev，未 push；dev 领先 origin/dev **84 commit**，工作区干净）：

### P1 想法20 Celery 取消回滚（完成）
- 后端：`TaskCancelled` 哨兵 + PlanTask `canceled` 态；`amap_loader/pipeline` 逐段 `cancel_check` 抛 `TaskCancelled`；worker `_watch_cancel` 监护 + `run_in_executor`（executor 放线程池跑、释放 loop）+ 捕获置 `canceled`。
- API：`POST /api/tasks/{id}/cancel`（归属校验）+ `GET /api/tasks` 列表；schemas 加 `TaskListItem/TaskListResponse/TaskCancelResponse`。
- 前端：工具栏「📋 异步任务」面板（列表/取消/查看结果）、`cancelTask/listTasks`。
- 🌟 worker 状态落库 bug（`abeceba`）：done/failed/canceled 分支漏 `commit` → status 卡 running，补 commit 修复。

### 任务生命周期统一收敛（完成，`69afe28` 起）
- 提交任务不阻塞：去 `useTaskPolling` await 等待，改 `registerTask` 登记进 store 任务集合 + 后台轮询（store 级，无活动任务即停 `3584ac9`）。
- 生命周期：游客内存（刷新清）、登录 localStorage（关/刷保留、登出清，`setPersistTasks/hydrate/clear` + App.vue `watch isLoggedIn`）。
- 任务卡片语义化（`bea7161`）：边框随状态色、任务名 `任务X-{求解|调整}`（最新在顶=任务N）；列表分区（`baa8fe4`，最新一条置顶、其余标「历史」）。

### 端点/路由语义化（完成，`7789579`）
- 后端 `POST /api/suggest`→`/api/or-ca`（CA 建议）、`/api/plan`→`/api/or-vns`（VNS 求解）；task_type `or-ca/or-vns`。
- 前端路由 `/suggest`→`/or`（生产页）、`/plan`→`/show`（展示页）；组件重命名 SuggestPage→OrPage、PlanPage→ShowPage；导航/`router.push` 目标同步。

### 前端修复
- 地图不聚焦（`4e85a3f`）：`viewResult` 回填 `cache.suggestSpots/polylines/algoTime`（重构后 fetchSuggest 不再回填缓存）。
- 启程时间默认 08:00（`62ef774`）：`day_start` 默认 0→480（plan store + `PlanRequest` schema + HomePage 黄警告判断）。

### 架构收敛到六边形/整洁架构（本会话主线）
按 `travelpal-architecture` 演进式（绞杀者）收敛为 **domain 端口/核心 + infra 实现** 两层：
- 批1 `ada0f24`：端口定义上移 `domain/ports.py`（`Solver`/`DrivingDataProvider`/`SessionStore`）；`/auth` 拆（密码哈希→`domain/security.py`、Redis 会话→`infrastructure/auth/session_store.py`，`api/auth.py` 注入 `_session_store`）；删顶层 `/auth`。
- 批2 `ca80777`：组合根注入——`pipeline` 收 `driving` 参数，domain 不再 import 实现；`tasks/executors` + `agent/tools` 装配注入 `AmapDrivingProvider`。
- 批3a `4a6fcf1`：`backend/data` → `infrastructure/data`（amap/driving_cache/driving_service/model/conversations/checkpointer）。
- 批3b-1 `a9bdc40`：`solver_factory` 组合根注入（search 求解选择可注入，回退 `get_solver`）。
- 批3b-2 `e1bf3ad`：engine 物理拆分——`ca/vns/solver` → `infrastructure/engine`（Solver 实现+注册表）；`search/clustering/fitness` → `domain`；`search(domain)` 解耦（删对 engine.ca/solver 依赖，用域层早退常量 + `solver_factory`，None 抛错）；删旧 `engine/__init__`。
- 另有 `e0f190b`（driving_service 收口+`preference` 口）、`04c3838`（端口-适配器+`SOLVER_REGISTRY`）、`baf81ac`（architecture skill 补绞杀者模式）。

**当前后端分层**：
- `domain/`：pipeline(OR编排) / search / clustering / fitness / ports / security / llm_service / weather_service。
- `infrastructure/`：data/、engine/(ca/vns/solver)、auth/session_store、llm/、retrieval/、weather/。
- 接入/应用层（仍在顶层）：api/、tasks/、agent/、mcp/、observability/、utils/。

## 决定 / 已知坑（累积）

- 认证：httpOnly Cookie + Redis 服务端会话（非 JWT）兼容 SSE；第三方走 API Key 双轨（ADR-010/011）。
- 会话记忆方案 B：orchestrator 内部不做 add_messages 转换，历史由 `get_history_messages` 读 checkpoint 后拼接。
- 会话归属：登录用户会话持久、复用最近未过期；游客每次新建；`_belongs` 防串。
- LavinMQ 用默认 guest/guest（独立 sy 账号被 bcrypt hash 的 compose 插值破坏，暂放弃）；容器间 broker 用服务名 `lavinmq`，勿用 localhost；docker 部署 `.env` 勿设 CELERY_BROKER_URL（compose 写死）；端口 5672/15672 仅回环 127.0.0.1；`make dc-up` 已含 lavinmq。
- 高德：熔断在 `_amap_get`，仅瞬时错误（网络/超时/5xx）重试，业务态不重试；熔断期抛"高德 API 熔断中"快速失败。
- 前端坑：`make format` 破坏 Vue 内联多语句 `@click="a; b"`（prettier 去分号），验证用 `vite build`。
- git 操作必须用户明确，未经确认不 commit；`.env` 不进 git，密钥仅 SSH 直传服务器。
- Agent/工具面板/门户 z-index：AgentPanel 遮罩(1999)/面板(2000)/navbar(2001)。

**本会话新增决策/坑**：
- **架构分层（六边形）**：domain 只端口/核心编排/纯算法（零外部依赖）；infra 实现 domain 端口（可插拔引擎/数据源）；应用层（tasks/agent）组合根装配注入。换数据源/换算法只动 infra，domain 零改动。
- **ML 定位**：不做路径计算，承载用户记忆/习惯（软约束），经**可量化参数注入 OR 目标函数**（**不是**成本矩阵；成本矩阵保持纯净）。`run_planning.preference` 口已留（当前不启用）。
- **端口-适配器**：`domain/ports.py` 端口 + infra 实现；`solver_registry/get_solver` 在 `infra/engine/solver.py`（应用层装配注入）；`DrivingDataProvider` 在 `domain/ports.py`，`AmapDrivingProvider` 在 `infra/data/driving_service.py`。
- **任务生命周期**：提交不阻塞（registerTask + store 后台轮询）；游客内存/登录 localStorage；登出清；轮询无活动任务即停（防空轮询）。
- **取消回滚**：worker 状态改写必须 `commit`（async_session 退出回滚）；协作式取消靠 `_watch_cancel` + `run_in_executor`（executor 线程池跑放 loop）+ `cancel_check` 逐段探测。
- **端点语义化**：`or-ca`(CA建议)/`or-vns`(VNS求解)、`/or`(生产)/`/show`(展示)；task_type 用 `or-ca/or-vns`。
- **地图**：`AmapMap.setFitView` 在无覆盖物时静默失效（默认中心北京）；确保 data 有值才渲染地图。
- **tests 迁移遗留**：`test_contract`/`test_agent` 等已同步 `or-ca/or-vns`、`day_start=480`、`pipeline/checkpointer/conversations` 新路径；新增测试跑 `solver_factory` 需传 `get_solver`。
- **依赖注入**：`pipeline`(domain) 经参数收 `driving`/`solver_factory`（None 抛错）；`search.solve_groups/cluster_and_solve` 的 `solver_factory` 默认 None、None 时抛错（组合根必注入）。

## 下一步目标

1. **更新 `travelpal-architecture` skill**（用户稍后触发）：基于 actual domain/infra 分层，把 backend.md 的"engine/data 独立层"改为"domain 端口+核心 / infra 实现"，补"新代码必须进 domain/infra、不从顶层开业务目录"硬约束。
2. **接入层归位（可选）**：api/tasks/agent/mcp/observability/utils 是否进一步归 infra（或明确为应用层）。
3. **P1 剩余项**：想法21-B 索引（`plan_tasks` `(status,created_at)` 复合 + `result`/`request_params` JSONB GIN）、想法3 Celery 用优（优先级/死信/重试）、想法19 QPS、想法14 cache。
4. **dev 领先 origin/dev 84 commit 未 push**：涉及大量重构（架构收敛+任务系统），建议联调验证后再 push（需用户明确）。
