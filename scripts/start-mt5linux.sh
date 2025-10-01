#!/bin/bash
# Script to start mt5linux server

echo "=== Starting MT5Linux Server ==="

# Set environment variables
export DISPLAY=${DISPLAY:-:1}
export MT5_PORT=${MT5_PORT:-8011}

# Check if Wine is available
if ! command -v wine &> /dev/null; then
    echo "❌ Wine not found"
    exit 1
fi

# Check if MT5 is installed
MT5_PATH="/root/.wine/drive_c/Program Files/MetaTrader 5/terminal64.exe"
if [ ! -f "$MT5_PATH" ]; then
    echo "❌ MT5 not installed at: $MT5_PATH"
    echo "Run: cd /app/Metatrader && python3 start.py"
    exit 1
fi

# Kill any existing mt5linux processes
echo "Stopping any existing mt5linux processes..."
pkill -f "mt5linux" 2>/dev/null || true
sleep 2

# Start MT5 terminal in Wine (if not already running)
echo "Starting MT5 terminal..."
wine "$MT5_PATH" &
sleep 3

# Start mt5linux server
echo "Starting mt5linux server on port $MT5_PORT..."
python3 -m mt5linux --host 0.0.0.0 -p $MT5_PORT -w wine python.exe &

# Wait for server to start
sleep 5

# Check if server is running
if curl -s http://localhost:$MT5_PORT/ > /dev/null 2>&1; then
    echo "✅ mt5linux server started successfully on port $MT5_PORT"
else
    echo "⚠️  mt5linux server may not be responding yet (this is normal, give it a few more seconds)"
fi

echo ""
echo "MT5Linux server should be running on port $MT5_PORT"
echo "Test with: curl http://localhost:$MT5_PORT/"

