# structure 文档规范

`docs/structure/` 目录的规范说明与本目录文档索引。
每个子目录以 `README.md` 自描述是本目录惯例（分形文档），本文即 `structure/` 的 README。

## 修改记录

| 日期 | 变更 | 动机 |
|------|------|------|
| 2026-08-06 | docs.md → README.md 重写为 structure 规范 | 承接 ARCHITECTURE.md 文档导航，明确 structure 每篇必备章节与写作约定 |

## 一、文档分层

| 层级 | 位置 | 职责 |
|------|------|------|
| 根 README | `README.md` | 产品介绍、徽章、快速开始 |
| 架构总入口 | `ARCHITECTURE.md` | C4 图 + 决策速览 + 文档导航 |
| 项目结构 | `docs/structure/`（本文） | 各层详解与数据字典 |
| 架构决策 | `docs/ADR/` | 决策记录 + 写作规范（`README.md`）+ 模板（`TEMPLATE.md`） |
| 运维手册 | `docs/runbooks/` | 故障排查等可操作手册 |
| 接口规范 | `docs/openapi.json` | Sphinx 构建自动生成 |

## 二、structure 统一规范

`structure/` 下每篇文档必备以下章节（顺序可调）：

| 章节 | 要求 | 说明 |
|------|------|------|
| 修改记录 | 保留 + 补动机列 | 每行含日期、变更、动机；不删除历史行 |
| 读者指南 | 可选 | 声明面向读者（如「后端开发」）与阅读前置 |
| 架构总览 | 必备 | 一段话讲清该层职责与上下层关系 |
| 目录结构 | 必备 | 目录树带行内注释，说明每个文件职责 |
| 数据流 | 必备 | 用 Mermaid 或表格描述该层数据流转 |
| 术语表 | 建议 | 收录该层出现的关键名词定义 |
| 维护契约 | 必备 | 声明「改什么必须同步什么」（如改 schema 需跑 gen:api） |

### 写作约定

- **文件路径归验证列**：正文中不写源码路径，路径放入 ADR-011++ 等「组件状态跟踪」表格的验证列，避免正文随重构失效
- **新图用 Mermaid**：GitHub 原生渲染；Sphinx 显示代码块，不引入 mermaid 依赖
- **读者指南表格模板**：

| 列 | 内容 |
|----|------|
| 面向读者 | 角色（如前端开发/运维） |
| 阅读前置 | 建议先读的文档 |
| 阅读目标 | 读完能做什么 |

## 三、本目录索引

| 文档 | 覆盖 |
|------|------|
| [`project.md`](project.md) | 项目全局目录与模块总览 |
| [`backend.md`](backend.md) | 后端分层架构与引擎链路 |
| [`agent.md`](agent.md) | Agent 编排、工具、RAG 流程 |
| [`frontend.md`](frontend.md) | 前端组件树、路由、状态管理 |
| [`data.md`](data.md) | 全链路数据字典（单位约定 + 类型定义） |
| [`tools.md`](tools.md) | MCP 工具清单（单一事实来源 TOOL_REGISTRY） |

## 四、维护契约

修改本文档任一结构文件时，同步检查：

1. 改动了 `backend/` 公开接口 → 更新 `backend.md` + `data.md` + 对应 ADR 组件状态跟踪表
2. 改动了 MCP 工具注册 → 更新 `tools.md`（TOOL_REGISTRY 是单一事实来源）
3. 改动了路由/schema → 跑 `make gen-api` 重新生成 openapi.json 与前端类型
4. 本目录文档索引变化 → 同步 `index.rst` 与根 `ARCHITECTURE.md` 文档导航

## 五、交叉引用

- 根 `ARCHITECTURE.md`：本目录是它「项目结构」章节的下钻入口
- `docs/ADR/README.md`：ADR 写作规范与完整索引
- `docs/runbooks/troubleshooting.md`：故障排查手册
