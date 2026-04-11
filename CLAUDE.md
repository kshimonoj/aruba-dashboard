# Aruba Central Streaming Dashboard

## Project Overview

A real-time streaming dashboard that connects to HPE Aruba Networking Central via WebSocket,
receives AP Monitoring and Audit Trail events in CloudEvents/protobuf format, decodes them,
and relays them to a browser-based dashboard built with Next.js.

## Architecture

```
HPE Aruba Central (wss://)
    │
    ├── /network-services/v1alpha1/audit-trail-events
    └── /network-monitoring/v1alpha1/ap-events
         │
    [aruba_stream.py]  ←  TokenManager supplies fresh Bearer token
         │
    [decoder.py]       ←  CloudEvents protobuf → JSON
         │
    [main.py / FastAPI :8000]
         │
         ├── /ws/events       ← Audit Trail relay
         └── /ws/ap-events    ← AP Monitoring relay
              │
         [Next.js :3000]
              ├── LiveEventTable.tsx
              └── APMonitoringTable.tsx
```

## Backend (`backend/`)

| File | Role |
|------|------|
| `main.py` | FastAPI application. Manages lifespan (token init + stream start), exposes `/ws/events`, `/ws/ap-events`, and `/health`. Broadcasts decoded JSON to all connected frontend clients. |
| `aruba_stream.py` | Generic `StreamClient` class. Connects to a given WSS endpoint with a Bearer token, forwards raw bytes to a callback, and auto-reconnects on disconnect or token expiry. |
| `token_manager.py` | `TokenManager` singleton. Fetches OAuth2 tokens via `client_credentials` grant, caches them, and refreshes every 110 minutes (10 minutes before expiry). Retries every 30 s on failure. |
| `decoder.py` | Two-stage protobuf decoder. `decode_message()` handles Audit Trail (JSON). `decode_ap_message()` parses the CloudEvents protobuf envelope (field 4 = type, field 8 = `google.protobuf.Any`) then decodes the inner AP message using field-number maps. Returns plain JSON dict. |
| `proto/ap_monitoring.proto` | Proto3 schema for all AP Monitoring message types (APInfo, RadioInfo, VapInfo, PortInfo, WlanInfo, TunnelInfo, APSystemStat, RadioStat, VapStat, PortStat, ModemStat, TunnelStat, IPProbeStat, RoleStat, SsidStat, VlanStat) and enumerations. Reference only — decoding is done manually without `protoc`. |
| `requirements.txt` | `fastapi`, `uvicorn[standard]`, `websockets`, `protobuf`, `python-dotenv`, `requests` |

## Frontend (`frontend/`)

| File | Role |
|------|------|
| `app/page.tsx` | Dashboard root. Tab switcher (Audit Trail / AP Monitoring). Mounts both tables simultaneously to keep WebSocket connections alive while the inactive tab is hidden. |
| `components/LiveEventTable.tsx` | Connects to `ws://<host>:8000/ws/events`. Displays last 100 Audit Trail events. Click-to-expand rows show formatted JSON + extracted key fields. Format badge (json / protobuf / binary). |
| `components/APMonitoringTable.tsx` | Connects to `ws://<host>:8000/ws/ap-events`. Displays last 100 AP Monitoring events with columns: event type badge, serial number, MAC address, status. Click-to-expand shows all decoded protobuf fields. |
| `components/StatusBar.tsx` | Shows total event count and last-received timestamp for the active tab. |

## Endpoints

### WebSocket streams (Aruba Central → Backend)

| Name | URL |
|------|-----|
| Audit Trail | `wss://{CENTRAL_HOST}/network-services/v1alpha1/audit-trail-events` |
| AP Monitoring | `wss://{CENTRAL_HOST}/network-monitoring/v1alpha1/ap-events` |

### OAuth2 token

| | |
|---|---|
| URL | `https://sso.common.cloud.hpe.com/as/token.oauth2` |
| Method | `POST application/x-www-form-urlencoded` |
| Grant | `client_credentials` |
| Token TTL | 7199 s (≈ 2 hours) |

### Backend API (FastAPI)

| Endpoint | Description |
|----------|-------------|
| `GET /health` | Returns connection status, client counts, and `token_expires_in` |
| `WS /ws/events` | Streams decoded Audit Trail events to frontend |
| `WS /ws/ap-events` | Streams decoded AP Monitoring events to frontend |

## Key Implementation Notes

### Protobuf two-stage decode (`decoder.py`)

AP Monitoring messages are encoded as **CloudEvents protobuf** (binary, not JSON):

```
Outer CloudEvents envelope (protobuf)
  field 4  → type   (string)  e.g. "com.hpe.greenlake...aps.stats.device"
  field 8  → proto_data (google.protobuf.Any)
                field 1 → type_url  e.g. "type.googleapis.com/ap.APSystemStat"
                field 2 → value     (inner AP message bytes)

Inner AP message (protobuf)
  decoded with per-message field-number maps
  wire types: varint (int/enum), fixed32 (float), fixed64 (double), LEN (string/bytes)
```

### Token auto-refresh (`token_manager.py`)

- Normal refresh cycle: **every 6600 s (1 h 50 min)**
- Emergency refresh: when `token_expires_in < 60 s` (checked per-message in `StreamClient`)
- On failure: retries every **30 s** until successful
- `StreamClient._should_reconnect()` checks `TokenManager.token_expires_in < 60` and breaks the receive loop, triggering a fresh connection with a new token

### WebSocket relay (`main.py` + `aruba_stream.py`)

- Two `StreamClient` instances run as independent `asyncio.Task`s
- Both share the same `TokenManager` singleton
- Each stream has its own `Set[WebSocket]` of connected frontend clients
- Messages are broadcast to all clients concurrently; disconnected clients are pruned automatically

## Environment Variables

| Variable | Description |
|----------|-------------|
| `CENTRAL_HOST` | Aruba Central API hostname (e.g. `internal.api.central.arubanetworks.com`) |
| `CLIENT_ID` | OAuth2 client ID from Aruba Central / HPE GreenLake |
| `CLIENT_SECRET` | OAuth2 client secret |

Copy `backend/.env.example` to `backend/.env` and fill in values. The access token is never stored in `.env` — it is fetched at runtime.

## systemd Services

| Service | Unit file | Description |
|---------|-----------|-------------|
| `aruba-backend` | `/etc/systemd/system/aruba-backend.service` | Runs `python3 -m uvicorn main:app --host 0.0.0.0 --port 8000` from `backend/`. Auto-restarts on failure. |
| `aruba-frontend` | `/etc/systemd/system/aruba-frontend.service` | Runs `next start` from `frontend/` using Node.js 20 (nvm). Auto-restarts on failure. |

Both services are enabled (`systemctl enable`) and start automatically on boot.

## Future Extension Points

### Additional Aruba Central streaming endpoints

| Endpoint | Data |
|----------|------|
| `/network-services/v1alpha1/location-events` | Client location updates |
| `/network-services/v1alpha1/geofence-events` | Geofence entry/exit events |
| `/network-analytics/v1alpha1/location-analytics` | Dwell time, foot traffic analytics |

To add a new stream:
1. Add `make_<name>_client()` in `aruba_stream.py`
2. Add field maps in `decoder.py`
3. Add `Set[WebSocket]` + `/ws/<name>` endpoint in `main.py`
4. Add a new tab + table component in the frontend

### UI improvements

- Filter/search by serial number, MAC address, or event type
- Charts and graphs for AP stats (CPU, memory, tx/rx bytes over time)
- Alert threshold display (e.g. highlight APs with CPU > 80%)
- Export events to CSV
- Persistent event history with a local database (SQLite / PostgreSQL)
