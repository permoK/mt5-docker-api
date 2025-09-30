# MT5 Docker API - Fixes Applied

## Date: 2025-09-30

### Issues Fixed

#### 1. Missing `app.py` File
**Problem:** The Dockerfile was trying to run `/app/app.py` which doesn't exist.
**Solution:** Updated the Dockerfile to use the correct module path: `src.api.main:app`

#### 2. X Server Lock Files
**Problem:** `/tmp/.X1-lock` persists between container restarts, preventing Xvfb from starting.
**Solution:** Added cleanup of lock files in the entrypoint script:
```bash
rm -f /tmp/.X1-lock /tmp/.X11-unix/X1
```

#### 3. Wrong API Port in Healthcheck
**Problem:** docker-compose.yml healthcheck was using port 8000 instead of 8010.
**Solution:** Updated healthcheck to use correct port 8010.

#### 4. Incorrect Module Path
**Problem:** Various scripts referenced `api.main:app` instead of `src.api.main:app`.
**Solution:** Updated all references to use the correct module path.

### Files Modified

1. **Dockerfile**
   - Fixed entrypoint script to clean up X server locks
   - Updated API module path to `src.api.main:app`
   - Changed port from 8000 to 8010
   - Added proper error handling with `set -e`

2. **docker-compose.yml**
   - Changed from using Docker Hub image to local build
   - Updated healthcheck port from 8000 to 8010

3. **.env** (created)
   - Added template for environment variables
   - Includes MT5 credentials, API keys, and configuration

### How to Use

#### 1. Configure Environment Variables
Edit the `.env` file with your MT5 credentials:
```bash
MT5_LOGIN=your_mt5_login_number
MT5_PASSWORD=your_mt5_password
MT5_SERVER=your_broker_server
API_KEY=your-secure-api-key
VNC_PASSWORD=your_vnc_password
```

#### 2. Build the Image
```bash
docker-compose build
```

#### 3. Start the Container
```bash
docker-compose up -d
```

#### 4. Check Logs
```bash
docker-compose logs -f
```

#### 5. Access the Services

- **VNC Web Access**: http://localhost:3010
  - View the MT5 terminal graphically
  - Password: Set in `.env` as `VNC_PASSWORD`

- **REST API**: http://localhost:8010
  - Main API endpoint for trading operations

- **API Documentation**: http://localhost:8010/docs
  - Interactive Swagger UI documentation

- **Health Check**: http://localhost:8010/health
  - Check if MT5 is connected and API is running

### API Endpoints

#### Account Information
```bash
GET http://localhost:8010/account
```

#### Get Available Symbols
```bash
GET http://localhost:8010/symbols
```

#### Get Symbol Details
```bash
GET http://localhost:8010/symbol/EURUSD
```

#### Place Order
```bash
POST http://localhost:8010/order
Content-Type: application/json

{
  "symbol": "EURUSD",
  "volume": 0.1,
  "order_type": "BUY",
  "sl": 1.0950,
  "tp": 1.1050
}
```

#### Get Open Positions
```bash
GET http://localhost:8010/positions
```

#### Close Position
```bash
DELETE http://localhost:8010/position/{ticket}
```

#### Get Historical Candles
```bash
POST http://localhost:8010/history/candles
Content-Type: application/json

{
  "symbol": "EURUSD",
  "timeframe": "M1",
  "start": "2024-01-01T00:00:00",
  "end": "2024-01-01T01:00:00"
}
```

#### WebSocket for Real-time Ticks
```javascript
ws://localhost:8010/ws/ticks/EURUSD
```

### Troubleshooting

#### Container Won't Start
1. Check logs: `docker-compose logs -f`
2. Ensure `.env` file has correct MT5 credentials
3. Verify ports 3010, 8010, 8011 are not in use

#### X Server Issues
The entrypoint script now automatically cleans up stale X server locks.
If issues persist:
```bash
docker-compose down -v
docker-compose up -d
```

#### MT5 Not Connecting
1. Verify MT5 credentials in `.env`
2. Check if your broker server is correct
3. Ensure your MT5 account allows API access
4. Check logs for connection errors

#### API Returns 503 "MT5 not connected"
1. Wait for MT5 to fully initialize (can take 1-2 minutes)
2. Check VNC to see if MT5 is running
3. Verify MT5 login credentials are correct

### Development

#### Running Tests
```bash
docker-compose exec mt5-docker-api python -m pytest tests/
```

#### Rebuilding After Code Changes
```bash
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

#### Accessing Container Shell
```bash
docker-compose exec mt5-docker-api bash
```

### Architecture

```
┌─────────────────────────────────────────┐
│         Docker Container                │
│                                         │
│  ┌──────────┐  ┌──────────┐            │
│  │  Xvfb    │  │ x11vnc   │            │
│  │  :1      │──│          │            │
│  └──────────┘  └──────────┘            │
│       │             │                   │
│       │        ┌────────────┐           │
│       │        │  noVNC     │           │
│       │        │  :3010     │           │
│       │        └────────────┘           │
│       │                                 │
│  ┌──────────────────┐                  │
│  │  Wine + MT5      │                  │
│  │  terminal64.exe  │                  │
│  └──────────────────┘                  │
│       │                                 │
│  ┌──────────────────┐                  │
│  │  FastAPI         │                  │
│  │  :8010           │                  │
│  └──────────────────┘                  │
└─────────────────────────────────────────┘
```

### Notes

- First startup will take longer as MT5 needs to be installed
- MT5 data is persisted in a Docker volume
- The API runs in "limited mode" if MT5 is not available
- All timestamps are in UTC
- WebSocket connections send updates every 500ms

### Support

For issues or questions:
1. Check the logs: `docker-compose logs -f`
2. Review the API docs: http://localhost:8010/docs
3. Check the original repository for updates

