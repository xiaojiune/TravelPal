# 项目总览

## 修改记录

| 日期 | 变更 |
|------|------|
| 2026-07-18 | 重写为交叉引用总览模式，补全 ADR 索引 |

## 技术栈总览

| 层 | 技术 | 说明 |
|----|------|------|
| 后端框架 | Python 3.12 + FastAPI | 异步 HTTP + SSE 流式 |
| 求解引擎 | CA（模拟退火）+ VNS+（变邻域搜索 + SA 混合 + 自适应算子） | 核心算法 |
| 前端框架 | Vue 3 + Vite + TypeScript | SPA 单页应用 |
| 地图 SDK | 高德 AMap JS API v2.0 | 2D 路线可视化 |
| 数据库 | PostgreSQL 16（pgvector） | 历史记录持久化 |
| 缓存 | Redis | 预留 |
| LLM | DeepSeek API（兼容 OpenAI SDK） | 营业时间解析 + Agent 对话 |
| 容器化 | Docker Compose（Nginx + uvicorn + Postgres + Redis） | 一键部署 |

## 顶层目录

```
TravelPal/
├── backend/        后端 FastAPI        → 详见 backend.md
├── frontend/       前端 Vue 3 + Vite   → 详见 frontend.md
├── docs/           项目文档体系        → 本目录（结构文档 + ADR + 编码规范）
├── data/           数据集
│   ├── DataSets/    TSPTW 测试集（n100w20, n60w60...）
│   └── spots/       景点 MD 仓库（待填充）
├── tests/          测试目录
├── docker-compose.yml    四服务编排（postgres/redis/backend/nginx）
├── Dockerfile.backend    后端容器镜像（Poetry export + pip）
├── Dockerfile.frontend   前端容器镜像（双阶段：Node build → Nginx serve）
├── deploy.sh             一键部署脚本
├── .env.example          环境变量模板
├── Makefile              开发命令（dev/serve/lint/build/test/docker）
└── pyproject.toml        Poetry 项目配置 + 依赖管理
```

## 系统级调用链路

```
用户操作
  │
  ├── POST /api/poi-lookup    →  高德 POI 搜索（LLM 解析营业时间）
  │
  ├── POST /api/suggest       →  ca_suggest()：6 种聚类 × 天数遍历
  │     └── 返回建议列表       →  用户选择天数 → 前端合成 PlanResult
  │
  ├── POST /api/plan          →  指定天数 → cluster_and_solve()
  │     └── 返回完整方案       →  前端 AMap 渲染 + SchedulePanel
  │
  └── POST /api/chat (SSE)    →  LLM Agent 流式对话
        └── 返回流式回复       →  聊天面板渲染
```

各环节的**完整数据流**和**关键数据结构**见以下文档：

| 链路环节 | 关键文档 |
|----------|---------|
| 端到端前端交互 | [`frontend.md`](./frontend.md#七数据流图) |
| Suggest/Plan 引擎分支 | [`backend.md`](./backend.md#九数据流图) |
| POI 查询 + LLM 解析流程 | [`backend.md`](./backend.md#七数据加载层) |
| 数据结构全貌 | [`data.md`](./data.md) |

## ADR 索引

| 文档 | 主题 | 状态 |
|------|------|------|
| [`ADR/001.md`](../ADR/001.md) | CA / VNS 平级并行架构 | ✅ 已采纳 |
| [`ADR/002.md`](../ADR/002.md) | 前端架构选型（Vue 3 + FastAPI 分离） | ✅ 已采纳 |
| [`ADR/003.md`](../ADR/003.md) | 可视化方案变更（Cesium 3D → AMap 2D） | ✅ 已采纳 |
| [`ADR/004.md`](../ADR/004.md) | 项目哲学——"旅行伴侣"而非"规划工具" | ✅ 已采纳 |
| [`ADR/005.md`](../ADR/005.md) | 营业时间 LLM 解析与 Agent 架构决策 | ✅ 已采纳 |
