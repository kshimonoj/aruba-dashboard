# Aruba Central Streaming Dashboard

A real-time web dashboard that receives streaming data from HPE Aruba Networking Central via WebSocket and displays AP Monitoring and Audit Trail events in a browser.

## Architecture

```
HPE Aruba Central
    ↕  WebSocket (wss://)
Backend  ──  Python FastAPI  (port 8000)
    │         • WebSocket relay
    │         • Protobuf decode (CloudEvents format)
    │         • OAuth2 token auto-refresh
    ↕  WebSocket (ws://)
Frontend ──  Next.js         (port 3000)
              • Real-time dashboard
              • Expandable event table
              • Dual tab: Audit Trail / AP Monitoring
```

**Runtime:** Ubuntu with systemd (always-on services)

## Received Event Types

| Stream | Endpoint | Message Types |
|--------|----------|---------------|
| Audit Trail | `/network-services/v1alpha1/audit-trail-events` | Audit log events |
| AP Monitoring | `/network-monitoring/v1alpha1/ap-events` | APInfo, RadioInfo, VapInfo, PortInfo, WlanInfo, TunnelInfo, APSystemStat, RadioStat, VapStat, PortStat, ModemStat, TunnelStat, IPProbeStat, RoleStat, SsidStat, VlanStat |

## Prerequisites

- Python 3.9+
- Node.js 20+
- Ubuntu with systemd
- HPE Aruba Central account with API credentials (OAuth2 client credentials)

## Setup

### 1. Clone the repository

```bash
git clone git@github.com:kshimonoj/aruba-dashboard.git
cd aruba-dashboard
```

### 2. Environment variables

Copy the example file and fill in your credentials:

```bash
cp backend/.env.example backend/.env
```

Edit `backend/.env`:

```env
CENTRAL_HOST=internal.api.central.arubanetworks.com
CLIENT_ID=your-client-id
CLIENT_SECRET=your-client-secret
```

| Variable | Description |
|----------|-------------|
| `CENTRAL_HOST` | Aruba Central API hostname |
| `CLIENT_ID` | OAuth2 client ID from Aruba Central |
| `CLIENT_SECRET` | OAuth2 client secret from Aruba Central |

> The access token is fetched and refreshed automatically at runtime — no manual token management required.

### 3. Backend

```bash
cd backend
pip3 install -r requirements.txt
```

### 4. Frontend

```bash
cd frontend
npm install
npm run build
```

## Running with systemd

Services are managed by systemd and start automatically on boot.

### Start

```bash
sudo systemctl start aruba-backend
sudo systemctl start aruba-frontend
```

### Stop

```bash
sudo systemctl stop aruba-backend
sudo systemctl stop aruba-frontend
```

### Restart

```bash
sudo systemctl restart aruba-backend aruba-frontend
```

### Status

```bash
sudo systemctl status aruba-backend aruba-frontend
```

### Enable auto-start on boot

```bash
sudo systemctl enable aruba-backend aruba-frontend
```

### View logs

```bash
# Backend logs
sudo journalctl -u aruba-backend -f

# Frontend logs
sudo journalctl -u aruba-frontend -f
```

## Health Check

```bash
curl http://localhost:8000/health
```

Example response:

```json
{
  "status": "ok",
  "audit_connected": true,
  "ap_connected": true,
  "audit_clients": 1,
  "ap_clients": 1,
  "token_expires_in": 6843,
  "token_status": "valid"
}
```

## Access

| Service | URL |
|---------|-----|
| Dashboard | http://\<server-ip\>:3000 |
| Backend API | http://\<server-ip\>:8000 |
| Health check | http://\<server-ip\>:8000/health |

## Project Structure

```
aruba-dashboard/
├── backend/
│   ├── main.py              # FastAPI app, WebSocket endpoints
│   ├── aruba_stream.py      # WebSocket client for Aruba Central
│   ├── decoder.py           # CloudEvents protobuf decoder
│   ├── token_manager.py     # OAuth2 token auto-refresh
│   ├── proto/
│   │   └── ap_monitoring.proto  # AP Monitoring message definitions
│   ├── requirements.txt
│   └── .env.example
└── frontend/
    ├── app/
    │   └── page.tsx         # Dashboard page with tab navigation
    └── components/
        ├── LiveEventTable.tsx      # Audit Trail event table
        ├── APMonitoringTable.tsx   # AP Monitoring event table
        └── StatusBar.tsx           # Event count & last received time
```
