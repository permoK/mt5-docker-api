FROM python:3.9-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    wget \
    curl \
    gnupg2 \
    software-properties-common \
    xvfb \
    x11vnc \
    novnc \
    supervisor \
    net-tools \
    && rm -rf /var/lib/apt/lists/*

# Install Wine
RUN dpkg --add-architecture i386 && \
    wget -nc https://dl.winehq.org/wine-builds/winehq.key && \
    apt-key add winehq.key && \
    rm winehq.key && \
    echo "deb https://dl.winehq.org/wine-builds/debian/ bullseye main" > /etc/apt/sources.list.d/winehq.list && \
    apt-get update && \
    apt-get install -y --install-recommends winehq-stable && \
    rm -rf /var/lib/apt/lists/*

# Install Python packages
RUN pip install --no-cache-dir \
    pydantic \
    python-dotenv \
    requests \
    urllib3 \
    fastapi \
    uvicorn[standard] \
    websockets \
    mt5linux

# Environment variables
ENV WINEPREFIX=/config/.wine
ENV WINEARCH=win64
ENV WINEDEBUG=-all
ENV DISPLAY=:1

# Create directories
RUN mkdir -p /app /config /scripts

# Copy application files
COPY src/ /app/
COPY scripts/ /scripts/
COPY Metatrader/ /Metatrader/

# Make scripts executable
RUN chmod +x /Metatrader/*.py /scripts/*.sh 2>/dev/null || true

# Supervisor configuration
RUN mkdir -p /var/log/supervisor && \
    echo '[supervisord]\n\
nodaemon=true\n\
\n\
[program:xvfb]\n\
command=/usr/bin/Xvfb :1 -screen 0 1024x768x16\n\
autorestart=true\n\
\n\
[program:x11vnc]\n\
command=/usr/bin/x11vnc -display :1 -forever -shared -nopw\n\
autorestart=true\n\
startretries=10\n\
\n\
[program:novnc]\n\
command=/usr/share/novnc/utils/launch.sh --vnc localhost:5900 --listen 3000\n\
autorestart=true\n\
\n\
[program:mt5]\n\
command=python3 /Metatrader/start.py\n\
autorestart=true\n\
stdout_logfile=/var/log/supervisor/mt5.log\n\
stderr_logfile=/var/log/supervisor/mt5.err\n\
\n\
[program:api]\n\
command=python3 -m uvicorn api.main:app --host 0.0.0.0 --port 8000\n\
directory=/app\n\
autorestart=true\n\
stdout_logfile=/var/log/supervisor/api.log\n\
stderr_logfile=/var/log/supervisor/api.err\n\
' > /etc/supervisor/conf.d/supervisord.conf

# Expose ports
EXPOSE 3000 8000 8001

# Volume
VOLUME /config

# Use entrypoint script
COPY scripts/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Start with entrypoint
ENTRYPOINT ["/entrypoint.sh"]