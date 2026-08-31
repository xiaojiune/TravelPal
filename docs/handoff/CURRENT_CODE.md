---
task: "TravelPal 六边形架构收敛收尾(domain 端口/核心 + infra 实现 + 组合根 + 会话/鉴权归位) + CI 修复/CICD拆分 + 服务器 lavinmq 部署修复；下一步= dev push / P1 剩余项"
status: "done"
date: "2026-08-31"
version: "0.1.0"
range: "2026-08-31"
git: "e6e94c0..HEAD"
---
# 代码会话交接

## 上一段进行到哪

本会话（承接上一档 e6e94c0）完成了架构收敛收尾 + CI/CD 修复 + 服务器部署修复，全部已提交 dev；工作区干净。

### 六边形架构收敛收尾（domain 纯端口/核心）
- `a9c55d1`：domain 求解子目录归位 `solver/`（聚类/适应度/求解入口收敛子域）。
- `576e099`：方案调整逻辑归位 `domain/planning/`（_core + ops/add,remove,balance）+ `solver_factory` 注入，**消除 domain→agent 反向依赖**。
- `77e9c26`：`typedefs.py` 收敛——领域类型归 `domain/types.py`、任务参数归 `tasks/types.py`、跨层异常归 `utils/exceptions.py`；删 typedefs.py。
- `62b5c5a`：新增**六边形依赖守护测试** `backend/utils/architecture.py::check_hexagonal_layering` + `tests/test_contract/test_architecture.py`（锁定 domain←infra←app 依赖方向）。
- `75b5a3e` / `c9dac78`：**会话端口-适配器**——`domain/ports.py` 增 `ConversationStore`/`ConversationSession` 端口 + `domain/conversation_rules.py`（Conversation/TTL/_belongs/_expires 规则）；infra 以 `PostgresConversationStore` + `SqlAlchemyConversationSession` 实现；`api/routes` 经组合根注入。
- `domain/ports.py` 现汇聚 `DrivingDataProvider`/`Solver`/`SessionStore`/`ConversationStore`/`ConversationSession`（端口单一来源）。

### infra 拆轴 + 组合根
- `b345e4e`：`infrastructure/data` 拆轴——ORM 归 `db/`（database/models/checkpointer）、高德适配归 `external/amap/`（amap_loader/driving_cache/driving_service）；`data/` 删除。
- `5ffb87b`：组合根 `backend/di.py`——`get_driving_provider()`（Amap 单例）+ `get_conversation_store()`，消除 3 处 `_driving = AmapDrivingProvider()` 硬编码。
- `c9dac78` / `0395b25` / `cf82fae`：会话/鉴权归位 + 子包 `__init__` 补齐 + **鉴权统一命名** `api/auth.py` + `infra/auth/` + 路由 `/api/auth`（前后端一致）。

### CI/CD
- CI 修复（让 CI 绿）：`bddd62e`(poetry.lock content-hash)、`a3bd1c2`(sync_all `__all__` 规范化)、`e579b48`(alembic/env.py `infrastructure.data.model`→`db`)、`09192c5`(plan_tasks task_type/status 列注释迁移)。
- `9628707`：**CI/CD 拆分**——`ci.yml` 只留 test+frontend(纯 CI)；`deploy.yml`(CD) 用 `workflow_run` 等 CI 全绿且 main push 才部署（等效原 needs）。

### 服务器部署修复（无 git commit）
- 服务器 lavinmq 拉取 403：根因 = 服务器无 lavinmq 镜像 + daocloud 加速器对 lavinmq 403。
- 解决：本地 `docker save cloudamqp/lavinmq:latest` → `scp` 服务器 → `docker load`；服务器 `daemon.json` 换源（`1ms`/`xuanyuan`/`daocloud`）+ `systemctl restart docker`；lavinmq 容器已 Up。

### 其它
- `8a99451`：README 首页截图替换（HomePage.png）。
- `38fb2f9`：git-release skill（区分普通 push 同步与发布打 tag，用户侧）。

## 当前后端分层

- **`domain/`**：`ports.py`(端口汇聚)、`conversation_rules.py`、`types.py`、`security.py`、`llm_service.py`、`weather_service.py`、`pipeline.py`(OR 编排)、`solver/`(clustering/fitness/search)、`planning/`(_core + ops/add,remove,balance)。
- **`infrastructure/`**：`db/`(database/models/checkpointer)、`engine/`(ca/vns/solver)、`external/amap/`(amap_loader/driving_cache/driving_service)、`auth/`(session_store/postgres_conversation_store)、`llm/`、`retrieval/`、`weather/`。
- **应用/接入层（顶层）**：`api/`(auth.py/routes.py/admin.py/server.py)、`tasks/`、`agent/`、`mcp/`、`observability/`、`utils/`；`di.py`(组合根)、`config.py`；`typedefs.py` 已删。
- 依赖方向 `domain ← infra ← app`，组合根 `di.py` 装配注入（driving / conversation store / solver_factory）。

## 决定 / 已知坑（累积）

- 认证：httpOnly Cookie + Redis 服务端会话（非 JWT）兼容 SSE；第三方走 API Key 双轨（ADR-010/011）。
- 会话记忆方案 B：orchestrator 内部不做 add_messages 转换，历史由 `get_history_messages` 读 checkpoint 后拼接。
- 会话归属：登录用户会话持久、复用最近未过期；游客每次新建；`_belongs` 防串。
- LavinMQ 用默认 guest/guest（独立 sy 账号被 bcrypt hash 的 compose 插值破坏，暂放弃）；容器间 broker 用服务名 `lavinmq`；docker 部署 `.env` 勿设 CELERY_BROKER_URL（compose 写死）；端口 5672/15672 仅回环；`make dc-up` 已含 lavinmq。
- 高德：熔断在 `_amap_get`，仅瞬时错误重试，业务态不重试；熔断期抛"高德 API 熔断中"。
- 前端坑：`make format` 破坏 Vue 内联多语句 `@click="a; b"`，验证用 `vite build`。
- git 操作必须用户明确，未经确认不 commit/push；`.env` 不进 git。
- Agent/工具面板/门户 z-index：AgentPanel 遮罩(1999)/面板(2000)/navbar(2001)。
- **架构分层（六边形）**：domain 只端口/核心/纯算法（零外部依赖）；infra 实现 domain 端口；应用层组合根装配注入。换数据源/算法只动 infra。
- **ML 定位**：不做路径计算，承载用户记忆/习惯（软约束），经可量化参数注入 OR 目标函数（**不是**成本矩阵）。`run_planning.preference` 口已留（未启用）。
- **任务生命周期**：提交不阻塞（registerTask + store 后台轮询）；游客内存/登录 localStorage；登出清；无活动任务即停。
- **取消回滚**：worker 状态改写必须 `commit`（async_session 退出回滚）；协作式取消靠 `_watch_cancel` + `run_in_executor` + `cancel_check`。
- **端点语义化**：`or-ca`/`or-vns`、`/or`(生产)/`/show`(展示)。
- **地图**：`AmapMap.setFitView` 无覆盖物静默失效（默认北京）；确保 data 有值才渲染。
- **依赖注入**：`pipeline`(domain) 收 `driving`/`solver_factory`（None 抛错）；`search` 的 `solver_factory` 组合根必注入。
- **会话端口-适配器**：`Conversation`(domain dataclass, `eq=False` 可哈希)；`ConversationSession`/`ConversationStore` 在 `domain/ports.py`；实现 `PostgresConversationStore`+`SqlAlchemyConversationSession` 在 `infra/auth/`；`api/routes` 经 `di.get_conversation_store()` + `SqlAlchemyConversationSession(session)` 注入。
- **鉴权统一命名**：`api/auth.py` + `infra/auth/` + 路由 `/api/auth`（方案2 统一 auth）；前端 openapi/types.generated 本就是 `/api/auth`，无需重生成。⚠️ 对话会话 `postgres_conversation_store.py` 现也在 `infra/auth/`（非认证），如需更纯粹可后续拆到 `infra/conversations/`。
- **架构守护测试**：`check_hexagonal_layering`——domain 禁 infra/api/agent/tasks/mcp；infra 禁 api/agent/tasks/mcp；utils/observability 为工具层默认不违规；`strict=True` 查 domain→utils。CI `test_contract` 含它。
- **CI/CD 拆分**：`deploy.yml` 用 `workflow_run`（CI 全绿 + push main 才部署）；`ci.yml` 只 test/frontend。
- **服务器 Docker 源**：`daemon.json` 三源（1ms/xuanyuan/daocloud）；lavinmq 镜像离线 load（避免 daocloud 403）；建议 compose 固定 lavinmq tag（避开 latest）。
- **auth 曾改名 session**：中途 auth→session→再统一回 auth（cf82fae）。

## 下一步目标

1. **dev push**：dev 领先 origin/dev **8 commit**（`5ffb87b..cf82fae`，未推）：组合根、data 拆轴、会话端口-适配器、注释、可哈希、会话/鉴权归位、子包 __init__、鉴权统一命名。建议联调验证后再 push（需用户明确）。注意 `/api/auth` 前后端已一致。
2. **服务器完整部署**：lavinmq 已修；若 push 后走 `deploy.yml` 自动部署（workflow_run），确认其它镜像（pgvector/redis）走新源 OK、lavinmq 不再 403。
3. **P1 剩余项**（先出计划等批准，遵循 plan-build）：想法21-B 索引（`plan_tasks` `(status,created_at)` 复合 + `result`/`request_params` JSONB GIN）、想法3 Celery 用优（优先级/死信/重试）、想法19 QPS、想法14 cache。
4. **（可选）接入层归位**：api/tasks/agent/mcp/observability/utils 是否进一步归 infra（已评估：当前"三层"自洽，非必要不拆）。
