# TravelPal

**不占有的陪伴，不缺席的可靠。**

[![Release](https://img.shields.io/github/v/release/xiaojiune/TravelPal?include_prereleases)](https://github.com/xiaojiune/TravelPal/releases)
[![codecov](https://codecov.io/gh/xiaojiune/TravelPal/branch/dev/graph/badge.svg)](https://codecov.io/gh/xiaojiune/TravelPal)
[![Commits](https://img.shields.io/github/commit-activity/m/xiaojiune/TravelPal)](https://github.com/xiaojiune/TravelPal/commits/dev)
[![License](https://img.shields.io/github/license/xiaojiune/TravelPal)](LICENSE)
[![trippal.site](https://img.shields.io/website?url=https://trippal.site&label=trippal.site)](https://trippal.site)
[![CI](https://img.shields.io/github/actions/workflow/status/xiaojiune/TravelPal/ci.yml?branch=main)](https://github.com/xiaojiune/TravelPal/actions)
[![MCP](https://img.shields.io/badge/MCP%20Server-integrated-4D77FF)](backend/mcp/)
[![Python](https://img.shields.io/badge/Python-3.12-blue?logo=python)](pyproject.toml)
[![Vue](https://img.shields.io/badge/Vue-3-green?logo=vuedotjs)](frontend/)

📌 **版本状态**
- 🟠 橙色徽章 = 新功能预发布，[🌐点击前往dev](https://github.com/xiaojiune/TravelPal/tree/dev)
- 🔵 蓝色徽章 = 稳定版已部署，[🌐点击前往体验](https://trippal.site)

📖 文档站：<https://xiaojiune.github.io/TravelPal/>

🏷️ `AI 行程决策引擎 · 对话式共创 · 全栈工程化`

---

## 🎒 规划一次旅行，是不是总这样？

- 翻遍攻略和点评，还是不知道该把哪些地方排进同一天
- 营业时间、开车耗时、停留时长……全靠感觉估算
- 排出来的行程"看起来合理"，真出门却发现根本走不完

TravelPal 把这些体力活接过来：你说一句想去哪，它把坐标、营业时间、驾车耗时全部核实好，再交给算法排出一条真的能走完的行程。

## ✨ 它给你什么

- **一句大白话，一条真行程**：告诉它想去哪、玩几天，剩下的它来
- **精确到分钟的行程表**：每个景点几点到、几点走、营业时间对不对，一目了然
- **真实驾车路线**：不是画直线，基于高德真实路网逐段验证
- **多套方案挑着选**：不同天数与求解方法多组选择，决策权始终在你

> 更多正在生长：对话式行程调整、个性化偏好记忆已在规划中——不承诺一步到位，但每一步都在长。

## 🤔 和市面上的旅行产品有什么区别？

**基础设施与平台（高德地图、携程、飞猪）**
解决「怎么到、怎么订」：地图导航、交通住宿预订。优势是数据与生态完备，但不负责「该去哪、按什么顺序去」——排程决策仍靠你自己。

**商业与主流规划软件（马蜂窝、穷游、Wanderlog、TripIt）**
攻略内容社区或手动整理工具。优势是 UGC 丰富、信息真实，但规划本质是信息聚合与人工整理，不对景点顺序、营业时间做约束求解——给你「建议」，不是「可执行的方案」。

**开源与 AI Agent 项目（智旅云图、TripStar）**
同走对话式 AI 路线，多为 LangChain + RAG 生成图文攻略。样式丰富、观感高级，但伴随着「不确定性」：绕路、营业时间不符、时间估算失真，方案看着合理，未必走得了。

**TravelPal 不只聚合信息，更给你可信任的行动**
- 别人有的，它也有：需求理解与信息聚合（POI 坐标、营业时间、驾车耗时），LLM 负责听懂与整理
- 别人没有的，它补上：CA/VNS 把营业时间、停留时长、驾车耗时纳入约束求解，每条路线经算法校验——给你「建议」之外的「可执行方案」
- 产出「精确时间表 + 真实驾车路线 + 可交互地图」

## ⚙️ 技术概览

**决策层 —— LLM Agent（LangGraph 编排）**
- 听懂自然语言，把「想去哪」变成可执行的规划请求
- 工具化接入 POI 查询、驾车耗时、基于表单直接生成行程

**求解层 —— CA / VNS 元启发式算法（未引入第三方求解框架）**
- 压缩退火（CA）为当前主力：秒级给出可行方案
- 变邻域搜索（VNS）邻域结构完整，面向单日大规模排布——当前行程点数少、CA 已近似等价，
  故暂不参与主流程；两者同为未来统一 OR 求解器的组成，现按场景拆分
- 严格约束营业时间窗、停留时长与驾车耗时，输出路径最优的每日行程
- 基于 Dumas TSPTW 基准算例（n20 / n40 / n60）验证求解质量

**工程层 —— 全栈工程化落地**
- FastAPI + SSE 流式对话，Celery + Redis 异步任务，PostgreSQL + Alembic 数据迁移
- Vue 3 + TypeScript + Naive UI，高德地图真实路线可视化
- Docker Compose 五服务一键部署，GitHub Actions 自动化 CI/CD
- 面向外部 AI 助手提供 MCP Server 接入同一套工具

| 方向 | 技术                                                 |
|------|------------------------------------------------------|
| 后端 | FastAPI · LangGraph · Celery · PostgreSQL · Redis    |
| 引擎 | NumPy · Numba JIT（ CA / VNS）                       |
| 前端 | Vue 3 · TypeScript · Naive UI · 高德 JS API          |
| 工程 | Docker Compose · Nginx · GitHub Actions · MCP Server |

## 🚀 快速开始

前置条件：Docker、Docker Compose。

```bash
# 1. 克隆
git clone https://github.com/xiaojiune/TravelPal.git
cd TravelPal

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env，填入以下 key（申请方式见下表）

# 3. 一键启动（五服务编排：PostgreSQL + Redis + Celery worker + 后端 + 前端 Nginx）
make deploy-up
# 首次启动自动执行数据库迁移（Alembic），无需手动初始化

# 4. 打开 http://localhost
# 后端启动后可访问 http://localhost:8000/docs 查看交互式 Swagger API 文档
```

### 获取 API Key

| Key | 获取地址 | 用途 |
|-----|---------|------|
| `AMAP_API_KEY` | [高德开放平台](https://lbs.amap.com/) → 控制台 → 应用管理 → 创建应用 → 添加 Key（Web 服务） | 后端 POI 搜索 / 驾车路径规划 |
| `AMAP_JS_KEY` | 同上（Web JS API） | 前端地图渲染 |
| `AMAP_JS_SECURITY_CODE` | 同上→ 添加 Key → 安全密钥 | 前端地图安全验证 |
| `LLM_API_KEY` | [DeepSeek 平台](https://platform.deepseek.com/) → API Keys | Agent 对话 |

## 🔧 开发模式

想直接用 Docker 一键体验？见上方「快速开始」（`make deploy-up`）。

前置条件：Python 3.12、Node.js 22、PostgreSQL、Redis。

本地数据库依赖通过 Docker 启动（无需本地安装）：
docker compose up -d postgres redis

```bash
make install            # 一键安装前后端依赖
cp .env.example .env    # 配置环境变量
#注意:（本地开发 DATABASE_URL 需改为 postgresql+asyncpg://travelpal:travelpal123@localhost:5432/travelpal）
make serve              # 启动后端（热重载）
make dev                # 启动前端（Vite HMR）
```

异步任务（行程规划）依赖 Celery worker，本地需另开终端启动：
make celery

完整命令清单：
make help

## 许可

Copyright © 2026 xiaojiune. Released under the MIT License.

---

欢迎 Star / Issue / PR 交流。
