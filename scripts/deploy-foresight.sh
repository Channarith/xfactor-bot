#!/bin/bash
# XFactor Bot MIN Deployment to foresight.nvidia.com
# This deploys the XFactor-botMin version with restricted features
# Usage: SSH_PASS='yourpassword' ./scripts/deploy-foresight.sh
#
# MIN Mode Features:
# - Broker connections disabled (locked behind easter egg)
# - Live trading disabled (locked behind easter egg)
# - Easter egg: Click MIN badge 7 times to unlock prompt
# - Unlock password: 106431
#
# All Help features and new features are included

set -e

# Configuration
REMOTE_USER="cvanthin"
REMOTE_HOST="foresight.nvidia.com"
REMOTE_DIR="/home/cvanthin/trading"
LOCAL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
APP_PORT=9876
VERSION="1.0.9"

# Check for password
if [ -z "$SSH_PASS" ]; then
    echo "❌ Error: SSH_PASS environment variable not set"
    echo ""
    echo "Usage: SSH_PASS='yourpassword' ./scripts/deploy-foresight.sh"
    echo ""
    exit 1
fi

SSH_CMD="sshpass -p '$SSH_PASS' ssh -o StrictHostKeyChecking=no"
SCP_CMD="sshpass -p '$SSH_PASS' scp -o StrictHostKeyChecking=no"
RSYNC_CMD="sshpass -p '$SSH_PASS' rsync -e 'ssh -o StrictHostKeyChecking=no'"

echo "╔════════════════════════════════════════════════════════════╗"
echo "║     XFactor Bot MIN Deployment to foresight.nvidia.com   ║"
echo "║                    Version: $VERSION                      ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "🔒 MIN Mode: Broker connections and Live trading disabled"
echo "🔓 Easter egg: Click MIN badge 7x → Password: 106431"
echo ""

# Step 0: Build frontend with DEMO_MODE=true
echo "🔨 Step 0: Building frontend for MIN mode..."
cd "$LOCAL_DIR/frontend"
VITE_DEMO_MODE=true npm run build
echo "✅ Frontend built for MIN mode"
cd "$LOCAL_DIR"
echo ""

# Step 1: Check disk space
echo "📊 Step 1: Checking remote disk space..."
eval $SSH_CMD $REMOTE_USER@$REMOTE_HOST "df -h /home && echo '' && du -sh /home/$REMOTE_USER 2>/dev/null || echo 'Home directory is new'"

echo ""
echo "Need approximately 500MB for deployment."
echo ""

# Step 2: Create directory
echo "📁 Step 2: Creating remote directory..."
eval $SSH_CMD $REMOTE_USER@$REMOTE_HOST "mkdir -p $REMOTE_DIR"
echo "✅ Created $REMOTE_DIR"

# Step 3: Upload files
echo ""
echo "📤 Step 3: Uploading files (this may take a few minutes)..."
eval $RSYNC_CMD -avz --progress \
    --exclude '.git' \
    --exclude '.venv' \
    --exclude 'venv' \
    --exclude '__pycache__' \
    --exclude '*.pyc' \
    --exclude '.pytest_cache' \
    --exclude 'node_modules' \
    --exclude '.DS_Store' \
    --exclude 'htmlcov' \
    --exclude '*.egg-info' \
    --exclude 'dist' \
    --exclude 'build' \
    --exclude '.cursor' \
    "'$LOCAL_DIR/'" "'$REMOTE_USER@$REMOTE_HOST:$REMOTE_DIR/'"

echo "✅ Files uploaded"

# Step 4: Set up environment
echo ""
echo "🔧 Step 4: Setting up Python environment..."
eval $SSH_CMD $REMOTE_USER@$REMOTE_HOST "cd $REMOTE_DIR && \
if [ ! -d '.venv' ]; then \
    echo 'Creating Python virtual environment...'; \
    python3 -m venv .venv; \
fi && \
source .venv/bin/activate && \
echo 'Installing Python dependencies...' && \
pip install --quiet --upgrade pip && \
pip install --quiet -r requirements.txt && \
echo '✅ Python environment ready'"

# Step 5: Set up frontend (built assets already uploaded)
echo ""
echo "🎨 Step 5: Frontend setup (pre-built for MIN mode)..."
echo "✅ Frontend assets deployed (built locally with VITE_DEMO_MODE=true)"

# Step 6: Create start/stop scripts
echo ""
echo "⚙️  Step 6: Creating service scripts..."

# Create start script
eval $SSH_CMD $REMOTE_USER@$REMOTE_HOST "cat > $REMOTE_DIR/start.sh << 'EOF'
#!/bin/bash
cd /home/cvanthin/trading
source .venv/bin/activate

# Kill any existing processes
pkill -f 'uvicorn src.api.main:app' 2>/dev/null || true
sleep 1

# Start API
echo 'Starting XFactor Bot API on port 9876...'
nohup uvicorn src.api.main:app --host 0.0.0.0 --port 9876 > api.log 2>&1 &
echo \$! > api.pid

sleep 2
echo ''
echo '╔════════════════════════════════════════════════════════════╗'
echo '║            🚀 XFactor Bot is running!                      ║'
echo '╠════════════════════════════════════════════════════════════╣'
echo '║  API + UI: http://foresight.nvidia.com:9876                ║'
echo '║  API Docs: http://foresight.nvidia.com:9876/docs           ║'
echo '╚════════════════════════════════════════════════════════════╝'
EOF
chmod +x $REMOTE_DIR/start.sh"

# Create stop script
eval $SSH_CMD $REMOTE_USER@$REMOTE_HOST "cat > $REMOTE_DIR/stop.sh << 'EOF'
#!/bin/bash
echo 'Stopping XFactor Bot...'
pkill -f 'uvicorn src.api.main:app' 2>/dev/null || true
[ -f /home/cvanthin/trading/api.pid ] && kill \$(cat /home/cvanthin/trading/api.pid) 2>/dev/null
rm -f /home/cvanthin/trading/api.pid
echo '✅ XFactor Bot stopped'
EOF
chmod +x $REMOTE_DIR/stop.sh"

echo "✅ Service scripts created"

# Step 7: Start the application
echo ""
echo "🚀 Step 7: Starting XFactor Bot..."
eval $SSH_CMD $REMOTE_USER@$REMOTE_HOST "$REMOTE_DIR/start.sh"

# Step 8: Verify
echo ""
echo "🔍 Step 8: Verifying deployment..."
sleep 3
eval $SSH_CMD $REMOTE_USER@$REMOTE_HOST "curl -s http://localhost:$APP_PORT/api || echo 'API not responding yet - may need a few more seconds'"

echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║           🎉 Deployment Complete!                          ║"
echo "╠════════════════════════════════════════════════════════════╣"
echo "║                                                            ║"
echo "║  🌐 XFactor Bot: http://foresight.nvidia.com:9876          ║"
echo "║  📚 API Docs:    http://foresight.nvidia.com:9876/docs     ║"
echo "║                                                            ║"
echo "║  🔒 MIN Mode Active:                                       ║"
echo "║     • Broker connections: LOCKED                           ║"
echo "║     • Live trading: LOCKED                                 ║"
echo "║     • Easter egg: Click MIN badge 7x                       ║"
echo "║     • Password: 106431                                     ║"
echo "║                                                            ║"
echo "║  Commands:                                                 ║"
echo "║  • Start: ssh $REMOTE_USER@$REMOTE_HOST '$REMOTE_DIR/start.sh'  ║"
echo "║  • Stop:  ssh $REMOTE_USER@$REMOTE_HOST '$REMOTE_DIR/stop.sh'   ║"
echo "║  • Logs:  ssh $REMOTE_USER@$REMOTE_HOST 'tail -f $REMOTE_DIR/api.log' ║"
echo "║                                                            ║"
echo "╚════════════════════════════════════════════════════════════╝"
