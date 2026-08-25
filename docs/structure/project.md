# 项目总览

## 修改记录

| 日期 | 变更 | 动机 |
|------|------|------|
| 2026-08-25 | 重写：更新异步任务链路与 ADR 索引，对齐 structure 模板 | 后端 suggest/plan 已改为异步任务（task_id 轮询），且 ADR 已重编号 |
| 2026-07-22 | 降级为纯引用文档，去除与 README 重复的技术栈/目录 | 避免与 README 双源维护 |
| 2026-07-18 | 重写为交叉引用总览模式 | 建立项目级导航 |

## 读者指南

| 列 | 内容 |
|----|------|
| 面向读者 | 所有开发者、新成员 |
| 阅读前置 | [README.md](../../README.md) |
| 阅读目标 | 快速了解项目全貌、系统级调用链路与各层文档入口 |

## 架构总览

TravelPal 是一个**基于双引擎 + LLM Agent 的智能旅行规划系统**，前后端分离：前端为 Vue 3 + TypeScript + Vite SPA，后端为 FastAPI。核心由四部分构成：

- **HTTPS 接口层**（`backend/api/`）：POI 查询、行程规划、Agent 对话、历史记录、异步任务、用户反馈等端点。
- **Agent 层**（`backend/agent/`）：LLM 对话编排（LangGraph）、规划能力（方案调整/评语）、工具包（TOOL_REGISTRY）。
- **求解引擎层**（`backend/engine/`）：CA / VNS 双求解器 + 6 种聚类 + 适应度评估。
- **数据与基础设施**（`backend/data/`、`backend/infrastructure/`、`backend/domain/`、`backend/tasks/`、`backend/observability/`）：高德数据、ORM、LLM/天气/检索实现、异步任务、指标。

技术栈和目录结构见 [README.md](../../README.md)。本页聚焦系统级调用链路与文档索引。

## 系统级调用链路

用户操作的端到端链路（注意 suggest / plan 现为**异步任务**，返回 `task_id` 后前端轮询 `/api/tasks/{id}`）：

```
用户操作
  │
  ├── POST /api/poi-lookup   → 高德 POI 搜索 + LLM 解析营业时间（同步）
  │
  ├── POST /api/suggest      → 提交建议任务（异步，返回 task_id）
  │     └── GET /api/tasks/{id}  轮询 → 返回 suggestions[]
  │
  ├── POST /api/plan         → 提交规划任务（异步，返回 task_id）
  │     └── GET /api/tasks/{id}  轮询 → 返回 PlanResult
  │
  ├── POST /api/chat (SSE)   → LLM Agent 流式对话（LangGraph 编排）
  │
  ├── POST /api/history      → 保存方案到分享站
  │      GET  /api/history       分页列表
  │      GET  /api/history/{id}  完整详情
  │      DELETE /api/history/{id} 删除（device_id 鉴权）
  │
  ├── POST /api/feedback     → 保存用户反馈（/about 页面问卷）
  │
  └── DELETE /api/tasks/{id} → 清理异步规划任务记录
```

各环节的完整数据流与关键数据结构见以下文档：

| 链路环节 | 关键文档 |
|----------|---------|
| 端到端前端交互 | [frontend.md](frontend.md) |
| 后端分层与接口 | [backend.md](backend.md) |
| POI 查询 + LLM 解析 | [backend.md](backend.md) |
| 数据结构全貌 | [data.md](data.md) |
| Agent 对话与工具 | [agent.md](agent.md) |

## 文档索引

`docs/` 按职责分层，入口唯一由 [index.rst](../index.rst) 导航：

| 目录 | 职责 |
|------|------|
| `structure/` | 代码结构与数据字典（backend/frontend/agent/data/project） |
| `design/` | 规划蓝图（架构演进 / UI-UX / 记忆），非决策记录 |
| `product/` | 使命→原则→计划（slogan / philosophy / roadmap） |
| `ADR/` | 决策记录（001-009，按 13 段模板） |
| `feedback/` | 用户反馈（AI 对话记录与外部建议） |
| `handoff/` | 会话交接文档（CURRENT_CODE / CURRENT_DOC） |

### 关联 ADR

- ADR-001：CA / VNS 平级并行架构（双引擎核心）。
- ADR-008：手写轻量架构 + 选择性引框架（LangChain 生态边界）。
- ADR-009：LLM 编排层选型（LangGraph 维持，PydanticAI 不引入）。

## 术语表

| 术语 | 定义 |
|------|------|
| CA | 压缩退火求解器（秒级快速预览） |
| VNS | 变邻域搜索求解器（可达理论最优，分钟级） |
| Task | 异步规划任务（plan_tasks 记录，pending/running/done/failed） |
| PlanResult | 完整规划结果（solution + daily_schedules + spots + polylines） |

## 维护契约

修改以下内容时必须同步：

- **新增/变更端点**：更新本页「系统级调用链路」及 [backend.md](backend.md) 的路由表。
- **数据模型**：更新 [data.md](data.md) 统一数据字典。
- **ADR**：新增决策在 [ADR/](../ADR/) 按模板记录，编号连续递增；本页「关联 ADR」随需补充。
- **文档入口**：导航唯一来源为 [index.rst](../index.rst)，新页面须加入其 toctree。