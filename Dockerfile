FROM ghcr.io/linuxserver/baseimage-kasmvnc:ubuntu2204

# set version label
ARG BUILD_DATE
ARG VERSION
LABEL build_version="Metatrader Docker:- ${VERSION} Build-date:- ${BUILD_DATE}"

ENV TITLE=Metatrader5
ENV WINEPREFIX="/config/.wine"
ENV DEBIAN_FRONTEND=noninteractive

# Update and install base packages
RUN apt-get update && apt-get upgrade -y && \
    apt-get install -y \
    software-properties-common \
    wget \
    curl \
    python3-pip \
    python3-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Add Wine repository and install
RUN dpkg --add-architecture i386 && \
    wget -qO- https://dl.winehq.org/wine-builds/winehq.key | apt-key add - && \
    add-apt-repository 'deb https://dl.winehq.org/wine-builds/ubuntu/ jammy main' && \
    apt-get update && \
    apt-get install -y --install-recommends winehq-stable && \
    rm -rf /var/lib/apt/lists/*

# Install Python packages
RUN pip3 install --no-cache-dir \
    pydantic \
    python-dotenv \
    requests \
    urllib3 \
    fastapi \
    uvicorn[standard] \
    websockets

# Copy files
COPY /Metatrader /Metatrader
COPY /config/settings.py /app/settings.py
RUN chmod +x /Metatrader/start.py
COPY /root /

EXPOSE 3000 8000 8001
VOLUME /config

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:3000/ || exit 1
