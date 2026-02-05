SERVICE=api

.PHONY: all clean
all: dev
clean: down

# --- Alembic Helpers ---
.PHONY: migration migrate rollback downgrade history current

# Create a new migration
# Usage: make migration msg="your message here"
migration:
	@test "$(msg)" || (echo "❌ msg is required. Usage: make migration msg='your message'"; exit 1)
	docker compose exec $(SERVICE) alembic revision --autogenerate -m "$(msg)"

# Apply all pending migrations
migrate:
	docker compose exec $(SERVICE) alembic upgrade head

# Rollback the last migration
rollback:
	docker compose exec $(SERVICE) alembic downgrade -1

# Rollback to a specific revision
# Usage: make downgrade rev=<revision_id>
downgrade:
	@test "$(rev)" || (echo "❌ rev is required. Usage: make downgrade rev=<revision_id>"; exit 1)
	docker compose exec $(SERVICE) alembic downgrade $(rev)

# Show migration history
history:
	docker compose exec $(SERVICE) alembic history

# Show current DB revision
current:
	docker compose exec $(SERVICE) alembic current


# --- Redis Helpers ---

.PHONY: redis redis-flush redis-info

# Open Redis CLI
redis:
	docker compose exec redis redis-cli

# Flush current Redis DB (DEV ONLY)
redis-flush:
	docker compose exec redis redis-cli FLUSHDB

# Show Redis info
redis-info:
	docker compose exec redis redis-cli INFO


# --- PostgreSQL Helpers ---

.PHONY: psql db-info db-reset

# Open Postgres psql shell
psql:
	docker compose exec postgres psql -U postgres -d smartvault

# Show Postgres version / connection info
db-info:
	docker compose exec postgres psql -U postgres -d smartvault -c "SELECT version();"

# Reset database (DEV ONLY)
db-reset:
	docker compose exec postgres psql -U postgres -d smartvault -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
	docker compose exec api alembic upgrade head

# --- Daily Dev Workflow ---

.PHONY: up down stop restart logs test dev reset

# Build + start all services
up:
	docker compose up -d --build
	docker compose ps

# Stop services (keeps containers/data)
stop:
	docker compose stop

# Stop + remove containers (keeps volumes/data unless -v)
down:
	docker compose down

# Restart all services
restart:
	docker compose restart
	docker compose ps

# Tail API logs
logs:
	docker compose logs -f $(SERVICE)

# Run tests inside the API container
test:
	docker compose exec $(SERVICE) pytest -q

# One-command dev bootstrap: up -> migrate -> show status
dev: up migrate current db-info redis-info

# DEV ONLY: reset DB + flush Redis + re-run migrations
reset: db-reset redis-flush migrate current


# --- Unit Test Helpers ---

.PHONY: test-vv test-api test-app test-k

test-vv:
	docker compose exec api pytest -vv

test-api:
	docker compose exec api pytest app/tests/api -q

test-app:
	docker compose exec api pytest app/tests/application -q

# Usage: make test-k k=create_user
test-k:
	@test "$(k)" || (echo "❌ k is required. Usage: make test-k k='pattern'"; exit 1)
	docker compose exec api pytest -k "$(k)" -q

.PHONY: install
install:
	docker compose exec $(SERVICE) pip install -r requirements.txt