# 后端分层决策（做法）

> 一行深引用，本文件供 SKILL.md 按需加载。目录职责与选层判断，不涉代码风格。

## 架构：六边形（整洁）架构

backend 是**六边形架构**：`domain` 定义端口（抽象），`infrastructure` 提供端口实现，`api` 只做 HTTP 接入。依赖方向单一、可插拔——换实现（多数据源、可插拔算法引擎）不动 `domain`。

```
api ──→ domain / agent / tasks       （只做 HTTP 接入，不碰实现）
domain ──→ (端口定义 ports.py + 业务编排)   （零依赖纯接口，不碰 HTTP/IO 实现）
agent ──→ domain / infrastructure       （LLM 对话/工具/规划）
tasks ──→ domain / infrastructure       （Celery 异步重活）
infrastructure ──→ (端口实现，可插拔)       （data/engine/llm/weather/retrieval/auth）
mcp / observability / utils / config.py / typedefs.py   （旁路 / 工具 / 配置）
```

**核心规则**：`domain/ports.py` 只定义端口（如 `DrivingDataProvider`、`Solver`），实现全部由 `infrastructure/` 提供——`infrastructure/data` 实现数据端口、`infrastructure/engine` 实现求解器端口。依赖方向单一，换实现的爆炸半径因此很小。

## 各层职责

| 层 | 职责 | 典型 |
|---|---|---|
| `api/` | HTTP 接入、请求/响应 schema、鉴权接入、生命周期 | server.py、routes.py、schemas.py、admin.py、auth.py |
| `domain/` | **端口定义** + 业务编排（不碰实现） | ports.py（端口）、pipeline.py（双阶段编排）、clustering.py、fitness.py、search.py、llm_service.py、weather_service.py |
| `agent/` | LLM 对话/工具/规划 | chat/、planning/、tools/（driving/plan/poi）、prompts.py |
| `infrastructure/data/` | 数据端口实现（`DrivingDataProvider`） | amap_loader.py、driving_service.py、checkpointer.py、conversations.py、driving_cache.py、model/ |
| `infrastructure/engine/` | 求解器端口实现（`Solver`）+ 注册表 | ca.py、vns.py、solver.py（`SOLVER_REGISTRY`） |
| `infrastructure/llm/` | LLM 实现（可插拔） | factory.py、openai_impl.py、dspy_optimizer.py |
| `infrastructure/weather/` | 天气实现（可插拔） | factory.py、http/mcp_weather_service.py |
| `infrastructure/retrieval/` | 检索实现 | bm25.py、hybrid_retriever.py、llama_index_retriever.py |
| `infrastructure/auth/` | 会话/鉴权实现 | session_store.py |
| `tasks/` | Celery 异步任务 | app.py、submit.py、executors.py、worker.py |
| `mcp/` | MCP 服务器（不引用编排层） | server.py |
| `observability/` | Prometheus 指标 | metrics.py |
| `config.py` / `typedefs.py` | 配置 / 全局类型（单一来源） | — |
| `utils/` | 跨层通用工具（纯函数，无状态） | breaker.py、decorators.py、gen_openapi.py、sync_all.py |

> 关键：**没有顶层 `engine/`、`data/`**——算法与数据实现都收敛在 `infrastructure/` 下（它们是可插拔的端口实现）。`infrastructure/engine/solver.py` 是求解器注册表（`SOLVER_REGISTRY`，CA/VNS 已注册），未来统一 OR 引擎在此新增即可，编排/调度零改动（呼应"绞杀者模式"）。

## 选层判断（功能类型 → 建议层）

| 功能类型 | 建议层 | 反例（放错） |
|---|---|---|
| 端口/抽象定义（接口、Protocol） | `domain/ports.py` | 放 `infrastructure/`（实现才在那） |
| 业务编排/用例 | `domain/` | `api/`（路由里写业务） |
| 算法求解实现 | `infrastructure/engine/` | `api/` 或 `domain/` |
| 数据访问实现（API/DB/缓存） | `infrastructure/data/` | `engine/` |
| 外部服务实现（LLM/天气/检索/鉴权） | `infrastructure/` | `domain/`（domain 只定义端口） |
| LLM 对话 / 工具 | `agent/` | `api/` |
| HTTP 接入 | `api/` | `domain/` |
| 异步任务 | `tasks/` | `api/`（同步阻塞） |
| 全局配置 / 类型 | `config.py` / `typedefs.py` | 散落各层 |
| 跨层通用纯函数 | `utils/` | 在各层复制 |

## 放错层的信号

- 路由里出现业务计算 / 直接查表 → 下沉到 `domain/` 或 `infrastructure/data/`。
- `domain/` 里出现 DB / HTTP / redis 调用 → domain 只定义端口、不碰实现；实现该去 `infrastructure/`。
- `infrastructure/engine/` 里出现 IO → 求解器实现不该有 IO。
- `domain/` 里 `import` 了 `infrastructure/xxx` → 方向反了（domain 不依赖实现）。
- 同一段逻辑在多个层之间复制 → 提公共模块（Rule of Three，见 SKILL.md 原则七）。
- 一个模块同时"建表 + 发任务 + 执行引擎" → 职责过重，是未来重构的痛点起点。

## 案例：用户系统（已落地）

`api/auth.py`（HTTP 接入）+ `domain/security.py`（鉴权逻辑/端口）+ `infrastructure/auth/session_store.py`（会话存储实现）+ `infrastructure/data/model/models.py`（用户表）。鉴权属业务 → 逻辑在 `domain`，实现（会话存储）在 `infrastructure/auth`，接入在 `api`。
