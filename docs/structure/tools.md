# 工具清单

## 修改记录

| 日期 | 变更 | 动机 |
|------|------|------|
| 2026-08-25 | 重写：注册表增至 7 个工具，poi 类型扩展 facility，plan 类改为异步任务提交 | 实际工具演进，旧文档仅 2 个工具 |
| 2026-08-08 | 移除 travelpal_search_rag（RAG 工具已删，BM25 引擎保留供未来复用） | RAG 工具壳移除 |
| 2026-08-04 | 新增 travelpal_get_driving；修正 travelpal_poi_lookup 参数为批量 names | 工具扩展 |
| 2026-08-03 | 初稿 | 建立工具清单 |

## 读者指南

| 列 | 内容 |
|----|------|
| 面向读者 | Agent / MCP 维护者、外部 AI 助手接入方 |
| 阅读前置 | [agent.md](agent.md)、[backend.md](backend.md) |
| 阅读目标 | 了解 Agent 可调用工具、契约与执行方式 |

## 架构总览

本页记录 TravelPal 通过 `TOOL_REGISTRY` 暴露给 Agent（内部 Function Calling）与外部 AI 助手（MCP Server）的全部工具。

- **单一事实来源**：`backend/agent/tools/__init__.py` 的 `TOOL_REGISTRY`。
- **分组元数据**：`TOOL_CATEGORIES` 按 `poi/plan/driving` 分组，供编排器裁剪、未来 MCP 分组与 Agent-driven UI 表单渲染。
- **工具契约**：`tools/schema.py` 从函数类型注解自动生成 `build_tool_definitions()`，与 MCP input_schema 同源。
- **异步任务**：`get_plan` / `submit_plan_form` 提交规划任务（写 `plan_tasks`，Celery 执行），立即返回 `task_id`，调用方用 `get_plan_result` 轮询。
- **MCP 暴露**：`backend/mcp/server.py` 遍历注册表动态注册，`make mcp-serve`（stdio）启动，opencode 经懒加载接入。

当前注册表（`TOOL_CATEGORIES` 分组）：

| 分组 | 工具 | 作用 |
|------|------|------|
| poi | poi_lookup | 批量查询 POI 坐标/地址/营业时间，识别类型 |
| plan | get_plan | 提交完整行程规划异步任务 |
| plan | get_plan_result | 轮询规划任务状态与结果 |
| plan | submit_plan_form | 基于表单上下文提交规划任务（表单驱动入口） |
| plan | add_poi | 向已有方案添加 POI（单日/全局重排） |
| plan | remove_poi | 从已有方案移除 POI（单日/全局重排） |
| driving | get_driving | 查询两点间驾车距离与耗时 |

## 数据流

### 内部 Function Calling

Agent 编排器（`orchestrator`）的 tools 节点按 `TOOL_REGISTRY` 分发执行，结果回填为 tool 消息再回到 agent 决策。

### 外部 MCP

`MCP Server` 遍历 `TOOL_REGISTRY` 注册叶子工具，外部 AI 助手（如 opencode）经 stdio 调用，实现留进程边界内。

### 异步规划工具（get_plan / submit_plan_form / add_poi / remove_poi）

1. 调用方提交请求 → `submit_task` 创建 `plan_tasks` 记录并投递 Celery。
2. worker 消费执行（`_run_suggest/_run_plan/_run_adjust`）。
3. 调用方用 `get_plan_result` 轮询 `status` 直至 done/failed。

## 工具契约

### poi_lookup

- **描述**：通过高德 API 批量查询 POI 的坐标、地址和营业时间，自动识别类型（酒店/景点/设施）。
- **参数**：`city`（string，必填），`names`（array[string]，必填）。
- **返回**：`list[dict]`，每项 `{ name, lon, lat, address, tw_start, tw_end, poi_type }`；`poi_type` 为 `hotel|spot|facility|unknown`。单点失败返回 `{ name, error }`。酒店默认 0-1440（全天）。

### get_plan

- **描述**：提交完整行程规划任务，立即返回 `task_id`。
- **参数**：与 `PlanRequest` 全量对齐（city/hotel_name/hotel_lon/hotel_lat/spots/n_days/mode...）。
- **返回**：`{ task_id, status: "pending" }` `或 { error }`。

### get_plan_result

- **描述**：查询规划任务状态与结果。
- **参数**：`task_id`（string，必填）。
- **返回**：`{ task_id, status, result?, error? }`；`status` 为 pending/running/done/failed，`result` 仅 done 存在。

### submit_plan_form

- **描述**：基于表单上下文（`form_context`，由编排层注入首页表单快照）提交规划任务；`n_days` 缺失走 suggest（自动推断天数），指定走 plan。
- **返回**：`{ task_id, status }` 或 `{ error }`。

### add_poi / remove_poi

- **描述**：向已有方案添加/移除 POI。`day` 缺失（用户意图未定）走全局重排，指定走单日重排。需 `plan`（当前方案快照）注入。
- **返回**：同步路径返回完整调整后方案（PlanResult）；异步路径返回 `{ task_id, status }` 供轮询；参数缺失返回 `{ error }`。

### get_driving

- **描述**：查询两点间驾车距离与耗时，供 AI 问答「A 到 B 耗时多久」。
- **参数**：`origin`/`destination`，各含 `{ name, lon, lat }`。
- **返回**：`{ origin_name, destination_name, distance_km, duration_min }`；失败 `{ error }`。折线暂不返回。

## 术语表

| 术语 | 定义 |
|------|------|
| TOOL_REGISTRY | 工具注册表 dict[str, Callable]，编排器/MCP 分发执行唯一来源 |
| TOOL_CATEGORIES | 工具分组元数据（poi/plan/driving） |
| build_tool_definitions | 从类型注解自动生成工具 schema（与 MCP input_schema 同源） |
| plan_tasks | 异步规划任务表 |

## 维护契约

新增/修改工具时必须同步：

- **新增工具**：在 `tools/` 对应子包实现（含完整 docstring，作为 MCP 描述来源）→ 注册到 `TOOL_REGISTRY` → 在 `TOOL_CATEGORIES` 标分组 → 更新本页「架构总览」表与「工具契约」节 → 重启 opencode（MCP 懒加载）。
- **改工具签名**：`tools/schema.py` 自动生成 schema，但需验证 `build_tool_definitions()` 输出，并同步前端表单（如 Agent-driven UI）。
- **改异步工具**：`get_plan` 等依赖 `plan_tasks` + Celery，需同步 [backend.md](backend.md) 的任务编排与 [data.md](data.md) 数据模型。
- **移除工具**：从 `TOOL_REGISTRY` 与 `TOOL_CATEGORIES` 删除，同步本页与相关文档。