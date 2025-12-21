#!/bin/bash
# XFactor Bot - Docker Rebuild Script
# Always rebuilds with latest code changes
#
# Usage: ./scripts/docker-rebuild.sh [options]
#   --clean    Force clean rebuild (no cache)
#   --logs     Show logs after starting
#   --stop     Just stop containers, don't start

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DOCKER_DIR="$PROJECT_ROOT/xfactor-bot"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║     XFactor Bot - Docker Rebuild           ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════╝${NC}"

cd "$DOCKER_DIR"

# Parse arguments
CLEAN_BUILD=false
SHOW_LOGS=false
STOP_ONLY=false

for arg in "$@"; do
    case $arg in
        --clean)
            CLEAN_BUILD=true
            ;;
        --logs)
            SHOW_LOGS=true
            ;;
        --stop)
            STOP_ONLY=true
            ;;
    esac
done

# Get current version from frontend package.json
VERSION=$(grep '"version"' "$PROJECT_ROOT/frontend/package.json" | head -1 | sed 's/.*"version": "\(.*\)".*/\1/')
echo -e "${YELLOW}Version: ${VERSION}${NC}"
echo ""

# Stop existing containers
echo -e "${YELLOW}[1/4] Stopping existing containers...${NC}"
docker-compose down 2>/dev/null || true

if [ "$STOP_ONLY" = true ]; then
    echo -e "${GREEN}✓ Containers stopped${NC}"
    exit 0
fi

# Build frontend first (for latest changes)
echo -e "${YELLOW}[2/4] Building frontend...${NC}"
cd "$PROJECT_ROOT/frontend"
npm run build 2>/dev/null || {
    echo -e "${RED}Frontend build failed, continuing with existing dist...${NC}"
}
cd "$DOCKER_DIR"

# Rebuild Docker image
echo -e "${YELLOW}[3/4] Rebuilding Docker image...${NC}"
if [ "$CLEAN_BUILD" = true ]; then
    echo -e "${YELLOW}    (Clean build - no cache)${NC}"
    docker-compose build --no-cache
else
    docker-compose build
fi

# Start containers
echo -e "${YELLOW}[4/4] Starting containers...${NC}"
docker-compose up -d

echo ""
echo -e "${GREEN}╔════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║     XFactor Bot v${VERSION} is running!       ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════╝${NC}"
echo ""
echo -e "  ${BLUE}App:${NC}        http://localhost:9876"
echo -e "  ${BLUE}Grafana:${NC}    http://localhost:3001"
echo -e "  ${BLUE}Prometheus:${NC} http://localhost:9090"
echo ""

if [ "$SHOW_LOGS" = true ]; then
    echo -e "${YELLOW}Showing logs (Ctrl+C to exit)...${NC}"
    docker-compose logs -f xfactor-bot
fi

