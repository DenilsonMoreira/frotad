.PHONY: infra-up infra-down api-test api-lint web-install web-lint web-typecheck check

infra-up:
	docker compose up -d postgres redis minio

infra-down:
	docker compose down

api-test:
	cd apps/api && pytest

api-lint:
	cd apps/api && ruff check .

web-install:
	cd apps/web && npm install

web-lint:
	cd apps/web && npm run lint

web-typecheck:
	cd apps/web && npm run typecheck

check: api-lint api-test web-lint web-typecheck
