#!/bin/bash
# Script to restart the FastAPI application

echo "=== Restarting MT5 API ==="

# Kill existing uvicorn process
echo "Stopping existing API process..."
pkill -f "uvicorn src.api.main:app" || echo "No existing process found"

# Wait a moment
sleep 2

# Start the API
echo "Starting API on port 8010..."
cd /app
export MT5_PORT=${MT5_PORT:-8011}
export MT5_HOST=${MT5_HOST:-localhost}

echo "MT5 connection: ${MT5_HOST}:${MT5_PORT}"

# Start uvicorn in background
nohup python3 -m uvicorn src.api.main:app --host 0.0.0.0 --port 8010 > /var/log/api.log 2>&1 &

# Wait for startup
sleep 3

# Check if it's running
if pgrep -f "uvicorn src.api.main:app" > /dev/null; then
    echo "✅ API started successfully"
    echo "Testing health endpoint..."
    sleep 2
    curl -s http://localhost:8010/health | python3 -m json.tool || echo "Health check failed"
else
    echo "❌ Failed to start API"
    exit 1
fi

echo ""
echo "API is running on http://0.0.0.0:8010"
echo "Logs: tail -f /var/log/api.log"

