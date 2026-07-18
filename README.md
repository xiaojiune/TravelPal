# TravelPal · 旅行伴侣

基于双引擎（CA/VNS）+ LLM Agent 的智能旅行规划系统。

通过对话了解你的喜好，自动生成兼顾路线、时间和景点的行程方案，并在地图上直观呈现。

📖 文档站：<https://xiaojiune.github.io/TravelPal/>

---

## ✨ 核心功能

- **对话式规划**：告诉 Agent 你想去哪、玩几天、什么节奏，边聊边调
- **地图可视化**：每日路线实时绘制在高德地图上，景点标记含到达/离开时间
- **方案选择**：一次生成多组方案，按天数/成本对比挑选，或深度搜索最优解
- **行程调整**：出发前自由修改景点列表和停留时间，重新规划
- **历史分享**：方案保存至云端，分享给朋友或跨设备查看

## 💡 与纯 LLM 旅行规划的区别

- 纯 LLM 方案（如直接问 ChatGPT）生成的行程是"看起来合理"的文本
- **TravelPal 的行程是"可执行"的方案**：自定义元启发式算法保证时间窗约束、避免绕路、支持用户实时调整
- LLM 负责"理解需求 + 解说"，自定义算法负责"数学最优解"——各司其职

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

# 3. 一键启动（PostgreSQL + Redis + 后端 + 前端 Nginx）
docker compose up -d

# 4. 打开 http://localhost
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

```bash
make install            # 一键安装前后端依赖
cp .env.example .env    # 配置环境变量（本地开发 DATABASE_URL 需改为 postgresql+asyncpg://travelpal:travelpal123@localhost:5432/travelpal）
make serve              # 启动后端（热重载）
make dev                # 启动前端（Vite HMR）
```

完整命令清单见 `make help`。

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
| 求解引擎 | NumPy + Numba JIT | 元启发式算法加速 |
| Agent | DeepSeek (OpenAI SDK) + BM25 RAG | 对话理解与文档检索 |
| 数据库 | PostgreSQL 16 (pgvector) + SQLAlchemy | 历史记录持久化 |
| 缓存 | Redis | 路径规划结果缓存 |
| 地图 | 高德 Web 服务 API + JS API 2.0 | POI 数据查询与 2D 路线可视化 |
| 前端 | Vue 3 + TypeScript + Vite + Pinia | SPA 用户界面 |
| 容器化 | Docker + Docker Compose + Nginx | 一键部署与反向代理 |

## 📖 相关文档

> **快速导航**：想了解系统架构？看 [`backend.md`](docs/structure/backend.md)；想了解 Agent 怎么工作的？看 [`agent.md`](docs/structure/agent.md)；想了解数据结构？看 [`data.md`](docs/structure/data.md)。

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

MIT License

---

TravelPal 使用 TSPTW 标准测试集（n20w20 / n60w60 / n100w20 / n200w40）进行算法验证。
