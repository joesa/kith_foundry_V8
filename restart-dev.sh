#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUN_DIR="$ROOT_DIR/.run"
LOG_DIR="$ROOT_DIR/.logs"

BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"
INNGEST_PORT="${INNGEST_PORT:-8288}"
PREFERRED_CONDA_ENV="${KITH_CONDA_ENV:-kith_venv}"
FALLBACK_CONDA_ENV="${KITH_FALLBACK_CONDA_ENV:-base}"
CONDA_EXE="${KITH_CONDA_EXE:-/c/Users/treas/miniconda3/Scripts/conda.exe}"
CONDA_ENVS_DIR="${KITH_CONDA_ENVS_DIR:-/c/Users/treas/miniconda3/envs}"
USE_INNGEST_DEV_SERVER="${KITH_USE_INNGEST_DEV_SERVER:-1}"
FLYCTL_EXE="${KITH_FLYCTL_EXE:-$(command -v flyctl 2>/dev/null || true)}"

BACKEND_PID_FILE="$RUN_DIR/backend.pid"
FRONTEND_PID_FILE="$RUN_DIR/frontend.pid"
INNGEST_PID_FILE="$RUN_DIR/inngest.pid"
BACKEND_LOG="$LOG_DIR/backend.log"
FRONTEND_LOG="$LOG_DIR/frontend.log"
INNGEST_LOG="$LOG_DIR/inngest.log"

ACTION="restart"
WSL_SHUTDOWN=0

usage() {
  cat <<'EOF'
Usage: ./restart-dev.sh [start|stop|restart|status] [--wsl-shutdown]

Commands:
  start           Start backend and frontend
  stop            Stop backend and frontend
  restart         Stop then start backend and frontend
  status          Show current status and recent log locations

Options:
  --wsl-shutdown  If a port listener survives normal stop, also run `wsl --shutdown`

Environment overrides:
  KITH_CONDA_EXE=/c/Users/treas/miniconda3/Scripts/conda.exe
  KITH_CONDA_ENVS_DIR=/c/Users/treas/miniconda3/envs
  KITH_CONDA_ENV=kith_venv
  KITH_FALLBACK_CONDA_ENV=base
  KITH_USE_INNGEST_DEV_SERVER=1
  KITH_FLYCTL_EXE=/c/Users/treas/.fly/bin/flyctl.exe
  BACKEND_PORT=8000
  FRONTEND_PORT=5173
  INNGEST_PORT=8288
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    start|stop|restart|status)
      ACTION="$1"
      shift
      ;;
    --wsl-shutdown)
      WSL_SHUTDOWN=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage
      exit 1
      ;;
  esac
done

mkdir -p "$RUN_DIR" "$LOG_DIR"

log() {
  printf '[kith-dev] %s\n' "$*"
}

port_listener_count() {
  local port="$1"
  powershell -NoProfile -Command "try { (@(Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue)).Count } catch { 0 }" | tr -d '\r'
}

stop_port_listeners() {
  local port="$1"
  powershell -NoProfile -Command "try { \$listeners = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue; foreach (\$listener in \$listeners) { try { Stop-Process -Id \$listener.OwningProcess -Force -ErrorAction Stop } catch {} } } catch {}" >/dev/null || true

  sleep 2

  if [[ "$(port_listener_count "$port")" != "0" && "$WSL_SHUTDOWN" == "1" ]]; then
    if command -v wsl >/dev/null 2>&1; then
      log "Port $port still busy; running wsl --shutdown"
      wsl --shutdown || true
      sleep 2
    fi
  fi
}

kill_pid_file() {
  local pid_file="$1"
  local label="$2"
  if [[ -f "$pid_file" ]]; then
    local pid
    pid="$(tr -d '\r\n' < "$pid_file" || true)"
    if [[ -n "${pid:-}" ]]; then
      kill "$pid" >/dev/null 2>&1 || true
      powershell -NoProfile -Command "try { Stop-Process -Id $pid -Force -ErrorAction Stop } catch {}" >/dev/null || true
    fi
    rm -f "$pid_file"
    log "Stopped $label from pid file"
  fi
}

resolve_conda_env() {
  if [[ -d "$CONDA_ENVS_DIR/$PREFERRED_CONDA_ENV" ]]; then
    echo "$PREFERRED_CONDA_ENV"
    return
  fi

  if [[ ! -x "$CONDA_EXE" ]]; then
    echo "$FALLBACK_CONDA_ENV"
    return
  fi

  local envs
  envs="$("$CONDA_EXE" env list 2>/dev/null | tr -d '\r' | awk 'NR > 2 && $1 != "" { print $1 }')"
  if printf '%s\n' "$envs" | awk -v target="$PREFERRED_CONDA_ENV" '$1 == target { found=1 } END { exit(found ? 0 : 1) }'; then
    echo "$PREFERRED_CONDA_ENV"
  else
    echo "$FALLBACK_CONDA_ENV"
  fi
}

resolve_fly_api_token() {
  if [[ -n "${FLY_API_TOKEN:-}" ]]; then
    printf '%s\n' "$FLY_API_TOKEN"
    return
  fi

  if [[ -n "${FLYCTL_EXE:-}" && -x "${FLYCTL_EXE:-}" ]]; then
    local token
    token="$("$FLYCTL_EXE" auth token 2>/dev/null | tr -d '\r' | tail -n 1)"
    if [[ -n "$token" ]]; then
      printf '%s\n' "$token"
      return
    fi
  fi

  printf '%s\n' ""
}

wait_for_url() {
  local url="$1"
  local label="$2"
  local attempts="${3:-30}"
  local delay="${4:-1}"

  for ((i=1; i<=attempts; i++)); do
    if curl -fsS "$url" >/dev/null 2>&1; then
      log "$label is ready at $url"
      return 0
    fi
    sleep "$delay"
  done

  log "$label did not become ready at $url"
  return 1
}

start_backend() {
  local env_name
  local fly_api_token
  env_name="$(resolve_conda_env)"
  fly_api_token="$(resolve_fly_api_token)"
  log "Starting backend with conda env: $env_name"
  (
    cd "$ROOT_DIR"
    if [[ -n "$fly_api_token" ]]; then
      nohup env FLY_API_TOKEN="$fly_api_token" "$CONDA_EXE" run -n "$env_name" python backend/main.py > "$BACKEND_LOG" 2>&1 &
    else
      nohup "$CONDA_EXE" run -n "$env_name" python backend/main.py > "$BACKEND_LOG" 2>&1 &
    fi
    echo $! > "$BACKEND_PID_FILE"
  )
}

start_frontend() {
  log "Starting frontend with Vite"
  (
    cd "$ROOT_DIR/frontend"
    nohup node node_modules/vite/bin/vite.js --host 0.0.0.0 > "$FRONTEND_LOG" 2>&1 &
    echo $! > "$FRONTEND_PID_FILE"
  )
}

start_inngest() {
  if [[ "$USE_INNGEST_DEV_SERVER" != "1" ]]; then
    log "Skipping Inngest dev server"
    return
  fi

  log "Starting Inngest dev server"
  (
    cd "$ROOT_DIR"
    nohup npx --yes --ignore-scripts=false inngest-cli@latest dev -u "http://localhost:$BACKEND_PORT/api/inngest" > "$INNGEST_LOG" 2>&1 &
    echo $! > "$INNGEST_PID_FILE"
  )
}

stop_services() {
  log "Stopping backend, frontend, and Inngest"
  kill_pid_file "$BACKEND_PID_FILE" "backend"
  kill_pid_file "$FRONTEND_PID_FILE" "frontend"
  kill_pid_file "$INNGEST_PID_FILE" "inngest"

  stop_port_listeners "$BACKEND_PORT"
  stop_port_listeners "$FRONTEND_PORT"
  stop_port_listeners "$INNGEST_PORT"

  local backend_count frontend_count inngest_count
  backend_count="$(port_listener_count "$BACKEND_PORT")"
  frontend_count="$(port_listener_count "$FRONTEND_PORT")"
  inngest_count="$(port_listener_count "$INNGEST_PORT")"

  if [[ "$backend_count" != "0" || "$frontend_count" != "0" || "$inngest_count" != "0" ]]; then
    log "Warning: backend listeners=$backend_count frontend listeners=$frontend_count inngest listeners=$inngest_count"
  else
    log "Ports $BACKEND_PORT, $FRONTEND_PORT, and $INNGEST_PORT are clear"
  fi
}

status_services() {
  local backend_count frontend_count inngest_count
  backend_count="$(port_listener_count "$BACKEND_PORT")"
  frontend_count="$(port_listener_count "$FRONTEND_PORT")"
  inngest_count="$(port_listener_count "$INNGEST_PORT")"

  log "Backend listeners on $BACKEND_PORT: $backend_count"
  log "Frontend listeners on $FRONTEND_PORT: $frontend_count"
  log "Inngest listeners on $INNGEST_PORT: $inngest_count"
  log "Backend log: $BACKEND_LOG"
  log "Frontend log: $FRONTEND_LOG"
  log "Inngest log: $INNGEST_LOG"
}

start_services() {
  stop_port_listeners "$BACKEND_PORT"
  stop_port_listeners "$FRONTEND_PORT"
  stop_port_listeners "$INNGEST_PORT"

  start_backend
  wait_for_url "http://127.0.0.1:$BACKEND_PORT/docs" "Backend" 45 1
  start_inngest
  if [[ "$USE_INNGEST_DEV_SERVER" == "1" ]]; then
    wait_for_url "http://127.0.0.1:$INNGEST_PORT/" "Inngest" 45 1
  fi
  start_frontend
  wait_for_url "http://127.0.0.1:$FRONTEND_PORT/" "Frontend" 45 1

  log "Restart complete"
  status_services
}

case "$ACTION" in
  start)
    start_services
    ;;
  stop)
    stop_services
    ;;
  restart)
    stop_services
    start_services
    ;;
  status)
    status_services
    ;;
esac
