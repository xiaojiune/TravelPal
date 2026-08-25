# 后端分层决策（做法）

> 一行深引用，本文件供 SKILL.md 按需加载。目录职责与选层判断，不涉代码风格。

## 各层职责与依赖方向

```
api ──→ domain / agent / tasks / data     （只做 HTTP 接入）
domain ──→ engine / infrastructure / data  （业务用例，不碰 HTTP）
infrastructure ──→ (外部实现)              （模型/天气/检索，可替换，接口由 domain 定）
engine ──→ (纯算法，零 IO)                 （VNS/CA，项目核心智力，独立可测）
data ──→ (DB 模型 + 外部 API + 缓存)       （唯一碰 IO 的数据层）任务）
tasks ──→ (Celery)                        （调用 engine/domain 做异步重活）
observability / mcp / utils                （旁路出口 / 通用工具）
```

**核心规则**：依赖方向单一。domain 零依赖纯接口 → infrastructure 只依赖 domain → api 只做接入。换框架的爆炸半径因此很小（ADR-008/010）。

## 各层职责

| 层 | 职责 | 典型 |
|---|---|---|
| `api/` | HTTP 接入、请求/响应 schema、生命周期 | server.py、routes.py、schemas.py |
| `domain/` | 业务用例编排 + 防腐层接口 | llm_service.py、weather_service.py |
| `agent/` | LLM 对话/工具/规划 | chat/orchestrator.py、tools/、planning/ |
| `infrastructure/` | 外部适配实现（可替换） | llm/factory.py、weather/factory.py、retrieval/ |
| `engine/` | 纯算法（VNS/CA/聚类，零 IO） | vns.py、ca.py、clustering.py |
| `data/` | 数据访问：外部 API/DB/缓存/模型 | amap_loader.py、model/models.py、driving_cache.py |
| `tasks/` | Celery 异步任务 | submit.py、executors.py、worker.py |
| `observability/` | Prometheus 指标 | metrics.py |
| `mcp/` | MCP 服务器（复用叶子工具，不引用编排层） | server.py |
| `config.py` / `typedefs.py` | 配置 / 全局类型（单一来源） | — |
| `utils/` | 跨层通用工具（纯函数，无状态） | decorators.py |

> 补充：`data/model/` 是 SQLAlchemy 模型 + 连接池；`data/amap_loader.py` 是外部 API 加载。

## 选层判断（功能类型 → 建议层）

| 功能类型 | 建议层 | 反例（放错） |
|---|---|---|
| 纯算法 / 计算 | `engine/` | 放 `api/` 或 `domain/` |
| 外部 IO（API/DB/缓存） | `data/` 或 `infrastructure/` | `engine/`（纯算法不该有 IO） |
| 业务用例编排 | `domain/` | `api/`（路由里写业务） |
| LLM 对话 / 工具 | `agent/` | `api/` |
| HTTP 接入 | `api/` | `domain/`（不碰 HTTP） |
| 异步任务 | `tasks/` | `api/`（同步阻塞） |
| 全局配置 / 类型 | `config.py` / `typedefs.py` | 散落各层 |
| 跨层通用纯函数 | `utils/` | 在各层复制 |

## 放错层的信号

- 路由里出现业务计算 / 直接查表 → 下沉到 `domain/` 或 `data/`。
- `engine/` 里出现 DB / HTTP / redis 调用 → 纯算法层不该有 IO。
- 同一段逻辑在多个层之间复制 → 提公共模块（Rule of Three，见 SKILL.md 原则七）。
- 一个模块同时做"建表 + 发任务 + 执行引擎" → 职责过重，是未来重构的痛点起点（ADR-010 #6）。
- 防腐层只有两个接口（LLM/Weather）却想保护"换编排/换存储" → 战术防腐而非战略领域层，别硬扩（ADR-010 #5）。

## 案例：引入"用户系统"

先探索：现在无 auth，`api/` 已有 history/feedback 用设备序号。
判断：用户鉴权属业务用例 → `domain/` 建 auth 服务；DB 表 → `data/model/models.py`；接入路由 → `api/routes.py`；JWT/哈希属基础设施 → `infrastructure/auth/`。
是否新建目录：若逻辑多可 `domain/auth/` + `infrastructure/auth/`，否则并入现有层（原则一：不新造一层）。
