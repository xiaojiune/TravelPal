# Agent 层架构详解

## 修改记录

| 日期 | 变更 | 动机 |
|------|------|------|
| 2026-08-25 | 重写：跟随实际代码重构（chat/ 子包、planning/ 子包、prompts.py、tools/ 分组），对齐 structure 模板 | 旧文档按 backend agent 平铺结构描述，已与代码严重脱节 |
| 2026-07-18 | 从 backend.md 拆分独立 | 建立 agent 层独立文档 |

## 读者指南

| 列 | 内容 |
|----|------|
| 面向读者 | 后端开发者、Agent 功能维护者 |
| 阅读前置 | [backend.md](backend.md)、[data.md](data.md) |
| 阅读目标 | 读懂 Agent 层的对话编排、工具系统、prompt 管理与规划能力，动手扩展 Agent 功能 |

## 架构总览

Agent 层位于 HTTP 路由层（backend/api/）与求解引擎层（backend/engine/）之间，负责把用户的自然语言意图翻译成「查 POI、排行程、调方案」的动作。它不做路线求解，只负责 LLM 对话、工具分发与 SSE 事件流。

`路由层(backend/api/routes.py)` 到 `Agent 层(backend/agent/)` 再到 `引擎层(backend/engine/)` 的调用方向见下方数据流；Agent 层内部分为 chat/（对话编排）、planning/（规划能力）、prompts.py（prompt 集中管理）、tools/（工具注册表与分组子包）。

RAG 文档检索注入已于 **2026-08-08 移除**（项目文档查询对非技术用户无意义、技术人员直接看 GitHub）；BM25 引擎（infrastructure/retrieval/bm25.py）保留供未来 raw_data 清洗后复用。

## 目录结构

`backend/agent/` 实际目录树：

- **chat/**：对话编排
  - chat.py —— 消息组装：`build_chat_messages`（注入 README 自述 + 规划上下文）
  - orchestrator.py —— LangGraph 编排器：LLM 决策 → 工具执行 → 回填 → 再决策
- **planning/**：规划能力（消费引擎）
  - `__init__.py` —— 规划能力导出（方案调整 + 评语）
  - `_core.py` —— 方案重排公共内核：`extract_cores` / `reorder_from_cores`
  - commentator.py —— 评语生成：`generate_commentary`（@placeholder，待接入 agent 工具）
  - ops/ —— 方案调整操作子包：add_poi.py / remove_poi.py / balance.py
- **prompts.py** —— 所有 LLM prompt：`CHAT_SYSTEM` / `PARSE_PROMPT` / `build_date_context`
- **tools/**：工具出口
  - `__init__.py` —— 工具注册表 `TOOL_REGISTRY` + 分组元数据 `TOOL_CATEGORIES`
  - schema.py —— 工具契约生成器：`build_tool_definitions`
  - poi/ —— `poi_lookup` / `parse_biz_hours` / `estimate_stay`
  - plan/ —— `get_plan` / `get_plan_result` / `submit_plan_form` / `add_poi` / `remove_poi`
  - driving/ —— `get_driving`（驾车距离/耗时）

任务分工边界：`planning/` 是**引擎能力消费方**（被 `engine/pipeline.adjust_plan` 分发调用）；`tools/plan/` 是 **Agent 工具出口**（面向 LLM 的 `add_poi` / `remove_poi` 等）。二者都含「方案调整」，但一个走引擎重排、一个走工具调用，应在文档中区分。

## 数据流

### 对话编排（LangGraph 循环）

用户消息 → `build_chat_messages()`（CHAT_SYSTEM + 规划上下文 + 日期上下文）→ orchestrator 的 agent 节点调 `LLMService.complete`：

- 有 tool_call：进 tools 节点，按 `TOOL_REGISTRY` 分发执行 → 回填 tool 消息 → 回到 agent（图自环）
- 无 tool_call：stream 实时输出最终回复 → 结束

SSE 事件通过 LangGraph custom stream（StreamWriter）推送，协议：

| 事件 | 触发时机 | 前端行为 |
|------|---------|---------|
| `tool_status` | LLM 返回 tool_call 时 | 显示「正在查询…」 |
| `tool_result` | 工具执行完成 | 渲染 POI 卡片至待选栏 |
| `content` | LLM 流式生成文字 | 打字机效果追加 |
| `error` | 对话生成异常 | 显示错误提示 |
| `done` | 全部输出完毕 | 结束 loading |

### 工具调用示例（poi_lookup）

「查一下广州的白云山」→ POST /api/chat → build_chat_messages() → orchestrator agent 节点：LLM 工具决策 → tool_call: `poi_lookup(city=广州, name=白云山)` → 高德 API → 坐标/地址/营业时间 → SSE: tool_result → 前端待选栏 → 回填 tool 消息 → agent 再次决策 → SSE: content + done。

规划类工具（submit_plan_form）会自动注入表单上下文，n_days 由 LLM 根据用户提及决定（未提及则不传，引擎自动推断天数）。get_plan / get_plan_result 仅面向外部调用方，对话中不用。

## 术语表

| 术语 | 定义 |
|------|------|
| TOOL_REGISTRY | 工具注册表：dict[str, Callable]，编排器/MCP 分发执行的唯一来源 |
| TOOL_CATEGORIES | 工具分组元数据（poi/plan/driving），供编排器裁剪、未来 MCP 分组与表单渲染 |
| build_tool_definitions | 从函数类型注解自动生成工具 schema（与 MCP input_schema 同源），见 tools/schema.py |
| @placeholder | 已声明但未接线的能力占位符（如 generate_commentary），见 utils/decorators |

## 维护契约

修改本层代码时必须同步以下内容：

- **新增工具**：在 tools/ 下建实现 → 注册到 TOOL_REGISTRY → 在 TOOL_CATEGORIES 标分组 → 更新本文件「目录结构」与工具表。
- **改工具签名**：tools/schema.py 会自动从类型注解生成 schema，但需验证 build_tool_definitions() 输出，并同步对应前端表单（如 Agent-driven UI）。
- **改 prompt**：统一改 prompts.py，勿在模块内散落 prompt 字符串；同步本文件「数据流」相关描述。
- **改规划能力**：planning/ 被 engine/pipeline.adjust_plan 消费，改签名需同步该调用点；评语 generate_commentary 为占位，接线后更新「目录结构」与「维护契约」。