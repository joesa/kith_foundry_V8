#!/bin/sh
set -e
cd /workspace
npm run dev > /tmp/vite.log 2>&1 &
VITE_PID=$!
cd /app && python3 -m uvicorn bridge:app --host 0.0.0.0 --port 9999 > /tmp/bridge.log 2>&1 &
BRIDGE_PID=$!
sleep 3
if ! kill -0 "$VITE_PID" 2>/dev/null; then
  echo "Vite failed:"; cat /tmp/vite.log; exit 1
fi
if ! kill -0 "$BRIDGE_PID" 2>/dev/null; then
  echo "Bridge failed:"; cat /tmp/bridge.log; exit 1
fi
exec nginx -g 'daemon off;'
