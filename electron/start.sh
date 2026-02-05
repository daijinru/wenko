#!/bin/bash
set -e

# 1. Free occupied ports (8080 for static server, 3000 for Vite Dev Server)
for PORT in 8080 3000; do
  PID=$(lsof -ti :$PORT 2>/dev/null || true)
  if [ -n "$PID" ]; then
    echo "Port $PORT is in use by PID $PID. Killing..."
    kill -9 $PID
  fi
done

# 2. Build live2d/live2d-widget
echo "Building live2d-widget..."
npm run build:live2d

# 3. Start dev mode (Vite Dev Server + Electron with HMR)
echo "Starting dev mode..."
npm run dev
