#!/bin/bash
# Stop XFactor Bot MIN Preview

echo "Stopping XFactor Bot MIN Preview..."

# Stop backend
if [ -f /tmp/xfactor-api.pid ]; then
    kill $(cat /tmp/xfactor-api.pid) 2>/dev/null || true
    rm /tmp/xfactor-api.pid
fi
pkill -f 'uvicorn src.api.main:app.*8000' 2>/dev/null || true

# Stop frontend
if [ -f /tmp/xfactor-frontend.pid ]; then
    kill $(cat /tmp/xfactor-frontend.pid) 2>/dev/null || true
    rm /tmp/xfactor-frontend.pid
fi
pkill -f 'vite.*5173' 2>/dev/null || true

echo "✅ XFactor Bot MIN Preview stopped"

