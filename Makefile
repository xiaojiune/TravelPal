.PHONY: install build gen-api serve serve-nodb dev lint format typecheck \
        test check ruff ruff-fix \
        dc-up dc-up-d dc-logs dc-ps dc-restart dc-build dc-down deploy-up deploy-down \
        clean help

# ======== 安装构建 ========

install: ## 一键安装前后端依赖
	.venv/bin/poetry install && cd frontend && npm ci

build: ## 前端生产构建
	cd frontend && npm run build

gen-api: ## 重新生成前端 API 类型（后端 schema 变更后执行）
	cd frontend && npm run gen:api

# ======== 开发 ========

serve: ## 启动后端服务（需要 PostgreSQL + Redis）
	.venv/bin/uvicorn backend.api.server:app --host 0.0.0.0 --port 8000 --reload

serve-nodb: ## 启动后端服务（跳过数据库，快速联调）
	SKIP_DB=true .venv/bin/uvicorn backend.api.server:app --host 0.0.0.0 --port 8000 --reload

dev: ## 启动前端开发服务器（Vite HMR）
	cd frontend && npm run dev

# ======== 代码质量 ========

lint: ## 前端 lint（ESLint）
	cd frontend && npm run lint

format: ## 前端代码格式化（Prettier）
	cd frontend && npx prettier --write src/

typecheck: ## 前端 TypeScript 类型检查
	cd frontend && npx vue-tsc --noEmit

ruff: ## 后端 Python lint 检查（ruff）
	.venv/bin/ruff check backend/

ruff-fix: ## 后端 Python lint 自动修复
	.venv/bin/ruff check --fix backend/

check: ## 前后端全量检查
	.venv/bin/ruff check backend/ && cd frontend && npm run lint && npx vue-tsc --noEmit

# ======== 测试 ========

test: ## 运行全部 Python 测试
	.venv/bin/pytest

# ======== Docker ========

dc-up: ## 启动基础设施（PostgreSQL + Redis，前台）
	docker compose up postgres redis

dc-up-d: ## 启动基础设施（PostgreSQL + Redis，后台）
	docker compose up -d postgres redis

dc-logs: ## 查看 Docker 日志
	docker compose logs -f

dc-ps: ## 查看 Docker 服务状态
	docker compose ps

dc-restart: ## 重启全部 Docker 服务
	docker compose restart

dc-build: ## 构建全部 Docker 镜像
	docker compose build

dc-down: ## 停止全部 Docker 服务
	docker compose down

deploy-up: ## 全量部署（PostgreSQL + Redis + 后端 + 前端 Nginx）
	docker compose up -d

deploy-down: ## 停止全量部署
	docker compose down

# ======== 工具 ========

clean: ## 清理构建缓存与临时文件
	rm -rf frontend/dist .pytest_cache frontend/node_modules/.vite
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

help: ## 显示此帮助信息
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | sort | \
	awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'
