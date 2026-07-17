# 后端结构

## 修改记录

| 日期 | 变更 |
|------|------|
| 2026-07-18 | 从 back.md 重写为 backend.md：全量结构重写 + 引擎链路/POI流程/数据流图修正，清理 ca.py 废弃参数 |

## 一、架构总览

后端采用**三条路径并列**的架构：

```
用户请求
    │
    ├── POST /api/poi-lookup ──→ 高德 API → LLM 解析营业时间
    │
    ├── POST /api/suggest ────→ Engine (CA 全参数搜索)
    │    用户选天数
    │   POST /api/plan ───────→ Engine (CA 或 VNS+)
    │
    └── POST /api/chat ───────→ Agent (Function Calling)
```

核心原则：**Agent 是交互层，Engine 是计算层**。Agent 不参与路径计算，只做意图识别与参数提取。当前 Agent 通过 chat_tools.py 直接调用函数，后续 MCP 迁移后可统一接管 API 入口。

## 二、目录结构

```
backend/
├── config.py              环境变量（AMap Key、LLM Key、DATABASE_URL 等）
├── typedefs.py            内部 TypedDict 定义（零运行时开销）
│
├── api/                   HTTP 接口层
│   ├── server.py          FastAPI 工厂 + CORS + lifespan（DB 初始化/关闭）
│   ├── routes.py          8 个 API 端点
│   └── schemas.py         Pydantic 请求/响应模型
│
├── agent/                 LLM Agent 层
│   ├── chat_tools.py       工具函数（parse_biz_hours、build_chat_messages）
│   ├── planner.py         行程调整三指令（加/删景点、调天数）
│   └── commentator.py     方案评语生成
│
├── engine/                求解引擎核心
│   ├── pipeline.py        流程编排入口（run_planning）
│   ├── search.py          建议/深度求解（ca_suggest / cluster_and_solve）
│   ├── ca.py              压缩退火求解器
│   ├── vns.py             变邻域搜索求解器
│   ├── clustering.py      6 种聚类方法注册表
│   └── fitness.py         适应度计算（距离/等待/迟到/晚归惩罚）
│
├── data/                  数据层
│   ├── amap_loader.py     高德 API → 成本/距离矩阵（build_real_data）
│   ├── model/
│   │   ├── database.py    async SQLAlchemy 引擎 + 会话工厂
│   │   └── models.py      HistoryRecord ORM（详见 data.md）
│   ├── knowledge_base.py  知识库检索
│   └── chroma_db/         向量数据库（待填充）
│
└── tools/                 工具脚本
    ├── deprecated.py       @legacy_only 装饰器（标记遗留函数）
    ├── gen_openapi.py     导出 OpenAPI 规范 JSON
    └── sync_all.py        自动同步 __init__.py 的 __all__
```

## 三、配置层

### config.py

环境变量配置入口，支持 `.env` 文件注入。关键变量：

| 变量 | 默认值 | 用途 |
|------|--------|------|
| `AMAP_API_KEY` | `""` | 高德 Web 服务 API（路线/POI） |
| `AMAP_JS_KEY` | `""` | 高德 JS API（前端地图） |
| `LLM_API_KEY` | `""` | LLM 调用密钥 |
| `LLM_BASE_URL` | `https://api.deepseek.com/v1` | LLM API 地址 |
| `DATABASE_URL` | `postgresql+asyncpg://travelpal:travelpal123@localhost:5432/travelpal` | PostgreSQL 连接 |
| `DEV_RELOAD` | `false` | uvicorn 热重载开关 |

### typedefs.py

内部数据模型定义（TypedDict），零运行时开销，只在类型约束时使用。
API 边界用 Pydantic（`schemas.py`），内部数据传递用 TypedDict。

详见 [`docs/structure/data.md`](data.md) 统一数据字典。

## 四、HTTP 接口层 (api/)

### server.py

FastAPI 应用工厂：

- `init_db()` / `close_db()` — 生命周期中管理连接池
- CORS 允许 `localhost:5173` 和 `127.0.0.1:5173`（Vue 开发服务器）
- `DEV_RELOAD` 环境变量控制热重载

### routes.py — 8 个端点

| 方法 | 路径 | 用途 |
|------|------|------|
| `POST` | `/api/poi-lookup` | 批量查询 POI 坐标 + LLM 解析营业时间 |
| `POST` | `/api/suggest` | 获取方案建议列表（fast 模式） |
| `POST` | `/api/plan` | 执行完整规划（deep 模式） |
| `POST` | `/api/chat` | LLM Agent 对话（SSE 流式） |
| `GET` | `/api/history` | 历史记录列表（分页） |
| `GET` | `/api/history/{record_id}` | 历史记录详情 |
| `POST` | `/api/history` | 创建历史记录（分享方案） |
| `DELETE` | `/api/history/{record_id}` | 删除历史记录（device_id 鉴权） |

### schemas.py

Pydantic 请求/响应模型，按功能分组：

- **POI 查询**：`POILookupRequest` / `POILookupItem` / `POILookupResponse`
- **规划请求**：`PlanRequest`（含酒店/景点/算法参数）
- **Agent 对话**：`ChatRequest`
- **历史记录**：`HistoryCreate` / `HistorySummary` / `HistoryDetail` / `HistoryListResponse` / `HistoryDeleteRequest`

详见 [`docs/ADR/005.md`](../ADR/005.md) 营业时间 LLM 解析决策。

## 五、LLM Agent 层 (agent/)

### chat_tools.py

工具函数，Agent 通过 Function Calling 调用：

- `parse_biz_hours(amap_opentime2, spot_name)` → LLM 解析营业时间为 `(start_min, end_min)`
- `build_chat_messages(messages, plan_result)` → 构造对话上下文
- `chat_stream(messages)` → SSE 流式响应

### planner.py

三指令规划器：

- `add_spot` — 加景点（重算路径）
- `remove_spot` — 去景点（重算路径）
- `adjust_days` — 调天数（重分配行程）

当前通过 Function Calling 调用。详见 [`docs/ADR/001.md`](../ADR/001.md#67) 引擎架构决策。

### commentator.py

方案评语生成器：

- `generate_commentary(plan_result)` → 自然语言评语（规则模板 + LLM 润色混合）

详见 [`docs/产品路线图.md`](../产品路线图.md) 第一阶段 Commentator。

## 六、求解引擎层 (engine/)

引擎核心，使用独立求解器 + 聚类方法的组合策略。

### 模块职责

| 模块 | 关键函数 | 定位 |
|------|---------|------|
| `pipeline.py` | `run_planning()` | 流程编排：矩阵构建 → 求解 → 行程生成 → 评语 |
| `search.py` | `ca_suggest()` / `cluster_and_solve()` | 建议/求解入口 |
| `ca.py` | `CASolver.solve()` | 快速求解器（压缩退火） |
| `vns.py` | `VNSSolver.solve()` | VNS+ 增强求解器（SA 混合接受 + 自适应算子权重 + 精英池后优化） |
| `clustering.py` | `call_cluster()` | 6 种聚类方法注册表 |
| `fitness.py` | `analyze_solution()` | 成本计算 + 可行性判定 |

### 聚类方法注册表

6 种方法（`clustering.py`）：

1. 基于距离的 K-means 聚类
2. 基于时间窗的聚类
3. 基于时空特征的聚类
4. 基于时间窗重叠的启发式分组
5. 基于时间窗密度的聚类
6. 混合分组方法

详见 [`docs/ADR/001.md`](../ADR/001.md) 引擎并行架构决策。

### 引擎内部调用链路

`cluster_and_solve` 是 `run_planning` 中的核心调度入口，根据外部参数分支：

```
cluster_and_solve(spots, cost_mat, mode, n_days)
│
├─ n_days=None (Suggest 阶段) ────────────────
│   └─ ca_suggest()
│       ├─ 外层：遍历 6 种聚类方法
│       ├─ 内层：天数递增（min_days → n_spots）
│       ├─ solve_groups(solver_type="CA") 求解各组
│       ├─ 增益阈值早退（<1.0% × 3 次 → stop）
│       ├─ 去重 + 按成本排序
│       └─ 返回 type="suggestion"（多条方案，每条含完整 routes/daily_schedules/cost）
│
└─ n_days 已指定 (Plan 阶段) ─────────────────
    ├─ solver_type = "VNS"（固定，仅 deep 模式）
    ├─ 遍历 6 种聚类方法，固定天数分组
    ├─ solve_groups(solver_type="VNS")
    └─ 返回 type="solution"（单条最优方案）
```

> `run_planning` 设计要点：
> - suggest 和 plan 共用数据准备与后处理
> - 共享范围：成本矩阵构建 → spots 时间窗收缩 → polyline 补调
> - 分叉点仅在 `cluster_and_solve` 内部
> - 拆为两个入口函数收益不高，当前保持统一

## 七、数据层 (data/)

### amap_loader.py

- `get_poi_details(city, spot_names)` → 高德 POI 批量查询
- `build_real_data(poi_cache)` → 构造成本矩阵、距离矩阵、真实轨迹 polylines

### model/（数据库 ORM）

- `database.py` — async SQLAlchemy 引擎连接池 + `get_session` 依赖注入
- `models.py` — `HistoryRecord` ORM 模型（id / device_id / note / city / hotel / n_days / cost / spot_count / plan_result / request_params / created_at）

详见 [`docs/structure/data.md`](data.md) 数据定义。

### knowledge_base.py / chroma_db/

知识库检索接口与向量数据库（预留，当前主要依赖 LLM 实时解析）。

## 八、工具层 (tools/)

| 脚本 | 用途 |
|------|------|
| `deprecated.py` | `@legacy_only` 装饰器，标记仅作遗留参考的函数 |
| `gen_openapi.py` | 导出 `openapi.json`（供 openapi-typescript 生成前端类型） |
| `sync_all.py` | 扫描 `__init__.py` 的 import 语句，自动同步 `__all__` |

## 九、数据流图

### POI 查找 → LLM 营业时间解析

```
前端传入 city + names[]（景点名称列表）
       ↓
POST /api/poi-lookup
       ↓
逐个调用 get_poi_details(name, city)
  ├── 高德 API 三策略搜索
  │   ① types=风景名胜 + city_limit（高德分类准确）
  │   ② 去掉 types 按关键词排序（如岭南印象园→中山纪念堂误配补救）
  │   ③ 全国搜索 + 跨城市判定（确认不在本市 → 返回提示）
  │
  ├── 成功 → (lon, lat, opentime2, address, ...)
  │     ↓
  │   parse_biz_hours(opentime2) → LLM 解析营业时间
  │     ├── 成功 → (start_min, end_min)
  │     └── 失败 → None（tw_start/tw_end 均置 None）
  │     ↓
  │   加入 items[] → POILookupItem
  │
  └── 失败 → 加入 failed[]（返回错误信息字符串）
       ↓
返回 { items: POILookupItem[], failed: string[] }
```

详见 [`docs/ADR/005.md`](../ADR/005.md) 营业时间 LLM 解析与 Agent 架构决策。

### 端到端业务流程（从前端视角）

整个规划业务分**4 个阶段**，前后端配合完成：

```
Stage 1 — POI 查找
  目的：获取景点坐标 + 营业时间
  前端 → POST /api/poi-lookup（传入 city + names[]）
  后端 → 高德 API 三策略搜索 → LLM 解析 opentime2
  返回 → POILookupItem[]（含坐标/地址/时间窗）
  前端 → 展示结果，用户确认

Stage 2 — Suggest（CA 固定）
  目的：让用户看到所有可能的行程方案
  前端 → POST /api/suggest（传入酒店 + 已确认景点 + 参数）
  后端 → run_planning(mode="fast", n_days=None)
          └── ca_suggest()
                ├── 遍历 6 种聚类 × 天数递增
                ├── CASolver.solve() 求解各组
                └── 返回 type="suggestion"（多条方案 + 矩阵）
  返回 → { suggestions[], cost_matrix, dist_matrix, polylines }
          每条建议已含完整 routes / daily_schedules / cost
  前端 → 展示方案卡片，用户可点击预览

  ┌── fast 路径（不调后端）──────────────────────────────┐
  │ 用户点击卡片 → frontend/buildPlanResultFromSuggestion │
  │ → store.planResult → router.push("/plan")            │
  └──────────────────────────────────────────────────────┘

Stage 3 — Plan（VNS 仅限 deep 模式）
  目的：对选定天数做深度优化
  前置：用户在 Suggest 页选好天数，点击"深度规划"
  前端 → POST /api/plan（mode="deep", n_days=用户选定）
  后端 → run_planning(mode="deep", n_days=指定)
          └── cluster_and_solve()
                ├── 遍历 6 种聚类，固定天数
                ├── solve_groups(solver_type="VNS")   # 分钟级
                └── 返回 type="solution"
  返回 → PlanResult（含 best_days/daily_schedules/commentary）
  前端 → 用户点击深度结果卡片
         → store.planResult = data → router.push("/plan")

Stage 4 — 结果展示
  PlanPage 读取 store.planResult
  纯展示，不调用任何后端 API
  组件: metrics-bar + commentary + AmapMap + SchedulePanel
```
