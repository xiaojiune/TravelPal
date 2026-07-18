.PHONY: dev serve serve-nodb lint typecheck build test clean \
        install format gen-api \
        dc-up dc-up-d dc-down dc-logs dc-ps dc-build dc-restart help

dev: ## 启动前端开发服务器（Vite HMR）
	cd frontend && npm run dev

serve: ## 启动后端服务（需要 PostgreSQL + Redis）
	.venv/bin/uvicorn backend.api.server:app --host 0.0.0.0 --port 8000 --reload

serve-nodb: ## 启动后端服务（跳过数据库，快速联调）
	SKIP_DB=true .venv/bin/uvicorn backend.api.server:app --host 0.0.0.0 --port 8000 --reload

lint: ## 前端 lint（ESLint）
	cd frontend && npm run lint

typecheck: ## 前端 TypeScript 类型检查
	cd frontend && npx vue-tsc --noEmit

build: ## 前端生产构建
	cd frontend && npm run build

test: ## 运行全部 Python 测试
	.venv/bin/pytest

install: ## 一键安装前后端依赖
	.venv/bin/poetry install && cd frontend && npm ci

format: ## 前端代码格式化（Prettier）
	cd frontend && npx prettier --write src/

gen-api: ## 重新生成前端 API 类型（后端 schema 变更后执行）
	cd frontend && npm run gen:api

dc-up: ## 启动全部 Docker 服务（前台）
	docker compose up

dc-up-d: ## 启动全部 Docker 服务（后台）
	docker compose up -d

dc-down: ## 停止全部 Docker 服务
	docker compose down

dc-logs: ## 查看 Docker 日志
	docker compose logs -f

dc-ps: ## 查看 Docker 服务状态
	docker compose ps

dc-build: ## 构建全部 Docker 镜像
	docker compose build

dc-restart: ## 重启全部 Docker 服务
	docker compose restart

clean: ## 清理构建缓存与临时文件
	rm -rf frontend/dist .pytest_cache frontend/node_modules/.vite
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

help: ## 显示此帮助信息
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | sort | \
	awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'
