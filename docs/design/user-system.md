# 用户系统（规划蓝图）

## 元信息

| 项 | 值 |
|----|----|
| 作者 | xiaojiune |
| 最后更新 | 2026-08-27 |
| 状态 | 进行中 |

## 执行摘要

本文件是**规划蓝图**，不是决策记录；具体决策依据见所引用的 ADR（ADR-008 / ADR-009）。核心判断有三：

- **用户系统是主方向**（见 docs/inbox.md 想法5），但它的价值不在「多一个登录页」，而在让对话/规划上下文可追溯、让业务数据归属到用户。
- **会话/状态持久化是用户系统的地基，应与它同批做**，不是它的上层构筑（修正：原标注为「上层构筑」是错的）。缺了它，用户系统只剩「登录 + 查历史」。
- **认证选型用 httpOnly Cookie + Redis 服务端 session**（非 JWT），主因是兼容 /api/chat 的 SSE 流式。

## 背景

- 现状：history_records 用 device_id 软鉴权（前端 localStorage 生成，仅用于删除校验）；feedback / plan_tasks / chat 均无用户归属；后端无状态（localStorage 存最近 10 次规划）；认证依赖一个都没装（无 passlib / pyjwt）。
- 触发原因：用户系统撑起 roadmap 第四阶段「记忆与复访 / 个性化」；业务数据归属账号、可跨设备；Admin 操作台用于运维侧用户/任务/反馈查看；为个性化内容（inbox 想法27）提供第一方语料。

## 总体目标

- **账号**：注册/登录，历史、任务、反馈归属账号，可跨设备查询。
- **会话记忆（地基）**：LangGraph checkpointer + session_id + Redis，上下文可追溯、不串（inbox 想法15）。
- **RBAC**：普通用户 + 管理员（role 字段），Admin 操作台只对 admin 开放。
- **兼容**：未登录访客零门槛可用（背后是 role=guest 的匿名 user），归属键仅 user_id，不破坏现有匿名/分享站。
- **克制**：只做用户名/邮箱 + 密码注册登录；不做找回密码 / 邮箱验证 / OAuth / 多租户（inbox 想法24 后置）。

## 分阶段路线图

| 阶段 | 目标 | 关键交付 | 状态 |
|------|------|----------|------|
| 近期 | 数据模型 + 认证后端 + 鉴权接入 | users 表 + user_id 外键 + 注册/登录/me + get_current_user/require_admin | 🚧 |
| 近期 | 前端认证 + Admin 操作台 | login/register 页 + Pinia + 路由守卫 + admin 页 | 🚧 |
| 中期 | 会话/记忆地基 | conversations + checkpointer + Redis 任务状态缓存 | ⏸ |
| 远期 | 配额/限流 | 登录额度 / guest 限制（inbox 想法1/3） | ⏸ |
| 不做 | 找回密码/邮箱验证/OAuth/多租户 | scope creep 红线 | ❌ |

## 各轴详细设计

### 轴 1：认证选型（Cookie + Redis Session）

- **目标**：浏览器走 httpOnly Cookie + Redis session，EventSource/SSE 自动携带，无需处理 Authorization header；第三方/外部 AI 助手（MCP Client）走 API Key / Bearer 双轨（MCP Server 暴露后本就需鉴权）。
- **实现状态**：⏸ 待实施
- **依赖**：Redis（已有）、config 加 SECRET_KEY + token 时效、CORS credentials、CSRF 防护（SameSite + CSRF token）。

### 轴 2：数据模型（Alembic 迁移）

- **目标**：新增 users 表 + 关联表 user_id 外键（归属键唯一，不设可空）+ conversations 会话表；device_id 降级为匿名凭据（device_token → user_id 映射），不再作为业务归属键；未登录访客对应一条 role=guest 的匿名 user。
- **实现状态**：⏸ 待实施
- **依赖**：Alembic（已有，schema 单一来源）；create_all 已移除（DB_INIT_MODE 废弃），变更走 alembic revision --autogenerate（make dc-migration）+ upgrade head（make migrate），并用 alembic check 防漂移。

### 轴 3：鉴权接入

- **目标**：get_current_user / require_admin 依赖；history/feedback/suggest/plan/tasks 归属校验；先做归属校验、不强锁全站，保障访客可用。
- **实现状态**：⏸ 待实施
- **依赖**：轴1、轴2。

### 轴 4：前端认证

- **目标**：login/register 页、Pinia user store、axios 拦截器（带 cookie）、路由守卫、SSE 请求带凭据。
- **实现状态**：⏸ 待实施
- **依赖**：轴1。

### 轴 5：Admin 操作台（简单版）

- **目标**：后端 require_admin + 一个 admin 页面（用户/任务/反馈）。
- **实现状态**：⏸ 待实施
- **依赖**：轴1、轴3。

### 轴 6：会话/记忆地基

- **目标**：conversations + session_id 绑定 thread_id/user_id + LangGraph checkpointer + Redis 任务状态缓存；上下文不串、可追溯、过期清理。
- **实现状态**：⏸ 待实施
- **依赖**：轴2；复用 LangGraph（ADR-009）。

## 组件状态跟踪表

| 组件 | 状态 | 说明 | 验证 |
|------|------|------|------|
| users 表 + user_id 外键 | ⏸ | 数据模型 | backend/data/model/models.py |
| 认证后端 | ⏸ | pwdlib/bcrypt + pyjwt 或 Redis session | backend/api/routes.py |
| 鉴权依赖 | ⏸ | get_current_user / require_admin | backend/api/ |
| 前端认证 | ⏸ | login/register + Pinia + 守卫 | frontend/src/ |
| Admin 操作台 | ⏸ | 简单版 admin 页 | frontend/src/ |
| 会话/记忆 | ⏸ | conversations + checkpointer | backend/agent/chat/ |

## 落地顺序

| 顺序 | 轴 | 内容 | 依赖 | 回滚方式 |
|------|-----|------|------|----------|
| 1 | 轴2 | users 表 + user_id 外键 + conversations 表；Alembic 迁移 | 无 | alembic downgrade + 还原模型 |
| 2 | 轴1 | 注册/登录/登出/me + 密码哈希 + token/session + SECRET_KEY | 轴2 | 关端点、还原 config |
| 3 | 轴3 | get_current_user/require_admin + history/feedback/tasks 归属 | 轴1/2 | 去依赖还原公共路由 |
| 4 | 轴4 | 前端登录注册 + Pinia + 路由守卫 + axios 拦截器 | 轴1 | 还原前端 store/守卫 |
| 5 | 轴5 | Admin 操作台（require_admin + admin 页） | 轴1/3 | 移除 admin 端点/页 |
| 6 | 轴6 | 会话/记忆地基（conversations + checkpointer + Redis） | 轴2 | 关 checkpointer、还原无状态 |

## 核心决策速览

- 认证选型：**httpOnly Cookie + Redis 服务端 session**（SSE 兼容 + 可撤销）；第三方走 API Key 双轨。
- **当前栈** = Cookie+Session 搭配 SSE（认证见 ADR-010、实时通道见 ADR-011），两者可各自独立演进。
- user_id **单一归属**；device_id 降级为匿名凭据（匿名 user = role=guest），不破坏匿名/分享站。
- **会话/记忆 = 地基**，与用户系统同批做（修正原「上层构筑」标注）。
- 第一版**克制**：只做密码注册登录 + RBAC + 数据归属，不做找回密码/OAuth/邮箱验证/多租户。
- 认证**不引 Django**，只用轻量库（自写优先，ADR-008）。

## 风险与取舍

| 风险 | 已做取舍 |
|------|---------|
| 安全（key/token/爆破/越权） | HTTPS、密码哈希、SECRET_KEY 走 .env、登录限流、RBAC 二次校验 |
| scope creep（用户系统易膨胀） | 第一版严格克制，红线清单明确不做项 |
| 匿名 user 记录膨胀 | 未激活匿名 user 定期清理（TTL）；登录时升级/合并，防重复与冲突 |
| 会话/记忆比认证易踩坑 | 把它当独立地基认真做，不当认证附属 |
| schema 漂移（create_all 双轨） | 已收敛为 Alembic 单一来源（create_all 移除），alembic check 防漂移 |
| 依赖选择 | 只用轻量库（pwdlib/bcrypt + pyjwt），评估版本/依赖 |

## 交叉引用

- 关联 ADR：ADR-008（自写优先/轻量库，认证不引 Django）、ADR-009（LangGraph 编排，会话持久化复用 checkpointer）、ADR-010（认证通道选型）。
- 相关 design/ 文档：docs/design/architecture.md（中期会话记忆）、docs/design/memory.md（用户记忆参数形态）。
- 结构文档：docs/structure/backend.md（后端分层）、docs/structure/data.md（数据字典）。
- 来源：docs/inbox.md（想法5/12/15/21/27 主线与地基）。

## 修改记录

| 日期 | 变更 |
|------|------|
| 2026-08-27 | 收敛 user 身份单一来源（user_id 归属 + 匿名 user）；create_all 移除，schema 单一来源为 Alembic。
