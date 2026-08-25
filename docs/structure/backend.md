# 后端架构详解

## 修改记录

| 日期 | 变更 | 动机 |
|------|------|------|
| 2026-08-25 | 重写：新增 domain/infrastructure/mcp/tasks/observability 层，suggest/plan 改异步任务，对齐 structure 模板 | 后端已扩展为分层架构，旧文档仅描述 api/agent/engine/data/utils 五层，严重缺失 |
| 2026-07-21 | deprecated.py → decorators.py；调度拆出 `_solve_best`；引擎链路补 VNS 报错分支；工具表同步 `@placeholder` | 代码演进同步 |
| 2026-07-18 | 从 back.md 重写为 backend.md：全量结构重写 + 引擎链路/POI流程/数据流图修正 | 建立后端独立文档 |

## 读者指南

| 列 | 内容 |
|----|------|
| 面向读者 | 后端开发者 |
| 阅读前置 | [project.md](project.md)、[data.md](data.md) |
| 阅读目标 | 读懂后端分层、接口、引擎求解与异步任务编排 |

## 架构总览

后端采用**分层 + 异步任务**架构。FastAPI 提供 HTTP 接口；`suggest` / `plan` 为**异步任务**（写入 `plan_tasks`，Celery 消费，前端轮询 `/api/tasks/{id}`），`poi-lookup` / `chat` 保持同步/SSE。核心原则：**Agent 是交互层，Engine 是计算层**——Agent 只做意图识别与工具分发，不参与路径求解。

```
HTTP 路由层 (api/)  ── 同步: poi-lookup / chat(SSE) ──┐
       │                                            │
       ├─ 异步: suggest / plan → tasks/(submit) → Celery → worker → engine
       │                                            │
       └─ history / feedback → data/model (ORM) ─────┘

domain/ 定义防腐层接口（LLM / Weather），infrastructure/ 提供可插拔实现
observability/ 聚合 Prometheus 指标，mcp/ 把叶子工具暴露给外部 AI 助手
```

## 目录结构

```
backend/
├── config.py            环境变量配置（Settings，.env 注入）
├── typedefs.py          内部 TypedDict（SpotDict/RouteResult/PlanResult/...）
│
├── api/                 HTTP 接口层
│   ├── server.py        FastAPI 工厂 + lifespan + MetricsMiddleware + /api/metrics
│   ├── routes.py        端点：poi-lookup/suggest/plan/chat/history/feedback/tasks
│   └── schemas.py       Pydantic 请求/响应模型（OpenAPI 驱动）
│
├── agent/               LLM Agent 层（详见 agent.md）
│   ├── chat/            LangGraph 编排（chat.py + orchestrator.py）
│   ├── planning/        规划能力（_core.py + commentator.py + ops/）
│   ├── prompts.py       LLM prompt 集中管理
│   └── tools/           工具包（TOOL_REGISTRY + poi/plan/driving 子包）
│
├── engine/              求解引擎核心
│   ├── pipeline.py      流程编排（run_planning / _rebuild_schedule / adjust_plan）
│   ├── search.py        双模式分发（ca_suggest / cluster_and_solve / _solve_best）
│   ├── ca.py            CASolver（压缩退火）
│   ├── vns.py           VNSSolver（变邻域搜索）
│   ├── clustering.py    6 种聚类方法注册表
│   └── fitness.py       适应度计算（_cal_fitness_numba / analyze_solution）
│
├── data/                数据层
│   ├── amap_loader.py   高德 API：POI 搜索/营业时间解析/驾车路径/成本矩阵
│   ├── driving_cache.py 驾车路径缓存（点对基元 + 整矩阵快照，Redis/内存）
│   └── model/           SQLAlchemy ORM（HistoryRecord / PlanTask / FeedbackRecord）
│
├── domain/              领域层（防腐层接口定义）
│   ├── llm_service.py   LLMService 协议（ToolCallResult/LLMResult）
│   └── weather_service.py WeatherService 协议（WeatherInfo）
│
├── infrastructure/     基础设施层（可插拔领域实现）
│   ├── llm/             LLM 实现（factory + openai_impl + dspy_optimizer 占位）
│   ├── weather/         天气实现（factory + http + mcp）
│   └── retrieval/       BM25 引擎 + Hybrid/LlamaIndex 占位
│
├── mcp/                 MCP 服务器：遍历 TOOL_REGISTRY 暴露叶子工具
│   └── server.py        FastMCP 兼容层（build_server / _run_stdio / main）
│
├── tasks/               异步任务包（Celery）
│   ├── app.py           Celery 应用 + 队列配置
│   ├── submit.py        提交侧：创建 plan_tasks 记录并投递队列
│   ├── worker.py        消费侧：run_plan_task + 状态流转
│   └── executors.py     执行体：_run_suggest / _run_plan / _run_adjust
│
├── observability/       观测性层（Prometheus 指标定义与多进程聚合）
│   └── metrics.py       metrics_response
│
└── utils/               通用工具
    ├── decorators.py    @legacy_only / @placeholder / @refactor
    ├── gen_openapi.py   导出 OpenAPI 规范 JSON
    └── sync_all.py      自动同步 __init__.py 的 __all__
```

## 数据流

### POI 查找 → LLM 营业时间解析（同步）

`POST /api/poi-lookup` → 逐个调用高德 POI 搜索（三策略：分类+城市限定 / 去类型关键词 / 全国跨城判定）→ 成功取坐标与 opentime2 → `parse_biz_hours`（LLM 解析，失败置 None）→ 返回 `{ items, failed }`。

### 行程规划（异步任务）

`POST /api/suggest` 或 `/api/plan` → `submit_task` 创建 plan_tasks 记录 + 投递 Celery → worker 消费 → `executors._run_suggest/_run_plan` → `engine`（建议走 `ca_suggest`，规划走 `cluster_and_solve`）→ 更新任务状态为 done，前端轮询 `/api/tasks/{id}` 取 `result`。

### Agent 对话（SSE）

`POST /api/chat` → `chat.py` 组装消息（CHAT_SYSTEM + 规划上下文 + 表单上下文）→ `orchestrator.stream_orchestrator`（LangGraph 循环）→ SSE 事件流（tool_status/tool_result/content/error/done）。详细见 [agent.md](agent.md)。

### 历史记录与反馈

`POST /api/history` 保存方案到分享站；`GET /api/history` 分页；`GET /api/history/{id}` 详情；`DELETE /api/history/{id}` 需 device_id 匹配。`POST /api/feedback` 保存 /about 问卷反馈。

## 术语表

| 术语 | 定义 |
|------|------|
| plan_tasks | 异步规划任务表（status: pending/running/done/failed） |
| TaskResult | suggest/plan 完成响应（SuggestResult 或 PlanResult） |
| LLMService | LLM 防腐层接口，infrastructure/llm 提供实现 |
| CA | 压缩退火求解器 |
| VNS | 变邻域搜索求解器 |

## 维护契约

修改以下内容时必须同步：

- **新增/变更端点**：更新 `routes.py`、`schemas.py` 及本页「数据流」、[data.md](data.md) 数据字典。
- **改引擎**：`engine/` 与 `agent/planning/`（被 pipeline.adjust_plan 消费）需同改，并更新 [agent.md](agent.md)。
- **改数据模型**：同步 `data/model/models.py` 与 [data.md](data.md)。
- **改工具**：注册到 `TOOL_REGISTRY` + 更新 [tools.md](tools.md) 与 [agent.md](agent.md)。
- **改接口契约**：`schemas.py` 改动需跑 `make gen-api`（生成前端 openapi 类型）。