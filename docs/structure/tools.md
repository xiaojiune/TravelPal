# 工具清单（MCP 工具定义）

## 修改记录

| 日期 | 变更 |
|------|------|
| 2026-08-03 | 初稿 |
| 2026-08-04 | 新增 travelpal_get_driving；修正 travelpal_poi_lookup 参数为批量 names |
| 2026-08-08 | 移除 travelpal_search_rag（RAG 工具已删，BM25 引擎保留供未来复用） |

## 概述

本页记录 TravelPal 通过 MCP Server（`backend/mcp/server.py`）暴露给外部 AI 助手的全部工具，按 MCP 工具定义格式编写。

- **单一事实来源**：`backend/agent/tools/__init__.py` 的 `TOOL_REGISTRY`。
- MCP Server 遍历注册表动态注册工具，**新增工具 = 注册一行 + 同步本文档**。
- 工具契约（名称/描述/参数 schema）进入 AI 上下文，实现留在进程边界内。
- 运行方式：`make mcp-serve`（stdio 传输），opencode 经 `experimental.mcp_lazy_load` 懒加载接入。

## travelpal_poi_lookup

- **描述**：通过高德 API 批量查询 POI 的坐标、地址和营业时间。自动识别每个 POI 类型（酒店/景点），酒店默认时间窗为 0-1440（全天）。
- **参数**：
  | 参数 | 类型 | 必填 | 说明 |
  |------|------|------|------|
  | city | string | 是 | 所在城市 |
  | names | array[string] | 是 | POI 名称列表（酒店/景点） |
- **返回**：`list[dict]`，每项 `{ name, lon, lat, address, tw_start, tw_end, poi_type }`
  - `poi_type`: `"hotel"` | `"spot"` | `"unknown"`
  - 单个查询失败时该项为 `{ name, error: str }`

## travelpal_get_driving

- **描述**：查询两点间驾车距离与耗时，供 AI 问答"A到B耗时多久"。
- **参数**：
  | 参数 | 类型 | 必填 | 说明 |
  |------|------|------|------|
  | origin | object | 是 | 起点，`{ name: string, lon: number, lat: number }` |
  | destination | object | 是 | 终点，`{ name: string, lon: number, lat: number }` |
- **返回**：`{ distance_km: number, duration_min: number }`
  - 失败时返回 `{ error: str }`
  - 折线数据暂不返回，待以后扩展
- **架构预留**：当前仅支持驾车；后期融合步行/骑车/公交时新增对应包装函数（见 `backend/agent/tools/driving.py` docstring）。

## 如何新增工具

1. 在 `backend/agent/tools/` 下实现工具函数（含完整 docstring，作为 MCP 描述来源）。
2. 在 `backend/agent/tools/__init__.py` 的 `TOOL_REGISTRY` 注册一行。
3. 重启 opencode（MCP Server 懒加载，工具自动出现）。
4. 同步本文档，新增对应工具定义节。
