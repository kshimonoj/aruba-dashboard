import asyncio
import logging
import os
import time
from typing import Callable, Optional

import websockets
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

CENTRAL_HOST = os.getenv("CENTRAL_HOST", "")
TOKEN_EXPIRY_SECONDS = 110 * 60  # フォールバック用: 1時間50分


class StreamClient:
    """汎用 Aruba Central WebSocket ストリームクライアント"""

    def __init__(
        self,
        name: str,
        url: str,
        on_message: Callable[[bytes], None],
        token_manager=None,
    ):
        self.name          = name
        self.url           = url
        self.on_message    = on_message
        self._token_manager = token_manager
        self._ws: Optional[websockets.WebSocketClientProtocol] = None
        self._running      = False
        self._connected    = False
        self._connect_time: Optional[float] = None

    @property
    def is_connected(self) -> bool:
        return self._connected

    def _get_token(self) -> str:
        if self._token_manager:
            return self._token_manager.get_token()
        return os.getenv("ACCESS_TOKEN", "")

    async def connect(self) -> None:
        self._running = True
        while self._running:
            try:
                await self._run_session()
            except Exception as e:
                logger.error(f"[{self.name}] Session error: {e}")
                if self._running:
                    logger.info(f"[{self.name}] Reconnecting in 5 seconds...")
                    await asyncio.sleep(5)

    async def _run_session(self) -> None:
        token = self._get_token()
        if not token:
            logger.warning(f"[{self.name}] No token available, waiting 10s...")
            await asyncio.sleep(10)
            return

        headers = {"Authorization": f"Bearer {token}"}
        logger.info(f"[{self.name}] Connecting to {self.url}")
        async with websockets.connect(
            self.url,
            extra_headers=headers,
            ping_interval=20,
            ping_timeout=30,
        ) as ws:
            self._ws           = ws
            self._connected    = True
            self._connect_time = time.monotonic()
            logger.info(f"[{self.name}] Connected")
            try:
                async for message in ws:
                    if self._should_reconnect():
                        logger.info(f"[{self.name}] Scheduled token refresh reconnect")
                        break
                    data = message if isinstance(message, bytes) else message.encode()
                    self.on_message(data)
            finally:
                self._connected = False
                self._ws        = None
                logger.info(f"[{self.name}] Disconnected")

    def _should_reconnect(self) -> bool:
        """TokenManagerがある場合はそちらの残時間を優先判断"""
        if self._token_manager:
            return self._token_manager.token_expires_in < 60
        if self._connect_time is None:
            return False
        return (time.monotonic() - self._connect_time) >= TOKEN_EXPIRY_SECONDS

    async def disconnect(self) -> None:
        self._running = False
        if self._ws:
            await self._ws.close()


def make_audit_trail_client(
    on_message: Callable[[bytes], None], token_manager=None
) -> StreamClient:
    url = f"wss://{CENTRAL_HOST}/network-services/v1alpha1/audit-trail-events"
    return StreamClient("audit-trail", url, on_message, token_manager)


def make_ap_monitoring_client(
    on_message: Callable[[bytes], None], token_manager=None
) -> StreamClient:
    url = f"wss://{CENTRAL_HOST}/network-monitoring/v1alpha1/ap-events"
    return StreamClient("ap-monitoring", url, on_message, token_manager)
