.PHONY: help api-install api-dev api-test api-lint api-format web-install web-dev web-build web-lint web-typecheck check

help:
	@echo "Lumen — common commands"
	@echo "  make api-install    install backend deps (into apps/api/.venv)"
	@echo "  make api-dev        run the FastAPI backend on :8000"
	@echo "  make api-test       run the backend test suite"
	@echo "  make api-lint       ruff lint the backend"
	@echo "  make web-install    install frontend deps"
	@echo "  make web-dev        run the Next.js frontend on :3000"
	@echo "  make web-build      production build of the frontend"
	@echo "  make check          lint + typecheck + tests across both apps"

# ---- Backend ----
api-install:
	cd apps/api && python -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt

api-dev:
	cd apps/api && . .venv/bin/activate && uvicorn app.main:app --reload --port 8000

api-test:
	cd apps/api && . .venv/bin/activate && pytest -q

api-lint:
	cd apps/api && . .venv/bin/activate && ruff check app

api-format:
	cd apps/api && . .venv/bin/activate && ruff format app

# ---- Frontend ----
web-install:
	cd apps/web && pnpm install

web-dev:
	cd apps/web && pnpm dev

web-build:
	cd apps/web && pnpm build

web-lint:
	cd apps/web && pnpm lint

web-typecheck:
	cd apps/web && pnpm typecheck

# ---- Combined ----
check: api-lint api-test web-lint web-typecheck web-build
	@echo "All checks passed."
