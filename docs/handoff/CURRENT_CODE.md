---
task: "TravelPal 用户系统全链路 + 视觉升级 + P1 稳定性起步：轴3~轴6、门户/工作区/三级界面、LavinMQ、API 降级熔断；下一步为 P1 想法20 取消回滚"
status: "continue"
date: "2026-08-30"
version: "0.1.0"
range: "2026-08-28..2026-08-30"
git: "a1d3fe8..HEAD"
---
# 代码会话交接

## 上一段进行到哪

本代码会话完成并提交（均在 dev，未 push；dev 领先 origin/dev 62 commit，工作区干净）：

### 用户系统（轴3~轴6，已完成）
- 轴3 鉴权接入：`get_current_user_optional`/`require_admin` + share/plan_tasks/feedback 归属。
- 轴4 前端认证：登录/注册页 + user store + 路由守卫 + SSE 带凭据。
- 轴5 Admin 操作台：后端管理 API（`require_admin` 放行 admin/super_admin）+ 前端只读页（前端仅 super_admin 激活入口）。
- 轴6 会话/记忆地基：LangGraph checkpointer + conversations 表 + `/api/chat` 续接历史 + `GET /api/chat/history`（登录恢复最近会话）+ 前端打开面板自动回显。记忆机制方案 B（保留 OpenAI dict 消息协议，`add_messages` 不用于 orchestrator）。
  - 关键提交：`28b98d8`(后端) `429fc4a`(前端) `5caa396`(会话绑定用户可恢复) `a1d3fe8`(登录/登出覆盖所有数据 reset) `fe8d2c4`(历史只读接口) `401cf60`(前端恢复最近会话)。

### 视觉升级（门户/工作区/三级界面，已完成）
- 品牌门户 `/`（一级）+ 工作区降二级 `/home` + 三级 `/profile`/`/admin`（`21e65c0`）。
- 个人中心入口 + 问卷迁至关于页（`0573ebe`）；门户登录态显示（`dfbbed2`）；非门户回门户 + 管理台居中 + AI 醒目（`5fbb7b3`）。
- 登录注册默认落工作区（`5d82bf4`）；工作区 UI（AI 右上浮动、新建归位标题行、门户样式登录注册）（`ba31a9a`）。
- 门户 Hero 高级感（大排版 + 品牌渐变柔光 + mock 演示卡透视 + 入场微动效）（`b5ace83`）；登录/注册品牌 header（`801703e`）。
- Agent 改为固定右栏共创 + 工具面板滑入动效（`a6ec878`/`a5357a8`）。
- 门户不触发 401 + 工作区内容水平居中（`c4979f0`）。

### 后端架构调整
- 会话存储迁 data 层（`7a172d9`）；pipeline 迁 domain（`2bc615f`）；删 chroma_db 死残留（`9b3da0b`）。

### P1 稳定性（已做的两项）
- idea9 Celery broker 升级 LavinMQ（`64dea01`/`b26c401`/`ac33dde`/`e1582c4`）：AMQP 0-9-1，Redis 仍作缓存/session；compose 加 lavinmq 服务（端口仅回环 127.0.0.1，防公网暴露）；端到端验证通过。
- idea1 API 降级与熔断（`a6dba8e` + 测试 `8bb9115`）：高德 `_amap_get`（熔断+3次指数退避重试）+ `CircuitBreaker`（3次/30s 半开探测）+ LLM `_create_completion` 重试；tenacity 提主依赖。

## 决定 / 已知坑

- 认证：httpOnly Cookie + Redis 服务端会话（非 JWT）兼容 SSE；第三方走 API Key 双轨（ADR-010/011）。
- 会话记忆方案 B：orchestrator 内部不做 add_messages 转换（会破坏现有 LLMService/SSE），历史由 `get_history_messages` 读 checkpoint 后拼接。
- 会话归属规则：登录用户会话持久、复用最近未过期；游客每次新建；`_belongs` 防串。
- LavinMQ 用默认 guest/guest（独立 sy 账号被 bcrypt hash 的 compose 插值破坏，暂放弃）；容器间 broker 必须用服务名 `lavinmq`，勿用 localhost；docker 部署 `.env` 勿设 CELERY_BROKER_URL（compose 写死）。
- LavinMQ 端口（5672/15672）已绑定 127.0.0.1 仅回环；compose 里 `ports` 用 `127.0.0.1:xx:xx` 格式。
- 高德：熔断在 `_amap_get`，仅瞬时错误（网络/超时/5xx）重试，业务态（status!=1）不重试；熔断期抛"高德 API 熔断中"快速失败。
- 前端坑：`make format` 会破坏 Vue 内联多语句 `@click="a; b"`（prettier 去分号），验证用 `vite build` 而非 format/prettier；`kind` 类的小工具类。
- git 操作必须用户明确，未经确认不 commit（教训）。
- `.env` 不进 git（DIRECTORY ignore 生效）；密钥仅 SSH 直传服务器，勿写进源码/文档。
- Agent/工具面板/门户的 z-index 层级：AgentPanel 遮罩(1999)/面板(2000)/navbar(2001)。

## 下一步目标

1. **P1 想法20 Celery 取消回滚**（用户痛点最强，待做）：
   - `plan_tasks` 加 cancel 态（或取消标志）；worker `_execute_task` 执行前/间查状态，被取消则不执行/快速退出。
   - HTTP 加 `POST /api/tasks/{task_id}/cancel`（归属校验）；前端任务列表加取消入口。
   - 先出计划等批准（plan-build），git 操作需用户明确。
2. **P1 想法21-B 索引优化**（低成本快赢）：`plan_tasks` 加 `(status,created_at)` 复合索引；`result`/`request_params` JSONB 加 GIN 索引。
3. P1 其余：想法3 Celery 用好（优先级/死信/重试，可基于 LavinMQ）、想法19/14（QPS/缓存）、想法20 已列。
4. dev 领先 origin/dev 62 commit，未 push（用户未明确要求 push）。
