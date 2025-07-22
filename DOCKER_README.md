# MT5 Docker API

[![Docker Pulls](https://img.shields.io/docker/pulls/jsfrnc/mt5-docker-api)](https://hub.docker.com/r/jsfrnc/mt5-docker-api)
[![Docker Image Size](https://img.shields.io/docker/image-size/jsfrnc/mt5-docker-api)](https://hub.docker.com/r/jsfrnc/mt5-docker-api)
[![GitHub](https://img.shields.io/github/license/jefrnc/mt5-docker-api)](https://github.com/jefrnc/mt5-docker-api)

Run MetaTrader5 in Docker with Web VNC access and REST API.

## Quick Start

```bash
docker run -d \
  -p 3000:3000 \
  -p 8000:8000 \
  -p 8001:8001 \
  -v mt5_data:/config \
  -e CUSTOM_USER=trader \
  -e PASSWORD=secure_password \
  jsfrnc/mt5-docker-api:latest
```

## Access Points

- **Web VNC**: http://localhost:3000
- **REST API**: http://localhost:8000/docs
- **MT5 Python**: localhost:8001

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `CUSTOM_USER` | Yes | - | VNC username |
| `PASSWORD` | Yes | - | VNC password (min 8 chars) |
| `VNC_PORT` | No | 3000 | Web VNC port |
| `API_PORT` | No | 8000 | REST API port |
| `MT5_PORT` | No | 8001 | MT5 Python server port |

## API Examples

```bash
# Get account info
curl http://localhost:8000/account

# Get symbols
curl http://localhost:8000/symbols

# Place order
curl -X POST http://localhost:8000/order \
  -H "Content-Type: application/json" \
  -d '{"symbol": "EURUSD", "volume": 0.01, "order_type": "BUY"}'
```

## Volumes

- `/config` - Persistent storage for MT5 data and configurations

## Tags

- `latest` - Latest stable version
- `1.0.0` - Specific version
- `1.0` - Major version
- `1` - Major version only

## Links

- [GitHub Repository](https://github.com/jefrnc/mt5-docker-api)
- [Documentation](https://github.com/jefrnc/mt5-docker-api#readme)
- [Issues](https://github.com/jefrnc/mt5-docker-api/issues)