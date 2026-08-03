# 工具清单（MCP 工具定义）

## 修改记录

| 日期 | 变更 |
|------|------|
| 2026-08-03 | 初稿 |

## 概述

本页记录 TravelPal 通过 MCP Server（`backend/mcp/server.py`）暴露给外部 AI 助手的全部工具，按 MCP 工具定义格式编写。

- **单一事实来源**：`backend/agent/tools/__init__.py` 的 `TOOL_REGISTRY`。
- MCP Server 遍历注册表动态注册工具，**新增工具 = 注册一行 + 同步本文档**。
- 工具契约（名称/描述/参数 schema）进入 AI 上下文，实现留在进程边界内。
- 运行方式：`make mcp-serve`（stdio 传输），opencode 经 `experimental.mcp_lazy_load` 懒加载接入。

## travelpal_poi_lookup

- **描述**：通过高德 API 查询 POI 的坐标、地址和营业时间。自动识别 POI 类型（酒店/景点），酒店默认时间窗为 0-1440（全天）。
- **参数**：
  | 参数 | 类型 | 必填 | 说明 |
  |------|------|------|------|
  | city | string | 是 | 所在城市 |
  | name | string | 是 | POI 名称 |
- **返回**：`{ name, lon, lat, address, tw_start, tw_end, poi_type }`
  - `poi_type`: `"hotel"` | `"spot"` | `"unknown"`
  - 查询失败时返回 `{ error: str }`

## travelpal_search_rag

- **描述**：全局接口：检索 RAG 文档库，惰性初始化。
- **参数**：
  | 参数 | 类型 | 必填 | 说明 |
  |------|------|------|------|
  | query | string | 是 | 用户查询文本 |
  | k | integer | 否 | 返回 top-k 条结果，默认 3 |
- **返回**：`list[dict]`，每项含 `score` / `source` / `heading` / `text`，按 BM25 分数降序。

## 如何新增工具

1. 在 `backend/agent/tools/` 下实现工具函数（含完整 docstring，作为 MCP 描述来源）。
2. 在 `backend/agent/tools/__init__.py` 的 `TOOL_REGISTRY` 注册一行。
3. 重启 opencode（MCP Server 懒加载，工具自动出现）。
4. 同步本文档，新增对应工具定义节。
