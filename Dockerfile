FROM python:3.13-slim-bookworm

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
    iproute2 \
    lsb-release \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install Wine (updated for Bookworm)
RUN dpkg --add-architecture i386 && \
    mkdir -pm755 /etc/apt/keyrings && \
    wget -O /etc/apt/keyrings/winehq-archive.key https://dl.winehq.org/wine-builds/winehq.key && \
    wget -NP /etc/apt/sources.list.d/ https://dl.winehq.org/wine-builds/debian/dists/bookworm/winehq-bookworm.sources && \
    apt-get update && \
    apt-get install -y --install-recommends winehq-stable && \
    rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt /tmp/requirements.txt

# Install Python packages from requirements
RUN pip install --no-cache-dir -r /tmp/requirements.txt || true

# Create working directory
WORKDIR /app

# Copy application code
COPY . /app/

# Set environment variables
ENV DISPLAY=:1
ENV PYTHONUNBUFFERED=1
ENV WINEPREFIX=/root/.wine

# Configure Wine
RUN winecfg || true

# Expose ports
EXPOSE 5900 3010 8010 8011

# Create startup script that cleans up X server locks
RUN echo '#!/bin/bash\n\
set -e\n\
\n\
echo "=== MT5 Docker API Starting ==="\n\
\n\
# Clean up any stale X server lock files\n\
echo "Cleaning up X server locks..."\n\
rm -f /tmp/.X1-lock /tmp/.X11-unix/X1\n\
\n\
# Start Xvfb\n\
echo "Starting Xvfb..."\n\
Xvfb :1 -screen 0 1024x768x16 &\n\
sleep 2\n\
\n\
# Start x11vnc\n\
echo "Starting x11vnc..."\n\
x11vnc -display :1 -nopw -forever -shared -repeat &\n\
sleep 1\n\
\n\
# Start noVNC\n\
echo "Starting noVNC..."\n\
websockify --web=/usr/share/novnc/ 3010 localhost:5900 &\n\
\n\
# Set display environment\n\
export DISPLAY=:1\n\
export MT5_PORT=${MT5_PORT:-8011}\n\
\n\
# Start Wine and MT5 installation if needed\n\
if [ ! -f "/root/.wine/drive_c/Program Files/MetaTrader 5/terminal64.exe" ]; then\n\
    echo "Installing MetaTrader 5..."\n\
    cd /app/Metatrader\n\
    python3 start.py\n\
    cd /app\n\
fi\n\
\n\
# Check if MT5 is installed\n\
if [ -f "/root/.wine/drive_c/Program Files/MetaTrader 5/terminal64.exe" ]; then\n\
    # Start MT5 terminal\n\
    echo "Starting MT5 terminal..."\n\
    wine "/root/.wine/drive_c/Program Files/MetaTrader 5/terminal64.exe" &\n\
    sleep 3\n\
    \n\
    # Start mt5linux server\n\
    echo "Starting mt5linux server on port $MT5_PORT..."\n\
    python3 -m mt5linux --host 0.0.0.0 -p $MT5_PORT -w wine python.exe &\n\
    sleep 5\n\
else\n\
    echo "WARNING: MT5 not installed, skipping MT5 and mt5linux startup"\n\
    echo "API will run in limited mode"\n\
fi\n\
\n\
# Start the FastAPI application\n\
echo "Starting FastAPI application..."\n\
cd /app\n\
exec python3 -m uvicorn src.api.main:app --host 0.0.0.0 --port 8010\n' > /app/entrypoint.sh && chmod +x /app/entrypoint.sh

CMD ["/app/entrypoint.sh"]
