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
CONDA_EXE="${KITH_CONDA_EXE:-$(command -v conda 2>/dev/null || true)}"
# Auto-detect miniconda3/anaconda3 under $HOME; fall back to .conda/envs
if [[ -n "${KITH_CONDA_ENVS_DIR:-}" ]]; then
  CONDA_ENVS_DIR="$KITH_CONDA_ENVS_DIR"
elif [[ -d "${HOME}/miniconda3/envs" ]]; then
  CONDA_ENVS_DIR="${HOME}/miniconda3/envs"
elif [[ -d "${HOME}/anaconda3/envs" ]]; then
  CONDA_ENVS_DIR="${HOME}/anaconda3/envs"
else
  CONDA_ENVS_DIR="${HOME}/.conda/envs"
fi
BACKEND_PYTHON_EXE="${KITH_BACKEND_PYTHON:-${CONDA_ENVS_DIR}/${PREFERRED_CONDA_ENV}/bin/python}"
USE_INNGEST_DEV_SERVER="${KITH_USE_INNGEST_DEV_SERVER:-1}"
REDIS_PORT="${REDIS_PORT:-6379}"
FLYCTL_EXE="${KITH_FLYCTL_EXE:-$(command -v flyctl 2>/dev/null || echo '/home/joe/.fly/bin/flyctl')}"
REDIS_DB_NAME="${KITH_REDIS_DB_NAME:-kith-redis}"
REDIS_SERVER_EXE="${KITH_REDIS_SERVER_EXE:-}"  # auto-detected below if empty

# Auto-detect redis-server in conda env or PATH
if [[ -z "$REDIS_SERVER_EXE" ]]; then
  if [[ -x "${CONDA_ENVS_DIR}/${PREFERRED_CONDA_ENV}/bin/redis-server" ]]; then
    REDIS_SERVER_EXE="${CONDA_ENVS_DIR}/${PREFERRED_CONDA_ENV}/bin/redis-server"
  else
    REDIS_SERVER_EXE="$(command -v redis-server 2>/dev/null || true)"
  fi
fi

BACKEND_PID_FILE="$RUN_DIR/backend.pid"
FRONTEND_PID_FILE="$RUN_DIR/frontend.pid"
INNGEST_PID_FILE="$RUN_DIR/inngest.pid"
REDIS_PID_FILE="$RUN_DIR/redis-proxy.pid"
BACKEND_LOG="$LOG_DIR/backend.log"
FRONTEND_LOG="$LOG_DIR/frontend.log"
INNGEST_LOG="$LOG_DIR/inngest.log"
REDIS_LOG="$LOG_DIR/redis-proxy.log"

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
  KITH_REDIS_DB_NAME=kith-redis
  REDIS_PORT=6379
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

get_port_listener_pids() {
  local port="$1"
  local output=""

  if command -v lsof >/dev/null 2>&1; then
    output="$(lsof -t -iTCP:"$port" -sTCP:LISTEN -Pn 2>/dev/null | sort -u || true)"
    printf '%s\n' "$output" | sed '/^$/d'
    return
  fi

  if command -v fuser >/dev/null 2>&1; then
    output="$(fuser -n tcp "$port" 2>/dev/null | tr ' ' '\n' | sed '/^$/d' | sort -u || true)"
    printf '%s\n' "$output" | sed '/^$/d'
    return
  fi

  if command -v ss >/dev/null 2>&1; then
    output="$(ss -ltnp 2>/dev/null | awk -v port=":$port" '
      $4 ~ port {
        while (match($0, /pid=[0-9]+/)) {
          pid = substr($0, RSTART + 4, RLENGTH - 4)
          print pid
          $0 = substr($0, RSTART + RLENGTH)
        }
      }
    ' | sort -u || true)"
    printf '%s\n' "$output" | sed '/^$/d'
    return
  fi

  if command -v netstat >/dev/null 2>&1; then
    output="$(netstat -ltnp 2>/dev/null | awk -v port=":$port" '$4 ~ port { sub(".*/","",$7); if ($7 != "-") print $7 }' | sort -u || true)"
    printf '%s\n' "$output" | sed '/^$/d'
  fi
}

port_listener_count() {
  local port="$1"
  if command -v powershell >/dev/null 2>&1; then
    powershell -NoProfile -Command "try { (@(Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue)).Count } catch { 0 }" | tr -d '\r'
    return
  fi

  # Linux / macOS fallback: prefer ss, then lsof, then netstat
  if command -v ss >/dev/null 2>&1; then
    ss -ltn "sport = :$port" 2>/dev/null | tail -n +2 | wc -l | tr -d ' '
  elif command -v lsof >/dev/null 2>&1; then
    lsof -iTCP:"$port" -sTCP:LISTEN -Pn 2>/dev/null | tail -n +2 | wc -l | tr -d ' '
  else
    netstat -ltn 2>/dev/null | grep -c ":$port[[:space:]]" || true
  fi
}

stop_port_listeners() {
  local port="$1"
  if command -v powershell >/dev/null 2>&1; then
    powershell -NoProfile -Command "try { \$listeners = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue; foreach (\$listener in \$listeners) { try { Stop-Process -Id \$listener.OwningProcess -Force -ErrorAction Stop } catch {} } } catch {}" >/dev/null || true
  else
    local pids
    pids="$(get_port_listener_pids "$port")"
    if [[ -n "$pids" ]]; then
      for pid in $pids; do
        pkill -TERM -P "$pid" >/dev/null 2>&1 || true
        kill -TERM "$pid" >/dev/null 2>&1 || true
      done
      sleep 2
      for pid in $pids; do
        pkill -KILL -P "$pid" >/dev/null 2>&1 || true
        kill -KILL "$pid" >/dev/null 2>&1 || true
      done
    fi
  fi

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
      # Try POSIX signals first, then fallback to PowerShell if available
      pkill -TERM -P "$pid" >/dev/null 2>&1 || true
      kill "$pid" >/dev/null 2>&1 || true
      if command -v powershell >/dev/null 2>&1; then
        powershell -NoProfile -Command "try { Stop-Process -Id $pid -Force -ErrorAction Stop } catch {}" >/dev/null || true
      else
        sleep 1
        pkill -KILL -P "$pid" >/dev/null 2>&1 || true
        kill -0 "$pid" >/dev/null 2>&1 && kill -TERM "$pid" >/dev/null 2>&1 || true
        sleep 1
        kill -0 "$pid" >/dev/null 2>&1 && kill -KILL "$pid" >/dev/null 2>&1 || true
      fi
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

resolve_backend_python() {
  if [[ -x "$BACKEND_PYTHON_EXE" ]]; then
    printf '%s\n' "$BACKEND_PYTHON_EXE"
    return
  fi

  if [[ -d "$CONDA_ENVS_DIR/$PREFERRED_CONDA_ENV" && -x "$CONDA_ENVS_DIR/$PREFERRED_CONDA_ENV/bin/python" ]]; then
    printf '%s\n' "$CONDA_ENVS_DIR/$PREFERRED_CONDA_ENV/bin/python"
    return
  fi

  if [[ -x "${CONDA_EXE:-}" ]]; then
    printf '%s\n' "$CONDA_EXE run -n $(resolve_conda_env) python"
    return
  fi

  command -v python
}

wait_for_url() {
  local url="$1"
  local label="$2"
  local attempts="${3:-30}"
  local delay="${4:-1}"
  local log_file="${5:-}"

  for ((i=1; i<=attempts; i++)); do
    if curl -fsS "$url" >/dev/null 2>&1; then
      log "$label is ready at $url"
      return 0
    fi
    sleep "$delay"
  done

  log "WARNING: $label did not become ready at $url"
  if [[ -n "$log_file" && -f "$log_file" ]]; then
    log "Last 20 lines of $log_file:"
    tail -n 20 "$log_file" | sed 's/^/  /'
  fi
  return 0
}

start_backend() {
  local env_name
  local fly_api_token
  local backend_python
  env_name="$(resolve_conda_env)"
  fly_api_token="$(resolve_fly_api_token)"
  backend_python="$(resolve_backend_python)"
  log "Starting backend with conda env: $env_name"
  (
    cd "$ROOT_DIR/backend"
    if [[ -n "$fly_api_token" ]]; then
      if [[ "$backend_python" == *" run -n "* ]]; then
        nohup env PYTHONPATH=. FLY_API_TOKEN="$fly_api_token" $backend_python -m uvicorn main:app --host 0.0.0.0 --port "$BACKEND_PORT" > "$BACKEND_LOG" 2>&1 &
      else
        nohup env PYTHONPATH=. FLY_API_TOKEN="$fly_api_token" "$backend_python" -m uvicorn main:app --host 0.0.0.0 --port "$BACKEND_PORT" > "$BACKEND_LOG" 2>&1 &
      fi
    else
      if [[ "$backend_python" == *" run -n "* ]]; then
        nohup env PYTHONPATH=. $backend_python -m uvicorn main:app --host 0.0.0.0 --port "$BACKEND_PORT" > "$BACKEND_LOG" 2>&1 &
      else
        nohup env PYTHONPATH=. "$backend_python" -m uvicorn main:app --host 0.0.0.0 --port "$BACKEND_PORT" > "$BACKEND_LOG" 2>&1 &
      fi
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

start_redis_proxy() {
  # Local redis-server is preferred for dev — no WireGuard tunnel needed.
  # Production uses the private Fly+Upstash URL set via flyctl secrets.
  if [[ ! -x "${REDIS_SERVER_EXE:-}" ]]; then
    log "redis-server not found — skipping (set KITH_REDIS_SERVER_EXE if needed)"
    log "Hint: /home/joe/miniconda3/bin/conda install -n kith_venv redis-server -c conda-forge"
    return
  fi

  # Skip if something is already listening on the Redis port
  if [[ "$(port_listener_count "$REDIS_PORT")" != "0" ]]; then
    log "Port $REDIS_PORT already in use — skipping local redis-server start"
    return
  fi

  log "Starting local redis-server on port $REDIS_PORT"
  (
    nohup "$REDIS_SERVER_EXE" \
      --port "$REDIS_PORT" \
      --daemonize no \
      --loglevel notice \
      --save "" \
      --appendonly no \
      > "$REDIS_LOG" 2>&1 &
    echo $! > "$REDIS_PID_FILE"
  )

  # Wait up to 8s for the port to open
  for ((i=1; i<=8; i++)); do
    if [[ "$(port_listener_count "$REDIS_PORT")" != "0" ]]; then
      log "Redis ready on localhost:$REDIS_PORT"
      return
    fi
    sleep 1
  done
  log "WARNING: redis-server did not open port $REDIS_PORT in 8s (check $REDIS_LOG)"
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
  log "Stopping backend, frontend, Inngest, and Redis proxy"
  kill_pid_file "$BACKEND_PID_FILE" "backend"
  kill_pid_file "$FRONTEND_PID_FILE" "frontend"
  kill_pid_file "$INNGEST_PID_FILE" "inngest"
  kill_pid_file "$REDIS_PID_FILE" "redis-proxy"

  stop_port_listeners "$BACKEND_PORT"
  stop_port_listeners "$FRONTEND_PORT"
  stop_port_listeners "$INNGEST_PORT"
  # Don't aggressively stop 6379 — another Redis may be legitimately there

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
  local backend_count frontend_count inngest_count redis_count
  backend_count="$(port_listener_count "$BACKEND_PORT")"
  frontend_count="$(port_listener_count "$FRONTEND_PORT")"
  inngest_count="$(port_listener_count "$INNGEST_PORT")"
  redis_count="$(port_listener_count "$REDIS_PORT")"

  log "Backend listeners on $BACKEND_PORT: $backend_count"
  log "Frontend listeners on $FRONTEND_PORT: $frontend_count"
  log "Inngest listeners on $INNGEST_PORT: $inngest_count"
  log "Redis proxy listeners on $REDIS_PORT: $redis_count"
  log "Backend log: $BACKEND_LOG"
  log "Frontend log: $FRONTEND_LOG"
  log "Inngest log: $INNGEST_LOG"
  log "Redis proxy log: $REDIS_LOG"
}

start_services() {
  stop_port_listeners "$BACKEND_PORT"
  stop_port_listeners "$FRONTEND_PORT"
  stop_port_listeners "$INNGEST_PORT"

  start_redis_proxy
  start_backend
  wait_for_url "http://127.0.0.1:$BACKEND_PORT/docs" "Backend" 45 1 "$BACKEND_LOG"
  start_inngest
  if [[ "$USE_INNGEST_DEV_SERVER" == "1" ]]; then
    wait_for_url "http://127.0.0.1:$INNGEST_PORT/" "Inngest" 45 1 "$INNGEST_LOG"
  fi
  start_frontend
  wait_for_url "http://127.0.0.1:$FRONTEND_PORT/" "Frontend" 45 1 "$FRONTEND_LOG"

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
