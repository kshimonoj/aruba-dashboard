"""
token_manager.py
Aruba Central / HPE GreenLake OAuth2 トークン自動更新
"""
import asyncio
import logging
import os
import time
from typing import Optional

import requests
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

TOKEN_URL      = "https://sso.common.cloud.hpe.com/as/token.oauth2"
REFRESH_BEFORE = 600          # 期限の10分前に更新（expires_in=7200想定）
RETRY_INTERVAL = 30           # 取得失敗時のリトライ間隔（秒）
REFRESH_INTERVAL = 6600       # 通常更新間隔：1時間50分


def _fetch_token_sync() -> dict:
    """
    同期 HTTP POST でアクセストークンを取得する。
    戻り値: {"access_token": "...", "expires_in": 7199, ...}
    """
    client_id     = os.getenv("CLIENT_ID", "")
    client_secret = os.getenv("CLIENT_SECRET", "")

    response = requests.post(
        TOKEN_URL,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={
            "grant_type":    "client_credentials",
            "client_id":     client_id,
            "client_secret": client_secret,
        },
        timeout=15,
    )
    response.raise_for_status()
    return response.json()


class TokenManager:
    """OAuth2 トークンのキャッシュと自動更新を管理するクラス"""

    def __init__(self) -> None:
        self._token:      Optional[str]   = None
        self._expires_at: Optional[float] = None   # monotonic time
        self._lock                        = asyncio.Lock()
        self._task:       Optional[asyncio.Task] = None

    # ── Public API ───────────────────────────────────────────

    def get_token(self) -> str:
        """現在のアクセストークンを返す。未取得の場合は空文字。"""
        return self._token or ""

    @property
    def token_expires_in(self) -> int:
        """トークンの残り有効秒数。未取得は -1。"""
        if self._expires_at is None:
            return -1
        remaining = int(self._expires_at - time.monotonic())
        return max(remaining, 0)

    async def start(self) -> None:
        """初回トークン取得 + バックグラウンド更新タスクを起動"""
        await self._do_refresh()
        self._task = asyncio.create_task(self._refresh_loop())
        logger.info("TokenManager started")

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            logger.info("TokenManager stopped")

    # ── Internal ─────────────────────────────────────────────

    async def _refresh_loop(self) -> None:
        while True:
            wait = max(self.token_expires_in - REFRESH_BEFORE, REFRESH_INTERVAL)
            logger.info(f"[TokenManager] Next refresh in {wait}s")
            await asyncio.sleep(wait)
            await self._do_refresh()

    async def _do_refresh(self) -> None:
        while True:
            try:
                loop = asyncio.get_event_loop()
                data = await loop.run_in_executor(None, _fetch_token_sync)

                async with self._lock:
                    self._token      = data["access_token"]
                    expires_in       = int(data.get("expires_in", 7199))
                    self._expires_at = time.monotonic() + expires_in

                logger.info(
                    f"[TokenManager] Token refreshed. expires_in={expires_in}s"
                )
                return  # 成功したらループを抜ける

            except Exception as e:
                logger.error(f"[TokenManager] Failed to fetch token: {e}")
                logger.info(f"[TokenManager] Retry in {RETRY_INTERVAL}s...")
                await asyncio.sleep(RETRY_INTERVAL)


# ── モジュールレベルのシングルトン ────────────────────────────
token_manager = TokenManager()
