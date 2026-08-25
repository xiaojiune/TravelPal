# 架构演进路线图（规划蓝图）

## 元信息

| 项 | 值 |
|----|----|
| 作者 | xiaojiune |
| 最后更新 | 2026-08-25 |
| 状态 | 进行中 |

## 执行摘要

本文件是**规划蓝图**，不是决策记录。它界定"项目往哪走"：哪些框架引入、哪些不引入、引入顺序与演进路径，避免盲目堆砌框架。具体"为什么这么选"见关联 ADR。

## 背景

项目已进入稳定期，核心 CA / VNS 引擎与全栈链路稳定。为应对后续功能扩展（多 Agent、异步任务、外部服务集成），需要一份架构演进路线图，明确引入边界与顺序。

## 总体目标

- **多 Agent 预留**：按多 Agent 设计、按单 Agent 执行（Router-Executor 中央编排）。
- **异步任务**：把分钟级路径计算异步化（Celery + 任务表 + 前端轮询）。
- **外部集成**：MCP 接入（Server 角色先行，Client 角色后置）。
- **观测性**：业务指标 + 指标端点（轻度接入，不部署 Grafana）。

## 分阶段路线图

| 阶段 | 目标 | 关键交付 | 状态 |
|------|------|---------|------|
| 近期 | 编排层落地 | category 工具裁剪 / schema 单一来源 / 编排契约测试 | 已实现 |
| 中期 | 会话与流控 | 会话记忆 / 人工确认（interrupt）/ 超长会话流控 | 待接入 |
| 远期 | 多 Agent | LangGraph 子图 / Supervisor / Hierarchical teams | 规划 |

## 各轴详细设计

### 轴 1：domain/LLMService 防腐层

**目标**：LLM 调用的唯一入口，用 Protocol（async stream / complete）+ factory 切换实现，不依赖 langchain 主包。

**实现状态**：已落地（手写实现，DeepSeek 走 OpenAI 兼容 SDK）。

**依赖**：无。

### 轴 2：Alembic 数据库迁移

**目标**：schema 增长前低成本接入（单表时铺路），用 async 模板 + 模型元数据对齐。

**实现状态**：已落地（迁移链与 ORM 模型对齐，CI 用 alembic check 校验漂移）。

**依赖**：无。

### 轴 3：MCP Server

**目标**：把现有工具暴露给 LLM，复用工具注册表、stdio 传输，支持工具发现。

**实现状态**：已落地（Server 角色）。需注意：Server 暴露给外部后要鉴权。

**依赖**：工具层（轴 1 防腐层无关，复用工具注册表）。

### 轴 4：异步任务表

**目标**：plan_tasks 表 + Celery worker + 前端轮询；结果由任务内自写表，不配 Celery result backend。

**实现状态**：已落地（suggest / plan 提交任务返回 task_id，前端轮询任务状态）。

**依赖**：轴 2。前提是单 uvicorn worker；多 worker 时需水平扩容 celery worker，前端接口不变。

### 轴 5：观测性

**目标**：业务指标（LLM 调用 / token / API 耗时）+ 指标端点，多进程聚合。

**实现状态**：已落地（prometheus_client 多进程，指标端点 Basic Auth 兜底）。

**依赖**：无。

### 轴 6：MCP Client

**目标**：连接外部 MCP 服务（天气 / 酒店 / 交通）。降级策略：HTTP 基线、MCP 按需、配置级降级。

**实现状态**：接口规范已落地（WeatherService 防腐层 + factory），HTTP / MCP 实现 TODO。

**依赖**：轴 3。

### 轴 7：DSPy / LlamaIndex

**目标**：按需组件化（占位已建：dspy_optimizer / llama_index_retriever / hybrid_retriever）；CrewAI 舍去。

**实现状态**：占位文件已建；多 Agent 扩展直接用 LangGraph 多图编排。

**依赖**：轴 1。

### 演进式架构：单 Agent 中央编排

**决策**：当前及可预见阶段采用**单 Agent 中央编排**（Router-Executor Pattern），不引入多 Agent。一个 LLM 大脑（Router）经 Function Calling / MCP 选择并调用执行器（Executor），代码只做"检测 tool_call → 分发执行"。

**演进策略**：按多 Agent 设计、按单 Agent 执行——每个"活 Agent"是独立职责边界 + 独立入口，共享同一套 LLMService 与工具注册表；不提前引入主管 Agent、Agent 通信协议、LangGraph 状态机。

**多 Agent 演进路径**：从单 Agent 扩到多 Agent 时，在 LangGraph 内用子图 / 多图组合完成（Supervisor / Hierarchical teams），LangGraph 原生支持，无需引入 CrewAI。

**工具分组（category）**：工具数量少时即确定分类维度，落地为平行映射（工具注册表保持纯注册表、分类独立维护、消费者零侵入）。

## 组件状态跟踪

| 状态 | 组件 | 说明 | 验证 |
|------|------|------|------|
| ✅ | domain/LLMService 防腐层 | Protocol + factory 切换实现 | `backend/domain/llm_service.py` + `backend/infrastructure/llm/` |
| ✅ | Alembic 数据库迁移 | 迁移链与 ORM 对齐，CI alembic check | `alembic/versions/` + `alembic/env.py` |
| ✅ | MCP Server 角色 | 遍历工具注册表注册叶子工具，stdio 传输 | `backend/mcp/server.py` |
| ✅ | WeatherService 防腐层 | Protocol + HTTP/MCP 可插拔（HTTP 基线） | `backend/infrastructure/weather/` |
| ✅ | 异步任务表 | plan_tasks + Celery worker + 前端轮询 | `backend/tasks/` + `backend/data/model/models.py` |
| ✅ | 观测性埋点 | 业务指标 + /api/metrics 多进程聚合 | `backend/observability/metrics.py` |
| ✅ | 演进式架构（单 Agent） | Router-Executor 条件边自环 | `backend/agent/chat/orchestrator.py` |
| 🚧 | DSPy / LlamaIndex | 占位文件已建，未实现 | `backend/infrastructure/` |
| 🚧 | MCP Client 角色 | 接口规范落地、实现 TODO（HTTP 基线、配置级降级） | `backend/infrastructure/weather/` |
| ⏸️ | 会话记忆（中期） | LangGraph checkpointer + 持久化 | 待接入 |
| ⏸️ | 人工确认 interrupt（中期） | 重工具调用前插入人工确认节点 | 待接入 |
| ⏸️ | 超长会话流控（中期） | 上下文接近上限时压缩/截断 | 待接入 |
| ⏸️ | 多 Agent（远期） | LangGraph 子图 / Supervisor / Hierarchical teams | 规划 |
| ❗ | 观测性 /metrics 访问控制 | `/api/metrics` 需限制访问（Basic Auth / 仅内网） | `backend/api/server.py` |
| ❌ | LangChain 接入 | 明确不引入（防腐层内替换未做） | 未安装 |
| ❌ | CrewAI | 明确舍去，多 Agent 用 LangGraph 多图 | 未引入 |

## 落地顺序

| 顺序 | 轴 | 内容 | 依赖 | 回滚方式 |
|------|-----|------|------|---------|
| 1 | LLMService 防腐层 | Protocol + factory，不依赖新框架 | 无 | 还原依赖、删防腐层 |
| 2 | Alembic 数据库迁移 | 单表时低成本接入，铺路 plan_tasks | 无 | alembic downgrade 回退 |
| 3 | MCP Server | 暴露现有工具给 LLM | 轴 1 | 关闭鉴权入口、删除暴露层 |
| 4 | 异步任务表 | plan_tasks + 轮询 | 轴 2 | 还原同步执行（已完成） |
| 5 | 观测性埋点 | 业务指标 + 指标端点 | 无 | 删端点、移除埋点 |
| 6 | MCP Client | 接入真实外部 MCP | 轴 3 | 切回 HTTP 实现，接口不变 |
| 7 | DSPy / LlamaIndex | 按需组件化（占位已建）；CrewAI 舍去 | 轴 1 | 防腐层内切回原实现 |

## 核心决策速览

- **MCP**：接入，Server 先行（复用工具注册表），Client 后置（有真实可用服务才接；只有 HTTP 就直接 httpx）。
- **Alembic**：单表时低成本接入，铺路 plan_tasks。
- **LangChain**：引入但用防腐层包住；第一轴只做 LLMService 防腐层；不引 Django。
- **Celery**：先任务表后平滑迁移（plan_tasks 自写），多 worker 水平扩容、前端接口不变。
- **观测性**：轻度（业务指标），不部署 Grafana，指标端点限访问。
- **组件化**：只引框架特定功能，防腐层 + 依赖倒置；多 Agent 不引 CrewAI。
- **换框架纪律**：先写单测锁定行为，再替换实现，一次只动一个轴。
- **演进式架构**：单 Agent 中央编排；多 Agent 演进用 LangGraph 子图 / 多图。

## 风险与取舍

| 风险 | 已做取舍 |
|------|---------|
| 每引一个框架多一层防腐翻译成本 | 按需渐进、一次一轴、占位优于提前引 |
| MCP Server 暴露给外部 | 需鉴权；本地 stdio 进程边界即鉴权，远程部署配 API Key |
| 多 worker 进程内任务状态无法共享 | 水平扩容 celery worker，前端轮询接口不变 |
| 指标端点公网泄露调用数据 | Nginx 前置 + Basic Auth / 仅内网 |

## 交叉引用

### 关联 ADR

- ADR-001：CA / VNS 平级并行（引擎层）。
- ADR-005：营业时间 LLM 解析与 Agent 架构决策（MCP 迁移预留）。
- ADR-006：MCP 协议迁移预留。
- ADR-007：BM25 RAG 知识检索（Deprecated）。
- ADR-009：Naive UI 分步引入（Agent-driven UI 承接方）。
- ADR-012：手写轻量架构 + 选择性引框架（换框架边界判断）。
- ADR-014：LLM 编排层选型（LangGraph 维持，PydanticAI 不引入）。

### 相关文档

- 结构详解（后端 / Agent）：`docs/structure/backend.md`、`docs/structure/agent.md`。

## 修改记录

| 日期 | 变更 |
|------|------|
| 2026-08-25 | 重大翻修：由 ADR-008 转为 design 规划蓝图，去 ADR 编号，结构调整为蓝图版。 |

## 历史版本归档（2026-08-25 前）

| 日期 | 变更 |
|------|------|
| 2026-08-01 | 初始创建（架构演进路线图）；并入 Alembic、WeatherService 防腐层；修正章节编号乱序，补 MCP Server 鉴权、Celery 单 worker 前提、/metrics 访问控制、回滚方式列 |
| 2026-08-01 | §1 MCP 补充部署形态（独立服务 + 原生懒加载）、职责边界（只复用叶子工具，不引用编排层）、Skill 触发引导说明 |
| 2026-08-03 | 新增 §9 演进式架构——单 Agent 中央编排（Router-Executor），按多 Agent 设计、按单 Agent 执行 |
| 2026-08-03 | 轴 6 MCP Client 落地降级策略：HTTP 基线、MCP 按需、配置级降级；WeatherService 防腐层接口规范已实现 |
| 2026-08-04 | 轴 4 异步任务表落地：Celery + plan_tasks 表，提交任务返回 task_id，前端轮询；docker-compose 新增 worker，Makefile 新增 make celery |
| 2026-08-04 | 轴 7 修订：DSPy / LlamaIndex 生成占位，CrewAI 舍去——多 Agent 用 LangGraph 多图编排 |
| 2026-08-06 | §9 融合编排层演进方向（近/中/远期）；category 落地为平行映射方案 B，近期三项实现 |
| 2026-08-07 | category 值 "planning" 统一为 "plan" |
| 2026-08-08 | search_rag 工具移除（RAG 工具壳删除，BM25 引擎保留） |