#!/bin/bash
# Health check script for MT5 container

# Check VNC service
if ! curl -f http://localhost:3000/ >/dev/null 2>&1; then
    echo "VNC service not responding"
    exit 1
fi

# Check MT5 API port
if ! nc -z localhost 8001 2>/dev/null; then
    echo "MT5 API port not responding"
    exit 1
fi

# Check Wine processes
if ! pgrep -f "wine.*terminal64.exe" >/dev/null 2>&1; then
    echo "MetaTrader5 not running"
    exit 1
fi

# Check Python mt5linux server
if ! pgrep -f "python.*mt5linux" >/dev/null 2>&1; then
    echo "MT5 Python server not running"
    exit 1
fi

# Check disk space (warn if less than 1GB)
available_space=$(df /config | awk 'NR==2 {print $4}')
if [ "$available_space" -lt 1048576 ]; then
    echo "Low disk space: ${available_space}KB available"
    exit 1
fi

echo "All health checks passed"
exit 0