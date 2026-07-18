# Agent 层

## 修改记录

| 日期 | 变更 |
|------|------|
| 2026-07-18 | 从 backend.md 拆分独立 |

## 一、架构总览

Agent 层位于 HTTP 路由层和求解引擎层之间，负责 LLM 对话与工具调用。

```
路由层 (routes.py)
    ↓ POST /api/chat
Agent 层
    ├── chat.py        对话流调度
    ├── tools/          工具注册与执行
    ├── commentator.py  评语生成
    └── planner.py      规划调整
    ↓
引擎层 (engine/)     ← 工具函数（poi_lookup 等）
```

## 二、目录结构

```
backend/agent/
├── chat.py           对话流：build_chat_messages / chat_stream / stream_chat
├── commentator.py    评语生成器：generate_commentary
├── planner.py        三指令规划器：add_poi / remove_poi / adjust_days
└── tools/
    ├── __init__.py   工具注册表 TOOL_REGISTRY
    ├── prompts.py    所有 LLM prompt 模板集中管理
    ├── poi.py        POI 查询工具：poi_lookup / parse_biz_hours
    └── rag.py        BM25 检索引擎：search_rag() / RagEngine
```

## 三、对话流

详见 [`backend.md §四 路由层`](backend.md#四http-接口层-api)。

### SSE 协议格式

后端通过 `text/event-stream` 推送结构化事件：

| type | 触发时机 | 前端行为 |
|------|---------|---------|
| `tool_status` | LLM 返回 tool_call 时 | 显示"正在查询..." |
| `tool_result` | 工具执行完成后 | 渲染 POI 卡片至左侧待选栏 |
| `content` | LLM 流式生成文字时 | 打字机效果追加 |
| `error` | 对话生成异常时 | 显示错误提示 |
| `done` | 全部输出完毕 | 结束 loading 状态 |

### 消息构建

`build_chat_messages()` 从 `prompts.py` 读取 `CHAT_SYSTEM`，附加规划上下文后组装为 OpenAI 格式。

### RAG 上下文注入

每次调用 `build_chat_messages()` 时自动触发 BM25 全文检索（[`rag.py`](../../backend/agent/tools/rag.py)）：

1. `search_rag(query)` 对用户消息分词后检索 `docs/*.md` + `README.md`
2. 取 top-3 相关片段，格式化为 `相关知识：\n- [来源] 标题：片段...`
3. 以 `system` 角色注入消息列表（位于 `CHAT_SYSTEM` 之后，user 消息之前）

匹配策略：中文拆单字、英文空白分词，无需 jieba 等外部库。

### 调试模式

`MOCK_MODE=True` 时走 `mock_stream_chat()` 固定回复，无需 API Key。
正式部署应保持 `MOCK_MODE=False`。

## 四、工具系统

### 注册表

`TOOL_REGISTRY` 字典集中管理所有可调用工具（[`tools/__init__.py`](../../backend/agent/tools/__init__.py)）：

```text
TOOL_REGISTRY: dict[str, Callable] = {
    "poi_lookup": poi_lookup,
}
```

新增工具只需在 `tools/` 下新建文件、实现函数、注册到 `TOOL_REGISTRY`。

### 主流程

```
用户消息 → build_chat_messages() + TOOL_DEFINITIONS
  → LLM 非流式首调
    ├─ tool_calls → 执行工具 → tool_result 追加 messages → LLM 二次调用 → SSE 流式回复
    └─ text       → SSE 直接流式输出
```

### poi_lookup 工具

详见 [`tools/poi.py`](../../backend/agent/tools/poi.py)。

通过高德 API 查询 POI 坐标、地址和营业时间。自动识别酒店与景点：

- 酒店：`poi_type="hotel"`，时间窗 `0-1440`（全天）
- 景点：`poi_type="spot"`，时间窗由 LLM 解析 `opentime2`

详见 [`data.md §POILookupItem`](data.md#poilookupitemapi-响应)。

## 五、提示词管理

所有 LLM prompt 集中在 `tools/prompts.py`：

| 常量 | 用途 |
|------|------|
| `CHAT_SYSTEM` | 对话系统 prompt |
| `PARSE_PROMPT` | 营业时间 LLM 解析模板 |
| `POI_TOOL_DEF` | poi_lookup 工具定义（JSON schema） |
| `TOOL_DEFINITIONS` | 全部工具定义列表 |

## 六、评语与规划调整

### commentator.py

`generate_commentary(plan_result)` → 自然语言评语。规则模板 + LLM 润色混合模式。
详见 [`docs/产品路线图.md`](../产品路线图.md) 第一阶段。

### planner.py

三指令规划器，当前函数已就绪但**未接入 Function Calling**：

| 函数 | 功能 |
|------|------|
| `add_poi_to_plan()` | 加景点后调用 `cluster_and_solve` 重算 |
| `remove_poi_from_plan()` | 去景点后重映射索引重算 |
| `adjust_plan_days()` | 调天数后重分配行程 |

目标：后续注册到 `TOOL_REGISTRY` 后，用户可通过对话调整方案。

## 七、数据流

### Function Calling 流程

```
用户: "查一下广州的白云山"
  → POST /api/chat { message: "查一下广州的白云山" }
  → build_chat_messages() → [system, user]
  → OpenAI tools=TOOL_DEFINITIONS
  → LLM: tool_call → poi_lookup(city="广州", name="白云山")
  → 高德 API → 坐标/地址/营业时间
  → SSE: tool_result
  → pendingPois[] 追加 ← 前端左侧待选栏
  → messages 追加 tool result → LLM 二次调用
  → SSE: content → "找到了！白云山..."
  → SSE: done
```

### RAG 检索流程

```
用户: "这个项目是做什么的"
  → POST /api/chat { message: "这个项目是做什么的" }
  → build_chat_messages()
      ├─ search_rag("这个项目是做什么的") → BM25 检索 docs/ 相关片段
      └─ 注入 system message（知识段位于 user 之前）
  → OpenAI 无 tools 调用 → SSE 直接流式输出
  → SSE: content → "这是一个基于 VNS+ 引擎的..."
  → SSE: done
```
