# 项目总览

## 顶层目录

```
TravelPal/
├── backend/                    # 后端 FastAPI
│   ├── agent/                  LLM Agent（planner / commentator / tools）
│   ├── api/                    HTTP 路由（routes / schemas / server）
│   ├── engine/                 求解核心（CA / VNS / clustering / fitness / search / pipeline）
│   └── data/                   数据加载（amap_loader / knowledge_base / chroma_db）
│
├── frontend/                   # 前端 Vue 3 + Vite
│   └── src/
│       ├── pages/              页面级组件（Home / Suggest / Plan）
│       ├── components/         可复用组件（AmapMap / SchedulePanel）
│       ├── router/             路由（/index.js）
│       ├── services/           API 封装（api.js）
│       └── stores/             Pinia 状态管理（plan.js）
│
├── data/                       # 数据集
│   ├── DataSets/               TSPTW 测试集（n100w20, n60w60...）
│   └── spots/                  景点 MD 仓库（待填充）
│
├── docs/                       # 决策日志 + 结构文档
│   ├── adr/                    架构决策记录（001 / 002 / 003）
│   └── structure/              当前结构描述（project / back / frontend / data）
│
└── docs++/                     # 外部知识库（架构设计 / 技术栈 / 旧项目参考等）
```

## 系统级调用链路

```
用户操作
  │
  ├── POST /api/poi-lookup      →  高德 POI 搜索
  │
  ├── POST /api/suggest         →  ca_suggest()
  │     └── 返回建议列表         →  用户选择天数
  │
  ├── POST /api/plan            →  cluster_and_solve()
  │     └── 返回完整方案         →  前端 AMap 渲染 + 行程面板
  │
  └── POST /api/chat (SSE)      →  LLM Agent 流式对话
        └── 返回流式回复         →  聊天面板渲染
```

## ADR 索引

| 文档 | 主题 | 状态 |
|------|------|------|
| `adr/001.md` | CA / VNS 平级并行架构 | ✅ 已采纳 |
| `adr/002.md` | 前端架构选型（Vue 3 + FastAPI 分离） | ✅ 已采纳 |
| `adr/003.md` | 可视化方案变更（Cesium 3D → AMap 2D） | ✅ 已采纳 |
