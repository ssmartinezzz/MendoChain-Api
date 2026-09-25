#!/usr/bin/env bash
# Install and run MendoChain API locally.
#
# Usage: ./setup.sh [command]
#   setup    (default) create .env, start PostgreSQL, install dependencies, run migrations
#   run      setup, then start the development server
#   test     setup, then run the test suite
#   db-stop  stop the PostgreSQL container
set -Eeuo pipefail

cd "$(dirname "$0")"

DB_CONTAINER="mendochain-db"
DB_VOLUME="mendochain-db-data"
DB_IMAGE="postgres:16-alpine"
LOG_FILE=".setup.log"

info() { printf '\033[1;34m==>\033[0m %s\n' "$*"; }
fail() { printf '\033[1;31merror:\033[0m %s\n' "$*" >&2; exit 1; }

on_unexpected_error() {
    printf '\033[1;31merror:\033[0m setup failed at line %s (exit code %s). Full output in %s\n' "$1" "$2" "$LOG_FILE" >&2
}

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
    ensure_env ACTOR_KEYS_SECRET "$(uv run --no-project python -c 'import base64, os; print(base64.urlsafe_b64encode(os.urandom(32)).decode())')"
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

next_free_port() {
    local port
    for port in $(seq $(($1 + 1)) $(($1 + 50))); do
        if ! port_in_use "$port"; then
            printf '%s' "$port"
            return
        fi
    done
}

port_conflict() {
    local port="$1" suggestion
    suggestion="$(next_free_port "$port")"
    suggestion="${suggestion:-<free port>}"
    if docker inspect "$DB_CONTAINER" >/dev/null 2>&1; then
        # The existing container is bound to this port, so moving it also means recreating it.
        fail "Port $port is taken by another process, but container '$DB_CONTAINER' needs it. Stop that process and run ./setup.sh again, or move the database: set DB_PORT=$suggestion in .env, run docker rm -f $DB_CONTAINER (data is kept in volume $DB_VOLUME), then ./setup.sh again."
    fi
    fail "Port $port is already in use by another process. Set DB_PORT=$suggestion in .env and run ./setup.sh again."
}

container_port() {
    docker inspect -f '{{with index .HostConfig.PortBindings "5432/tcp"}}{{(index . 0).HostPort}}{{end}}' "$DB_CONTAINER"
}

docker_or_port_conflict() {
    # Runs a docker command; a port clash becomes a clear message instead of a raw docker error.
    local port="$1" output
    shift
    if ! output="$("$@" 2>&1)"; then
        echo "$output" >> "$LOG_FILE"
        if grep -qiE 'port is already allocated|address already in use' <<<"$output"; then
            port_conflict "$port"
        fi
        fail "Docker could not start PostgreSQL: $output"
    fi
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

    if docker inspect "$DB_CONTAINER" >/dev/null 2>&1; then
        local bound
        bound="$(container_port)"
        if [[ "$bound" != "$port" ]]; then
            fail "Container '$DB_CONTAINER' listens on port $bound but .env has DB_PORT=$port. Set DB_PORT=$bound in .env, or recreate the container on the new port with: docker rm -f $DB_CONTAINER (data is kept in volume $DB_VOLUME)."
        fi
    fi

    if [[ "$(docker inspect -f '{{.State.Running}}' "$DB_CONTAINER" 2>/dev/null || true)" == "true" ]]; then
        if [[ -z "$(docker port "$DB_CONTAINER" 5432/tcp 2>/dev/null)" ]]; then
            # Docker can bring a container up without its port mapping after a failed start; only recreating fixes it.
            info "Container '$DB_CONTAINER' is running without its port mapping; recreating it (data is kept in volume $DB_VOLUME)"
            docker rm -f "$DB_CONTAINER" >/dev/null
            create_container "$port"
        else
            info "PostgreSQL container '$DB_CONTAINER' already running on port $port"
        fi
    elif docker inspect "$DB_CONTAINER" >/dev/null 2>&1; then
        # Check before starting: a start that fails on a busy port can leave the container without its mapping.
        if port_in_use "$port"; then
            port_conflict "$port"
        fi
        info "Starting PostgreSQL container '$DB_CONTAINER' on port $port"
        docker_or_port_conflict "$port" docker start "$DB_CONTAINER"
    else
        if port_in_use "$port"; then
            port_conflict "$port"
        fi
        create_container "$port"
    fi

    info "Waiting for PostgreSQL"
    for _ in $(seq 1 30); do
        if docker exec "$DB_CONTAINER" pg_isready -q -U "$(read_env DB_USER)" && port_in_use "$port"; then
            return
        fi
        sleep 1
    done
    fail "PostgreSQL is not reachable on localhost:$port after 30 seconds. Check: docker logs $DB_CONTAINER, or recreate it with docker rm -f $DB_CONTAINER (data is kept in volume $DB_VOLUME)."
}

create_container() {
    local port="$1"
    info "Creating PostgreSQL container '$DB_CONTAINER' on port $port"
    docker_or_port_conflict "$port" docker run -d --name "$DB_CONTAINER" \
        -e POSTGRES_DB="$(read_env DB_NAME)" \
        -e POSTGRES_USER="$(read_env DB_USER)" \
        -e POSTGRES_PASSWORD="$(read_env DB_PASSWORD)" \
        -p "$port:5432" \
        -v "$DB_VOLUME:/var/lib/postgresql/data" \
        "$DB_IMAGE"
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

run_setup() {
    # Setup output goes to the terminal and to $LOG_FILE; the server and tests only to the terminal.
    exec 3>&1 4>&2
    : > "$LOG_FILE"
    exec > >(tee -a "$LOG_FILE") 2>&1
    trap 'on_unexpected_error $LINENO $?' ERR
    setup
    trap - ERR
    exec 1>&3 2>&4 3>&- 4>&-
}

case "${1:-setup}" in
    setup)
        run_setup
        ;;
    run)
        run_setup
        uv run python manage.py runserver
        ;;
    test)
        run_setup
        LOG_LEVEL=WARNING uv run python manage.py test
        ;;
    db-stop)
        docker stop "$DB_CONTAINER" >/dev/null && info "Stopped '$DB_CONTAINER'"
        ;;
    *)
        fail "Unknown command '$1'. Use: setup | run | test | db-stop"
        ;;
esac
