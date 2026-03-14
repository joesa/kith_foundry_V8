"""
Gunicorn configuration for production deployment.

Usage:
  cd backend && gunicorn main:app -c gunicorn_config.py

Env overrides:
  WORKERS=4         — number of uvicorn workers (default: 4)
  PORT=8000         — bind port (default: 8000)
  KITH_FORCE_CLEAR_LOCK=1  — clear PID lock from previous run if needed
"""
import os

# Worker class — must be uvicorn to support async FastAPI
worker_class = "uvicorn.workers.UvicornWorker"

# Worker count: CPU-bound default is 2*cpu+1, but LLM work is I/O bound so
# 4 workers is a safe starting point. Override with WORKERS env var.
workers = int(os.getenv("WORKERS", 4))

# Bind address
bind = f"0.0.0.0:{os.getenv('PORT', 8000)}"

# Timeouts — LLM calls can take 30–120s; keep worker alive long enough.
timeout = 300           # kill worker if silent for 5 min
keepalive = 120         # keep-alive for persistent connections
graceful_timeout = 60   # time to finish in-flight requests on shutdown

# Logging
accesslog = "-"         # stdout
errorlog = "-"          # stdout
loglevel = os.getenv("LOG_LEVEL", "info")

# Restart workers after this many requests to prevent memory leaks.
max_requests = 1000
max_requests_jitter = 100

# Pre-load the application in the master process to share memory with workers.
# Saves per-worker startup time but means a crash in app init kills all workers.
preload_app = False   # Keep False — per-worker init ensures clean state per worker
