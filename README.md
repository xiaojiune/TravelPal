# TravelPal 旅行伴侣

基于双引擎（CA/VNS）+ LLM Agent 的智能旅行规划系统。

📖 文档站：https://xiaojiune.github.io/TravelPal/

## 技术栈

### 后端
- **语言**: Python 3.12
- **框架**: FastAPI + Uvicorn
- **引擎**: NumPy, Numba (JIT), scikit-learn
- **Agent**: OpenAI SDK (DeepSeek), ChromaDB
- **数据**: SQLAlchemy + asyncpg (PostgreSQL)
- **API**: 高德地图 (驾车路径规划/POI 搜索)

### 前端
- **框架**: Vue 3 + TypeScript + Vite
- **状态管理**: Pinia
- **路由**: Vue Router 4
- **地图**: 高德地图 JS API 2.0
- **HTTP**: Axios
- **代码风格**: ESLint + Prettier
- **类型工具**: openapi-typescript (自动生成 API 类型)

### 文档
- **文档站**: Sphinx + Read the Docs 主题
- **API 文档**: Redoc (openapi.json)
- **CI/CD**: GitHub Actions (CI + GitHub Pages)

## 项目结构

```
backend/          # 后端 Python 代码
├── agent/        # LLM Agent (Planner / Commentator)
├── api/          # FastAPI 路由与 Schema
├── data/         # 高德 API 数据加载
├── engine/       # 核心算法 (CA/VNS/Clustering)
├── tools/        # 工具脚本 (sync_all, gen_openapi)
└── types.py      # 共享 TypedDict
frontend/         # Vue 3 前端
├── src/
│   ├── pages/    # 页面组件
│   ├── components/ # 通用组件
│   ├── stores/   # Pinia 状态
│   ├── services/ # API 封装
│   └── composables/ # 可复用逻辑
└── ...
docs/             # Sphinx 文档站源码
tests/            # pytest 测试
```

## 快速开始

```bash
# 安装后端依赖
poetry install

# 安装前端依赖
cd frontend && npm install

# 配置环境变量（高德 API Key + LLM Key）
cp .env.example .env

# 启动后端（开发模式，默认启用热重载）
serve

# 或手动启动（无热重载）
python -m backend.api.server

# 启动前端开发服务器（新终端）
cd frontend && npm run dev
```
