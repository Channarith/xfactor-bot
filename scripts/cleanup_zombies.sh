#!/bin/bash
#
# XFactor Bot - Zombie Process Cleanup Script
# Cleans up any orphaned backend processes
#
# Usage: ./cleanup_zombies.sh
#
# This script is useful for:
# - Cleaning up after force quits
# - Resolving port conflicts
# - Fixing "Address already in use" errors
#

echo "=========================================="
echo "XFactor Bot - Zombie Process Cleanup"
echo "=========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Track if we found anything
FOUND_PROCESSES=0

# Function to kill processes by name
kill_by_name() {
    local name=$1
    local pids=$(pgrep -f "$name" 2>/dev/null)
    
    if [ -n "$pids" ]; then
        echo -e "${YELLOW}Found $name processes:${NC}"
        for pid in $pids; do
            echo "  PID: $pid"
            FOUND_PROCESSES=1
        done
        
        echo -e "${RED}Killing processes...${NC}"
        pkill -9 -f "$name" 2>/dev/null
        echo -e "${GREEN}Done${NC}"
        echo ""
    fi
}

# Function to kill processes by port
kill_by_port() {
    local port=$1
    local pids=$(lsof -ti :$port 2>/dev/null)
    
    if [ -n "$pids" ]; then
        echo -e "${YELLOW}Found processes on port $port:${NC}"
        for pid in $pids; do
            local proc_name=$(ps -p $pid -o comm= 2>/dev/null || echo "unknown")
            echo "  PID: $pid ($proc_name)"
            FOUND_PROCESSES=1
        done
        
        echo -e "${RED}Killing processes...${NC}"
        for pid in $pids; do
            kill -9 $pid 2>/dev/null
        done
        echo -e "${GREEN}Done${NC}"
        echo ""
    fi
}

echo "Checking for zombie XFactor processes..."
echo ""

# Kill xfactor-backend processes
kill_by_name "xfactor-backend"

# Kill any Python processes running the backend
kill_by_name "run_backend.py"

# Kill uvicorn processes on our port
kill_by_name "uvicorn.*9876"

# Kill processes on port 9876 (backend API)
echo "Checking port 9876 (Backend API)..."
kill_by_port 9876

# Kill processes on port 5173 (Vite dev server)
echo "Checking port 5173 (Vite Dev Server)..."
kill_by_port 5173

# Kill processes on port 3000 (alternate frontend)
echo "Checking port 3000 (Alternate Frontend)..."
kill_by_port 3000

# macOS specific: Check for xfactor-bot app processes
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo "Checking for XFactor Bot app processes (macOS)..."
    
    # Kill XFactor Bot app if running
    pids=$(pgrep -f "XFactor Bot" 2>/dev/null)
    if [ -n "$pids" ]; then
        echo -e "${YELLOW}Found XFactor Bot app processes${NC}"
        FOUND_PROCESSES=1
        pkill -9 -f "XFactor Bot" 2>/dev/null
        echo -e "${GREEN}Killed XFactor Bot app processes${NC}"
        echo ""
    fi
fi

# Summary
echo "=========================================="
if [ $FOUND_PROCESSES -eq 1 ]; then
    echo -e "${GREEN}Cleanup completed! All zombie processes killed.${NC}"
else
    echo -e "${GREEN}No zombie processes found. System is clean.${NC}"
fi
echo "=========================================="
echo ""

# Verify ports are free
echo "Verifying ports are free..."
if lsof -ti :9876 >/dev/null 2>&1; then
    echo -e "${RED}Warning: Port 9876 is still in use${NC}"
else
    echo -e "${GREEN}Port 9876: Free${NC}"
fi

if lsof -ti :5173 >/dev/null 2>&1; then
    echo -e "${YELLOW}Note: Port 5173 is in use (dev server may be running)${NC}"
else
    echo -e "${GREEN}Port 5173: Free${NC}"
fi

echo ""
echo "Done!"

