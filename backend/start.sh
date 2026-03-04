#!/bin/bash
set -euo pipefail

# Configure Vite for Fly preview traffic and websocket HMR behind TLS proxy.
cd /workspace
cat << 'EOF' > vite.config.ts
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

const flyHost = process.env.FLY_APP_NAME ? `${process.env.FLY_APP_NAME}.fly.dev` : undefined

export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 3000,
    strictPort: true,
    allowedHosts: true,
    watch: {
      usePolling: true,
      interval: 200
    },
    hmr: flyHost
      ? {
          protocol: 'wss',
          host: flyHost,
          clientPort: 443
        }
      : undefined
  }
})
EOF

npm run dev > /tmp/vite.log 2>&1 &
VITE_PID=$!

cd /app
uvicorn bridge:app --host 0.0.0.0 --port 9999 > /tmp/bridge.log 2>&1 &
BRIDGE_PID=$!

sleep 2
if ! kill -0 "$VITE_PID" 2>/dev/null; then
  echo "Vite failed to start:"
  cat /tmp/vite.log
  exit 1
fi
if ! kill -0 "$BRIDGE_PID" 2>/dev/null; then
  echo "Bridge API failed to start:"
  cat /tmp/bridge.log
  exit 1
fi

nginx -g 'daemon off;'
