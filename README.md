# TravelPal · 旅行伴侣

**不是生成文字攻略，是生成可执行的行程方案。**
结合元启发式算法（CA/VNS）与 LLM Agent，严格保证时间窗约束与路径最优的智能旅行规划系统。

🏷️ `运筹优化 · LLM Agent · 地图可视化 · 全栈工程化`

[![GitHub License](https://img.shields.io/github/license/xiaojiune/TravelPal)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.12-blue?logo=python)](pyproject.toml)
[![Vue](https://img.shields.io/badge/Vue-3-green?logo=vuedotjs)](frontend/)
[![codecov](https://codecov.io/gh/xiaojiune/TravelPal/branch/dev/graph/badge.svg)](https://codecov.io/gh/xiaojiune/TravelPal)

📖 文档站：<https://xiaojiune.github.io/TravelPal/>
🌐 在线演示：<http://119.29.222.100>（域名 `trippal.site` 备案中）

---

## ✨ 核心功能

- **双引擎求解**：CA 秒级出可行方案 + VNS 深度迭代优化，严格保证时间窗约束下的路径最优
- **算法验证**：基于 Dumas TSPTW 基准测试集（n20~n200）多规模算例验证，n100 求解时间秒至分钟级
- **对话式规划**：LLM Agent 理解自然语言需求，支持边聊边调
- **地图可视化**：真实驾车路径实时渲染，景点标注精确到达/离开时间与状态
- **方案选择**：一次生成多组方案，按总成本/时长/等待时间灵活选择
- **匿名公共历史**：可选保存行程至云端，跨设备查看与分享

## 💡 与纯 LLM 旅行规划的区别

- 纯 LLM 方案（如直接问 ChatGPT）生成的行程"看起来合理"，但常出现景点绕路、营业时间不符、时间估算失真，无法直接执行
- **TravelPal 的行程是"可执行"的方案**：自定义元启发式算法保证时间窗约束与路径最优，LLM 只负责需求理解与自然语言解说——各司其职
- **结果差异**：纯 LLM 给你"一段文字"，TravelPal 给你"精确时间表 + 真实驾车路径 + 可交互地图"

## 🖼️ 效果预览

> （待补充：规划结果页面截图、对话界面截图）

## 🚀 Docker 快速开始

前置条件：Docker、Docker Compose。

```bash
# 1. 克隆
git clone https://github.com/xiaojiune/TravelPal.git
cd TravelPal

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env，填入以下 key（申请方式见下表）

# 3. 一键启动（四服务编排：PostgreSQL + Redis + 后端 + 前端 Nginx）
docker compose up -d
# 首次启动自动完成数据库建表，无需手动初始化

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

前置条件：Python 3.12、Node.js 22、PostgreSQL、Redis。
本地数据库依赖也可通过 `docker compose up -d postgres redis` 快速启动，无需本地安装。

```bash
make install            # 一键安装前后端依赖
cp .env.example .env    # 配置环境变量（本地开发 DATABASE_URL 需改为 postgresql+asyncpg://travelpal:travelpal123@localhost:5432/travelpal）
make serve              # 启动后端（热重载）
make dev                # 启动前端（Vite HMR）
```

完整命令清单见 `make help`。Makefile 统一封装了开发/测试/构建/部署全生命周期命令，降低上手与复现成本。

## 📁 项目结构

```
TravelPal/
├── backend/         Python 后端（FastAPI）
│   ├── agent/       LLM Agent
│   ├── api/         HTTP 路由与 Schema
│   ├── engine/      核心算法（CA / VNS / Clustering）
│   ├── data/        数据加载与数据库模型
│   └── utils/       工具脚本
├── frontend/        Vue 3 前端（Vite + TypeScript）
├── docker/          Docker 构建文件 + nginx 配置
├── docs/            Sphinx 文档站
│   └── ADR/        架构决策记录（ADR-001 ~ ADR-007）
├── tests/           Python 测试
├── docker-compose.yml   四服务编排
└── Makefile              开发命令统一入口
```

## 🏗️ 技术栈

| 层 | 技术 | 用途 |
|---|------|------|
| 后端框架 | Python 3.12 + FastAPI | REST API / SSE 流式服务 |
| 求解引擎 | NumPy + Numba JIT | 多日行程规划（CA 快速预览 / VNS 深度优化） |
| Agent | DeepSeek + BM25 上下文检索 | 对话理解与项目文档问答 |
| 数据库 | PostgreSQL 16 (pgvector) + SQLAlchemy | 历史记录持久化 |
| 缓存 | Redis | 路径规划结果缓存 |
| 地图 | 高德 Web 服务 API + JS API 2.0 | POI 数据查询与 2D 路线可视化 |
| 前端 | Vue 3 + TypeScript + Vite + Pinia | SPA 用户界面 |
| 容器化 | Docker + Docker Compose + Nginx | 四服务一键编排，开箱即用 |

## 📖 相关文档

> **快速导航**：想了解系统架构？看 [`backend.md`](docs/structure/backend.md)；想了解 Agent 怎么工作的？看 [`agent.md`](docs/structure/agent.md)；想了解数据结构？看 [`data.md`](docs/structure/data.md)。
> 项目包含 7 篇架构决策记录（ADR），完整记录技术选型理由与设计权衡过程。

| 文档 | 说明 |
|------|------|
| [`project.md`](docs/structure/project.md) | 项目总览与调用链路 |
| [`backend.md`](docs/structure/backend.md) | 后端架构与数据流 |
| [`frontend.md`](docs/structure/frontend.md) | 前端组件与状态管理 |
| [`agent.md`](docs/structure/agent.md) | LLM Agent 交互流程 |
| [`data.md`](docs/structure/data.md) | 统一数据字典 |
| [`ADR/`](docs/ADR/) | 架构决策记录（ADR-001 ~ ADR-007） |
| [`deploy.md`](docs/deploy.md) | 服务器部署与 HTTPS |

## 许可

Copyright © 2026 xiaojiune. Released under the MIT License.

---

欢迎 Star / Issue / PR 交流。
