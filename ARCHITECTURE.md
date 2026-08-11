# TravelPal 架构总览

系统总入口文档：C4 架构图（Context / Container），先看这里建立整体认知。

## 修改记录

| 日期 | 变更 | 动机 |
|------|------|------|
| 2026-08-06 | 初始创建 | 补充项目总入口，内嵌 C4 Context/Container 图，串联 ADR 决策速览与文档导航 |
| 2026-08-11 | 精简为纯 C4 图 | 架构图是「被引对象」：删除系统定位/决策速览/文档导航等文字，避免与 docs 各包重复维护；文档导航职责移交 docs/index.rst |

## 一、C4 Context 图（系统与外部交互）

```mermaid
flowchart LR
  User["👤 旅行者<br/>浏览器访问 trippal.site"]
  Assistant["🤖 外部 AI 助手<br/>（MCP Client）"]
  Amap["🗺️ 高德地图 API<br/>POI 搜索 / 驾车路径"]
  LLM["🧠 DeepSeek LLM<br/>对话 / 营业时间解析"]

  subgraph TP["TravelPal 系统"]
    Web["🖥️ 前端 SPA + Nginx"]
    MCP["🔌 MCP Server（stdio）"]
  end

  User <-->|HTTPS /api| Web
  Assistant <-->|MCP 协议| MCP
  Web -.->|对话/规划请求| LLM
  Web <-->|POI/路径查询| Amap
  MCP -.->|工具执行| LLM
  MCP <-->|工具执行| Amap
```

## 二、C4 Container 图（系统内部组件）

```mermaid
flowchart TB
  subgraph Client["前端（deploy 于 Nginx 容器）"]
    SPA["🖥️ Vue3 SPA<br/>HomePage / SuggestPage / PlanPage / HistoryPage"]
    AgentPanel["🤖 Agent 面板<br/>ChatStream + ToolRail / ToolPanel"]
  end

  subgraph Server["后端（FastAPI 容器）"]
    API["⚡ api/ <br/>HTTP 路由 + SSE"]
    ORCH["🤝 agent/chat/orchestrator<br/>LangGraph 单 Agent 编排"]
    TOOLS["🧰 agent/tools/<br/>TOOL_REGISTRY"]
    ENGINE["🧮 engine/<br/>CA / VNS 双引擎 + 6 聚类"]
    MCP["🔌 mcp/ <br/>MCP Server"]
    OBS["📊 observability/<br/>Prometheus 指标"]
  end

  subgraph Worker["Celery Worker（tasks/ 容器）"]
    TASK["⚙️ tasks/<br/>submit_task → executors"]
  end

  subgraph Infra["基础设施"]
    PG[("🗄️ PostgreSQL<br/>history_records / plan_tasks / feedback_records")]
    Redis[("📮 Redis<br/>Celery broker + 驾车缓存")]
  end

  SPA <-->|HTTP/SSE| API
  AgentPanel <-->|SSE 事件流| API
  API --> ORCH
  ORCH --> TOOLS
  API --> MCP
  TOOLS -.-> ENGINE
  API -->|提交任务| TASK
  TASK --> ENGINE
  TASK <--> PG
  TASK <--> Redis
  API <--> PG
  OBS -.->|/api/metrics| API
```
