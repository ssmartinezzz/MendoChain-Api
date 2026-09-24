#!/usr/bin/env bash
# Install and run MendoChain API locally.
#
# Usage: ./setup.sh [command]
#   setup    (default) create .env, start PostgreSQL, install dependencies, run migrations
#   run      setup, then start the development server
#   test     setup, then run the test suite
#   db-stop  stop the PostgreSQL container
set -euo pipefail

cd "$(dirname "$0")"

DB_CONTAINER="mendochain-db"
DB_VOLUME="mendochain-db-data"
DB_IMAGE="postgres:16-alpine"

info() { printf '\033[1;34m==>\033[0m %s\n' "$*"; }
fail() { printf '\033[1;31merror:\033[0m %s\n' "$*" >&2; exit 1; }

# --- .env -------------------------------------------------------------------

read_env() {
    # Last KEY=value in .env, without surrounding quotes. Empty when missing.
    local value
    value="$(grep -E "^$1=" .env 2>/dev/null | tail -n 1 | cut -d= -f2- || true)"
    value="${value%\"}"; value="${value#\"}"
    value="${value%\'}"; value="${value#\'}"
    printf '%s' "$value"
}

ensure_env() {
    # Set KEY only when it is missing or empty, so existing values are never overwritten.
    local key="$1" value="$2"
    if [[ -n "$(read_env "$key")" ]]; then
        return
    fi
    if grep -qE "^$key=" .env; then
        sed -i.bak "s|^$key=.*|$key=$value|" .env && rm -f .env.bak
    else
        printf '%s=%s\n' "$key" "$value" >> .env
    fi
}

prepare_env() {
    if [[ ! -f .env ]]; then
        if [[ -f .env.example ]]; then
            info "Creating .env from .env.example"
            cp .env.example .env
        else
            info "Creating .env"
            touch .env
        fi
    fi
    ensure_env SECRET_KEY "$(uv run --no-project python -c 'import secrets; print(secrets.token_urlsafe(50))')"
    ensure_env DEBUG true
    ensure_env ALLOWED_HOSTS localhost,127.0.0.1
    ensure_env DB_NAME mendochain
    ensure_env DB_USER mendochain
    ensure_env DB_PASSWORD mendochain
    ensure_env DB_HOST localhost
    ensure_env DB_PORT 5432
}

# --- PostgreSQL -------------------------------------------------------------

port_in_use() {
    (exec 3<>"/dev/tcp/127.0.0.1/$1") 2>/dev/null
}

start_database() {
    if [[ -n "$(read_env DATABASE_URL)" ]]; then
        info "DATABASE_URL is set; skipping the local PostgreSQL container"
        return
    fi
    local host port
    host="$(read_env DB_HOST)"
    port="$(read_env DB_PORT)"
    if [[ "$host" != "localhost" && "$host" != "127.0.0.1" ]]; then
        info "DB_HOST is $host; skipping the local PostgreSQL container"
        return
    fi

    command -v docker >/dev/null || fail "Docker is required for the local database. Install it or set DATABASE_URL in .env."

    if [[ "$(docker inspect -f '{{.State.Running}}' "$DB_CONTAINER" 2>/dev/null || true)" == "true" ]]; then
        info "PostgreSQL container '$DB_CONTAINER' already running"
    elif docker inspect "$DB_CONTAINER" >/dev/null 2>&1; then
        info "Starting PostgreSQL container '$DB_CONTAINER'"
        docker start "$DB_CONTAINER" >/dev/null
    else
        if port_in_use "$port"; then
            fail "Port $port is already in use. Set another DB_PORT in .env (e.g. DB_PORT=5433) and run again."
        fi
        info "Creating PostgreSQL container '$DB_CONTAINER' on port $port"
        docker run -d --name "$DB_CONTAINER" \
            -e POSTGRES_DB="$(read_env DB_NAME)" \
            -e POSTGRES_USER="$(read_env DB_USER)" \
            -e POSTGRES_PASSWORD="$(read_env DB_PASSWORD)" \
            -p "$port:5432" \
            -v "$DB_VOLUME:/var/lib/postgresql/data" \
            "$DB_IMAGE" >/dev/null
    fi

    info "Waiting for PostgreSQL"
    for _ in $(seq 1 30); do
        if docker exec "$DB_CONTAINER" pg_isready -q -U "$(read_env DB_USER)"; then
            return
        fi
        sleep 1
    done
    fail "PostgreSQL did not become ready in 30 seconds. Check: docker logs $DB_CONTAINER"
}

# --- Commands ---------------------------------------------------------------

setup() {
    command -v uv >/dev/null || fail "uv is required. Install it with: curl -LsSf https://astral.sh/uv/install.sh | sh"
    prepare_env
    start_database
    info "Installing Python and dependencies with uv"
    uv sync --locked
    info "Applying migrations"
    uv run python manage.py migrate
    info "Collecting static files"
    uv run python manage.py collectstatic --noinput -v0
    info "Ready. Start the server with: ./setup.sh run"
}

case "${1:-setup}" in
    setup)
        setup
        ;;
    run)
        setup
        uv run python manage.py runserver
        ;;
    test)
        setup
        LOG_LEVEL=WARNING uv run python manage.py test
        ;;
    db-stop)
        docker stop "$DB_CONTAINER" >/dev/null && info "Stopped '$DB_CONTAINER'"
        ;;
    *)
        fail "Unknown command '$1'. Use: setup | run | test | db-stop"
        ;;
esac
