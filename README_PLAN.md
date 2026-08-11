# README 全面修订计划

> 基于 docs/product/feedback/ 下四方 AI 评审（Kimi / Qwen / doubao / dp）意见整合。
> 状态：已执行（2026-08-12，用户确认 7 项后全部实施，见 commit 记录）。

## P0 事实修正（准确性/安全/格式，无争议）

| # | 条目 | 来源 | 内容 |
|---|------|------|------|
| P0-1 | 「一句话出行程」表述 | Qwen#1 | 改为与表单流程一致（填表单→点生成） |
| P0-2 | 数据库密码明文 | Qwen#2 | `DATABASE_URL …travelpal123…` 改引用 `.env.example` 默认值 |
| P0-3 | 开发模式代码块损坏 | Qwen#3 | `docker compose up -d postgres redis` / `make celery` / `make help` 用 bash 包裹 |
| P0-4 | 前置条件自相矛盾 | Qwen#4 | 改「Python3.12 + Node22 + Docker」，明确 PG/Redis 由 Docker 提供 |
| P0-5 | Swagger 8000 端口 | Qwen#11 | 核实 docker-compose 是否映射后定措辞 |
| P0-6 | 许可年份格式 | Qwen#16 | `Copyright © 2026` → `起始年-2026` |
| P0-7 | API Key 表 AMAP_JS_KEY 描述 | Qwen#9 | 改为「同一应用下添加 Key（Web JS API）」，明确两个独立 Key |

## P1 产品感（营销/结构，多数采纳）

| # | 条目 | 来源 | 内容 |
|---|------|------|------|
| P1-1 | 对比部分折叠 | Kimi#4/doubao | `<details>` 折叠或精简一句 + 文档站链接 |
| P1-2 | 对比收尾加具体例子 | dp#4 | 「同样 5 个景点，输出可执行路线而非一段文字」 |
| P1-3 | 技术概览表格与文字重复 | Qwen#8 | 二选一：删表格或改一行「技术栈速览」 |
| P1-4 | 竞品名称统一 | Qwen#12 | FAQ「Stardrift」vs README「Wanderlog」统一 |
| P1-5 | 「对话式共创」标签 | Qwen#5 | 降级（AI 只支持查询辅助，撑不起「共创」） |
| P1-6 | 加 Roadmap 章节 | Kimi#8 | v1.0 已发布 / v1.1 规划中表格 |
| P1-7 | 加 FAQ 入口 | Qwen#14 | README 加 FAQ 链接 |
| P1-8 | 技术概览缓冲带 | Kimi#6 | 「如果你想了解它能做什么，上面已足够；如果你好奇怎么做到的，下面是实现细节」 |
| P1-9 | 快速开始/开发模式拆分 | Kimi#7 | 「🚀 快速体验（推荐）」vs「🔧 本地开发（贡献者）details 折叠」 |
| P1-10 | 快速开始加 Key 前置提醒 | Qwen#10 | 配置环境变量步骤加「⚠️ 首次运行前需先申请 API Key，见下方表格」 |
| P1-11 | 加 Contributing 指引 | Qwen#15 | 末尾「欢迎 PR」补简短贡献指引 |
| P1-12 | 痛点补桥接句 | dp#2 | 「因为大多数工具只帮你『想』，不帮你『算』」 |
| P1-13 | 无 Key 功能可用性说明 | doubao#4 | 明确「没有 Key 哪些功能可用」（或声明全部核心依赖 Key） |
| P1-14 | VNS 描述 | Qwen#7/dp#5 | 精简一句话 + 保留「为未来大规模预留」意图 |

## P2 视觉（需用户提供素材）

| # | 条目 | 来源 | 内容 |
|---|------|------|------|
| P2-1 | 徽章精简 | Kimi#2/dp#1/Qwen#6 | 精简至 3-5 枚（在线体验/Release/License），技术徽章合入技术概览或删 |
| P2-2 | 第一屏主界面截图 | Kimi#1/Qwen#13 | 标题下放 800px 图，路径 `docs/assets/screenshot-home.png`（本地仓库，不外链） |
| P2-3 | 实证数据 | doubao#2 | 技术概览补 Dumas 求解质量/偏差率一类数据 |

## 明确不采纳

| 条目 | 来源 | 理由 |
|------|------|------|
| 痛点改「周六早上 9 点」长叙事 | Kimi#3 | 与「克制」哲学不符 |
| 它给你什么改对比表格 | Kimi#5 | 4 bullet 已定，改动大收益一般 |
| Social Proof 用户语录 | Kimi#9 | 无真实用户 |
| 自研求解器答「为何不用 OR-Tools」 | doubao#5 | 自研是核心叙事，已多轮确认 |

## 待用户确认事项

1. **slogan 去留**（doubao#1）：A 保持原样 / B 下方补白话定位（如「基于约束求解的可执行旅行规划工具」）/ C 其他
2. **版本状态首屏位置**（doubao#6/dp#1）：A 移走（放快速开始前）/ B 精简一行 / C 保留现状
3. **实证数据**（doubao#2）：是否有 Dumas 求解质量数据（gap%、耗时）？有则补，无则定性表述
4. **徽章取舍**（P2-1）：保留哪 3-5 枚（建议：在线体验 + Release + License + 可选 Codecov/Python）
5. **主界面截图**（P2-2）：需用户在浏览器截图，800px 宽，放 `docs/assets/screenshot-home.png`
6. **P1-9 拆分方案**：快速体验 vs 本地开发（details 折叠）结构是否同意
7. **P1-13 无 Key 说明**：确认「所有核心功能依赖 API Key」陈述是否准确
