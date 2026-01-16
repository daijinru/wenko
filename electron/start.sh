#!/bin/bash

# 1. Check port usage (8080)
PORT=8080
echo "Checking port $PORT..."
PID=$(lsof -ti :$PORT)
if [ -n "$PID" ]; then
  echo "Port $PORT is in use by PID $PID. Killing..."
  kill -9 $PID
else
  echo "Port $PORT is free."
fi

# 2. Build live2d/live2d-widget
echo "Building live2d-widget..."
# Save current directory
CURRENT_DIR=$(pwd)
cd live2d/live2d-widget
# Install dependencies if needed (optional, but good practice)
yarn install
yarn build
# Return to electron directory
cd "$CURRENT_DIR"

# 3. Build electron internal assets
echo "Building electron assets..."
npm run build

# 4. Start electron
echo "Starting electron..."
yarn start
