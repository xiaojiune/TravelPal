.PHONY: install build gen-api gen-all sync-check serve mcp-serve celery dev lint format typecheck \
        test check ruff ruff-fix ruff-format pyright \
        dc-up dc-logs dc-ps dc-restart dc-build deploy-up deploy-down \
        dc-migration migrate \
        clean help

# 裸 make 默认显示帮助（避免误触第一个目标 install 引发 npm ci 重装）
.DEFAULT_GOAL := help

# 迁移脚本消息：make dc-migration MESSAGE="xxx" 指定，默认 auto
MESSAGE ?= auto

# ======== 安装构建 ========

install: ## 一键安装前后端依赖
	@echo '==> 安装后端依赖（poetry）'
	.venv/bin/poetry install
	@echo '==> 安装前端依赖（npm ci）'
	cd frontend && npm ci --legacy-peer-deps

build: ## 前端生产构建
	cd frontend && npm run build

gen-api: ## 重新生成前端 API 类型（后端 schema 变更后执行）
	cd frontend && npm run gen:api

gen-all: ## 自动同步所有 __init__.py 的 __all__（增删 import 后执行）
	.venv/bin/python -m backend.utils.sync_all

sync-check: ## 校验 __all__ 与 import 是否一致（dry-run，不一致退出 1）
	.venv/bin/python -m backend.utils.sync_all --check

# ======== 开发 ========

serve: ## 启动后端服务（需要 PostgreSQL + Redis）
	.venv/bin/uvicorn backend.api.server:app --host 0.0.0.0 --port 8000 --reload

mcp-serve: ## 启动 MCP Server（stdio 传输，供外部 AI 助手通过 MCP 调用工具）
	.venv/bin/python -m backend.mcp.server

celery: ## 启动 Celery worker（消费异步规划任务，需 dc-up + serve）
	.venv/bin/celery -A backend.tasks.app worker --loglevel=info --concurrency=1

dev: ## 启动前端开发服务器（Vite HMR）
	cd frontend && npm run dev

# ======== 代码质量 ========

lint: ## 前端 lint 自动修复（ESLint --fix）
	cd frontend && npm run lint:fix

format: ## 前端代码格式化（Prettier）
	cd frontend && npx prettier --write src/

typecheck: ## 前端 TypeScript 类型检查
	cd frontend && npx vue-tsc --noEmit

ruff: ## 后端 Python lint 检查（ruff）
	.venv/bin/ruff check backend/

ruff-fix: ## 后端 Python lint 自动修复
	.venv/bin/ruff check --fix backend/

ruff-format: ## 后端 Python 代码格式化（ruff）
	.venv/bin/ruff format backend/

pyright: ## 后端 Python 类型检查
	.venv/bin/pyright backend/

check: ## 全量检查（推送前/明确要求时使用：格式 + lint + 类型 + 测试 + 一致性）
	@echo '==> ruff format --check（后端格式）'
	.venv/bin/ruff format --check backend/
	@echo '==> ruff check（后端 lint）'
	.venv/bin/ruff check backend/
	@echo '==> pyright（后端类型）'
	.venv/bin/pyright backend/
	@echo '==> pytest（后端测试）'
	.venv/bin/pytest
	@echo '==> poetry check --lock（后端依赖一致性）'
	.venv/bin/poetry check --lock
	@echo '==> sync_all --check（__all__ 同步）'
	.venv/bin/python -m backend.utils.sync_all --check
	@echo '==> npm ci --dry-run（前端依赖一致性）'
	cd frontend && npm ci --dry-run --ignore-scripts --no-audit --no-fund
	@echo '==> eslint（前端）'
	cd frontend && npm run lint
	@echo '==> prettier --check（前端格式）'
	cd frontend && npx prettier --check src/
	@echo '==> vue-tsc（前端类型）'
	cd frontend && npx vue-tsc --noEmit
	@echo '==> OpenAPI 类型同步'
	cd frontend && npm run gen:api && git diff --exit-code -- src/api/types.generated.ts

# ======== 测试 ========
# 串行执行：实测 pytest-xdist 对 numba（@njit 编译按进程重复）+ sklearn（自带多线程）
# 的求解测试无收益甚至更慢。当前规模（<100 点、秒级求解）无并行需求；
# 未来若走 learning-based 求解（GNN/Transformer 学启发式）再考虑 GPU 加速。

test: ## 运行全部 Python 测试
	.venv/bin/pytest

# ======== Docker ========

dc-up: ## 启动基础设施（PostgreSQL + Redis，后台）
	docker compose up -d postgres redis

dc-logs: ## 查看 Docker 日志
	docker compose logs -f

dc-ps: ## 查看 Docker 服务状态
	docker compose ps

dc-restart: ## 重启全部 Docker 服务
	docker compose restart

dc-build: ## 构建全部 Docker 镜像
	docker compose build

deploy-up: ## 全量部署（PostgreSQL + Redis + 后端 + Celery worker + 前端 Nginx）
	docker compose up -d

deploy-down: ## 停止全量部署
	docker compose down

dc-migration: ## 生成数据库迁移脚本（对比 models.py，需 docker compose up -d）；指定消息：make dc-migration MESSAGE="xxx"
	.venv/bin/alembic revision --autogenerate -m "$(MESSAGE)"

migrate: ## 应用数据库迁移到最新版本（需 docker compose up -d）
	.venv/bin/alembic upgrade head

# ======== 工具 ========

clean: ## 清理构建缓存与临时文件
	rm -rf frontend/dist .pytest_cache .ruff_cache frontend/node_modules/.vite
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

help: ## 显示此帮助信息
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | sort | \
	awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'
