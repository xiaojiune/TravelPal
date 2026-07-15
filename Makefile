.PHONY: dev serve lint build test clean dc-up dc-down dc-logs dc-ps

dev:
	cd frontend && npm run dev

serve:
	.venv/bin/python -m backend.api.server --reload

lint:
	cd frontend && npm run lint

build:
	cd frontend && npm run build

test:
	.venv/bin/pytest

dc-up:
	docker compose up -d

dc-down:
	docker compose down

dc-logs:
	docker compose logs -f

dc-ps:
	docker compose ps

clean:
	rm -rf frontend/dist .pytest_cache frontend/node_modules/.vite
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
