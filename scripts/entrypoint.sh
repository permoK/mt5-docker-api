#!/bin/bash
set -e

echo "=== MT5 Docker API Starting ==="
echo "Environment:"
echo "  WINEPREFIX: ${WINEPREFIX:-/config/.wine}"
echo "  MT5_PORT: ${MT5_PORT:-8001}"
echo "  API_PORT: ${API_PORT:-8000}"
echo "  VNC_PORT: ${VNC_PORT:-3000}"

# Create necessary directories
mkdir -p /config/.wine /var/log/supervisor

# Check if supervisor config exists
if [ ! -f /etc/supervisor/conf.d/supervisord.conf ]; then
    echo "Creating supervisor configuration..."
    cat > /etc/supervisor/conf.d/supervisord.conf << EOF
[supervisord]
nodaemon=true
user=root

[program:xvfb]
command=/usr/bin/Xvfb :1 -screen 0 1024x768x16
autorestart=true
stdout_logfile=/var/log/supervisor/xvfb.log
stderr_logfile=/var/log/supervisor/xvfb.err

[program:x11vnc]
command=/usr/bin/x11vnc -display :1 -forever -shared -nopw
autorestart=true
startretries=10
stdout_logfile=/var/log/supervisor/x11vnc.log
stderr_logfile=/var/log/supervisor/x11vnc.err

[program:novnc]
command=/usr/share/novnc/utils/launch.sh --vnc localhost:5900 --listen ${VNC_PORT:-3000}
autorestart=true
stdout_logfile=/var/log/supervisor/novnc.log
stderr_logfile=/var/log/supervisor/novnc.err

[program:mt5]
command=python3 /Metatrader/start.py
autorestart=true
environment=PYTHONUNBUFFERED=1
stdout_logfile=/var/log/supervisor/mt5.log
stderr_logfile=/var/log/supervisor/mt5.err

[program:api]
command=python3 -m uvicorn api.main:app --host 0.0.0.0 --port ${API_PORT:-8000}
directory=/app
autorestart=true
environment=PYTHONUNBUFFERED=1
stdout_logfile=/var/log/supervisor/api.log
stderr_logfile=/var/log/supervisor/api.err
EOF
fi

echo "Starting supervisor..."
exec /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf