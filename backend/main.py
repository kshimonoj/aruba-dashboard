import asyncio
import json
import logging
from contextlib import asynccontextmanager
from typing import Set

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from token_manager import token_manager
from aruba_stream import make_audit_trail_client, make_ap_monitoring_client
from decoder import decode_message, decode_ap_message

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

audit_clients: Set[WebSocket] = set()
ap_clients:    Set[WebSocket] = set()

audit_stream = None
ap_stream    = None


def _make_handler(clients: Set[WebSocket], decoder):
    def handle(data: bytes) -> None:
        if not clients:
            return
        decoded  = decoder(data)
        payload  = json.dumps(decoded, ensure_ascii=False)
        asyncio.get_event_loop().create_task(_broadcast(clients, payload))
    return handle


async def _broadcast(clients: Set[WebSocket], payload: str) -> None:
    disconnected = set()
    for client in clients:
        try:
            await client.send_text(payload)
        except Exception:
            disconnected.add(client)
    clients.difference_update(disconnected)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global audit_stream, ap_stream

    # 1. トークン取得（初回・ブロッキング）
    await token_manager.start()

    # 2. ストリーム接続開始
    audit_stream = make_audit_trail_client(
        _make_handler(audit_clients, decode_message), token_manager
    )
    ap_stream = make_ap_monitoring_client(
        _make_handler(ap_clients, decode_ap_message), token_manager
    )

    t1 = asyncio.create_task(audit_stream.connect())
    t2 = asyncio.create_task(ap_stream.connect())
    logger.info("Both stream clients started")
    yield

    await audit_stream.disconnect()
    await ap_stream.disconnect()
    await token_manager.stop()
    t1.cancel(); t2.cancel()
    logger.info("Shutdown complete")


app = FastAPI(title="Aruba Central Streaming Dashboard", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://192.168.19.150:3000", "http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health() -> dict:
    expires_in = token_manager.token_expires_in
    return {
        "status":           "ok",
        "audit_connected":  audit_stream.is_connected if audit_stream else False,
        "ap_connected":     ap_stream.is_connected    if ap_stream    else False,
        "audit_clients":    len(audit_clients),
        "ap_clients":       len(ap_clients),
        "token_expires_in": expires_in,
        "token_status":     "valid" if expires_in > 60 else ("expiring" if expires_in >= 0 else "unavailable"),
    }


async def _ws_endpoint(websocket: WebSocket, clients: Set[WebSocket], name: str) -> None:
    await websocket.accept()
    clients.add(websocket)
    logger.info(f"[{name}] client connected. total={len(clients)}")
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        clients.discard(websocket)
        logger.info(f"[{name}] client disconnected. total={len(clients)}")


@app.websocket("/ws/events")
async def ws_audit(websocket: WebSocket) -> None:
    await _ws_endpoint(websocket, audit_clients, "audit-trail")


@app.websocket("/ws/ap-events")
async def ws_ap(websocket: WebSocket) -> None:
    await _ws_endpoint(websocket, ap_clients, "ap-monitoring")
