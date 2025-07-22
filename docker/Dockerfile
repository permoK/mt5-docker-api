# Stage 1: Builder - Instalar dependencias pesadas
FROM ubuntu:22.04 as builder

ENV DEBIAN_FRONTEND=noninteractive

# Instalar herramientas de construcción
RUN apt-get update && apt-get install -y \
    wget \
    curl \
    gnupg2 \
    software-properties-common \
    && rm -rf /var/lib/apt/lists/*

# Descargar e instalar Wine
RUN dpkg --add-architecture i386 && \
    wget -qO- https://dl.winehq.org/wine-builds/winehq.key | apt-key add - && \
    add-apt-repository 'deb https://dl.winehq.org/wine-builds/ubuntu/ jammy main' && \
    apt-get update && \
    apt-get install -y --install-recommends \
    winehq-stable \
    && rm -rf /var/lib/apt/lists/*

# Stage 2: Runtime - Imagen final optimizada
FROM ghcr.io/linuxserver/baseimage-kasmvnc:ubuntu2204

# Copiar Wine desde builder
COPY --from=builder /opt/wine-stable /opt/wine-stable
COPY --from=builder /usr/bin/wine* /usr/bin/
COPY --from=builder /usr/lib/wine /usr/lib/wine
COPY --from=builder /usr/lib32/wine /usr/lib32/wine
COPY --from=builder /usr/share/wine /usr/share/wine

# set version label
ARG BUILD_DATE
ARG VERSION
LABEL build_version="Metatrader Docker:- ${VERSION} Build-date:- ${BUILD_DATE}"

ENV TITLE=Metatrader5
ENV WINEPREFIX="/config/.wine"
ENV DEBIAN_FRONTEND=noninteractive
ENV WINEARCH=win64
ENV WINEDEBUG=-all

# Instalar solo dependencias runtime necesarias
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3-pip \
    python3-dev \
    curl \
    ca-certificates \
    libfreetype6:i386 \
    libncurses5:i386 \
    libx11-6:i386 \
    libxext6:i386 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Instalar paquetes Python optimizados
RUN pip3 install --no-cache-dir --compile \
    pydantic==1.10.* \
    python-dotenv \
    requests \
    urllib3 \
    && find /usr/local -type f -name '*.pyc' -delete \
    && find /usr/local -type d -name '__pycache__' -delete

# Copiar archivos de aplicación
COPY /Metatrader /Metatrader
COPY /config/settings.py /app/settings.py
COPY /root /

# Script de healthcheck
COPY /scripts/healthcheck.sh /healthcheck.sh
RUN chmod +x /Metatrader/start.py /healthcheck.sh

EXPOSE 3000 8001
VOLUME /config

# Healthcheck optimizado
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD /healthcheck.sh || exit 1

# Reducir capas finales
RUN ldconfig && \
    fc-cache -f