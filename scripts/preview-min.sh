#!/bin/bash
# XFactor Bot MIN Preview - Test MIN mode locally
# This script builds and runs the MIN version for local preview
#
# MIN Mode Features:
# - Broker connections disabled (locked behind easter egg)
# - Live trading disabled (locked behind easter egg)  
# - Easter egg: Click MIN badge 7 times to unlock prompt
# - Unlock password: 106431
#
# Usage: ./scripts/preview-min.sh

set -e

LOCAL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$LOCAL_DIR"

echo "╔════════════════════════════════════════════════════════════╗"
echo "║      XFactor Bot MIN Preview - Local Testing               ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "🔒 MIN Mode Preview:"
echo "   • Broker connections: DISABLED"
echo "   • Live trading: DISABLED"
echo "   • Easter egg: Click MIN badge 7 times"
echo "   • Unlock password: 106431"
echo ""

# Step 1: Build frontend with DEMO_MODE=true
echo "🔨 Step 1: Building frontend for MIN mode..."
cd "$LOCAL_DIR/frontend"
VITE_DEMO_MODE=true npm run build
echo "✅ Frontend built for MIN mode"
echo ""

# Step 2: Start backend
echo "🚀 Step 2: Starting backend API..."
cd "$LOCAL_DIR"

# Kill any existing processes
pkill -f 'uvicorn src.api.main:app.*8000' 2>/dev/null || true
sleep 1

# Activate venv if exists
if [ -d "venv" ]; then
    source venv/bin/activate
elif [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# Start backend in background
nohup python3 -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload > /tmp/xfactor-api.log 2>&1 &
echo $! > /tmp/xfactor-api.pid
echo "✅ Backend started (PID: $(cat /tmp/xfactor-api.pid))"
echo ""

# Step 3: Start frontend dev server with DEMO_MODE
echo "🌐 Step 3: Starting frontend dev server..."
cd "$LOCAL_DIR/frontend"

# Kill any existing frontend
pkill -f 'vite.*5173' 2>/dev/null || true
sleep 1

# Start frontend with DEMO_MODE in background
nohup VITE_DEMO_MODE=true npm run dev > /tmp/xfactor-frontend.log 2>&1 &
echo $! > /tmp/xfactor-frontend.pid
echo "✅ Frontend started (PID: $(cat /tmp/xfactor-frontend.pid))"
echo ""

sleep 3

echo "╔════════════════════════════════════════════════════════════╗"
echo "║          🎉 MIN Preview Ready!                             ║"
echo "╠════════════════════════════════════════════════════════════╣"
echo "║                                                            ║"
echo "║  🌐 Frontend: http://localhost:5173                        ║"
echo "║  🔧 Backend:  http://localhost:8000                        ║"
echo "║  📚 API Docs: http://localhost:8000/docs                   ║"
echo "║                                                            ║"
echo "║  To unlock full features:                                  ║"
echo "║  1. Click the MIN badge 7 times quickly                    ║"
echo "║  2. Enter password: 106431                                 ║"
echo "║                                                            ║"
echo "║  To stop: ./scripts/stop-min-preview.sh                    ║"
echo "║                                                            ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "Opening browser..."
sleep 1
open http://localhost:5173 2>/dev/null || xdg-open http://localhost:5173 2>/dev/null || echo "Please open http://localhost:5173 manually"

