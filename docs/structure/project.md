# 项目总览

## 修改记录

| 日期 | 变更 |
|------|------|
| 2026-07-18 | 重写为交叉引用总览模式，补全 ADR 索引 |
| 2026-07-22 | 降级为纯引用文档，去除与 README 重复的技术栈/目录 |

> 技术栈和目录结构见 [README.md](../../README.md#项目结构)。本页聚焦调用链路与文档索引。

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
