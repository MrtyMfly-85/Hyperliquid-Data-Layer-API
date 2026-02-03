"""Base REST + WebSocket client for Hyperliquid public API."""

from __future__ import annotations

import asyncio
import json
import threading
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, TypedDict

import requests
import websockets

from .config import HYPERLIQUID_REST, HYPERLIQUID_WS


class AllMidsResponse(TypedDict, total=False):
    mids: Dict[str, str]


class MetaAndAssetCtxsResponse(TypedDict, total=False):
    meta: Dict[str, Any]
    assetCtxs: List[Dict[str, Any]]


class L2BookResponse(TypedDict, total=False):
    coin: str
    levels: List[List[List[float]]]


class CandleSnapshotResponse(TypedDict, total=False):
    t: List[int]
    o: List[float]
    h: List[float]
    l: List[float]
    c: List[float]
    v: List[float]
    n: List[int]


class ClearinghouseStateResponse(TypedDict, total=False):
    assetPositions: List[Dict[str, Any]]
    marginSummary: Dict[str, Any]


class VaultDetailsResponse(TypedDict, total=False):
    vault: str
    positions: List[Dict[str, Any]]
    summary: Dict[str, Any]


class FundingHistoryResponse(TypedDict, total=False):
    history: List[Dict[str, Any]]


class UserFillsResponse(TypedDict, total=False):
    fills: List[Dict[str, Any]]


class HistoricalOrdersResponse(TypedDict, total=False):
    orders: List[Dict[str, Any]]


class RateLimiter:
    def __init__(self, max_per_sec: float):
        self.max_per_sec = max_per_sec
        self.min_interval = 1.0 / max_per_sec
        self._lock = threading.Lock()
        self._last_ts = 0.0

    def wait(self) -> None:
        with self._lock:
            now = time.time()
            delta = now - self._last_ts
            if delta < self.min_interval:
                time.sleep(self.min_interval - delta)
            self._last_ts = time.time()


@dataclass
class RestRequest:
    payload: Dict[str, Any]
    response: Any


class HyperliquidRESTClient:
    def __init__(self, url: str = HYPERLIQUID_REST, max_rps: float = 10.0):
        self.url = url
        self.session = requests.Session()
        self.limiter = RateLimiter(max_rps)

    def _post(self, payload: Dict[str, Any]) -> RestRequest:
        self.limiter.wait()
        retries = 3
        backoff = 0.5
        last_exc: Optional[Exception] = None
        for attempt in range(retries):
            try:
                resp = self.session.post(self.url, json=payload, timeout=15)
                if resp.status_code >= 500 or resp.status_code == 429:
                    raise requests.HTTPError(f"HTTP {resp.status_code}")
                resp.raise_for_status()
                return RestRequest(payload=payload, response=resp.json())
            except Exception as exc:
                last_exc = exc
                if attempt == retries - 1:
                    break
                time.sleep(backoff)
                backoff *= 2
        raise RuntimeError(f"REST request failed: {last_exc}")

    def all_mids(self) -> AllMidsResponse:
        return self._post({"type": "allMids"}).response

    def meta_and_asset_ctxs(self) -> MetaAndAssetCtxsResponse:
        return self._post({"type": "metaAndAssetCtxs"}).response

    def l2_book(self, coin: str) -> L2BookResponse:
        return self._post({"type": "l2Book", "coin": coin}).response

    def candle_snapshot(self, coin: str, interval: str, start_time: int, end_time: int) -> CandleSnapshotResponse:
        payload = {
            "type": "candleSnapshot",
            "req": {
                "coin": coin,
                "interval": interval,
                "startTime": start_time,
                "endTime": end_time,
            },
        }
        return self._post(payload).response

    def clearinghouse_state(self, user: str) -> ClearinghouseStateResponse:
        return self._post({"type": "clearinghouseState", "user": user}).response

    def vault_details(self, vault: str) -> VaultDetailsResponse:
        return self._post({"type": "vaultDetails", "vaultAddress": vault}).response

    def user_fills(self, user: str) -> UserFillsResponse:
        return self._post({"type": "userFills", "user": user}).response

    def user_fills_by_time(self, user: str, start_time: int, end_time: int) -> UserFillsResponse:
        payload = {
            "type": "userFillsByTime",
            "user": user,
            "startTime": start_time,
            "endTime": end_time,
        }
        return self._post(payload).response

    def historical_orders(self, user: str) -> HistoricalOrdersResponse:
        return self._post({"type": "historicalOrders", "user": user}).response

    def funding_history(self, coin: str, start_time: int, end_time: int) -> FundingHistoryResponse:
        payload = {
            "type": "fundingHistory",
            "coin": coin,
            "startTime": start_time,
            "endTime": end_time,
        }
        return self._post(payload).response


class HyperliquidWSClient:
    def __init__(
        self,
        url: str = HYPERLIQUID_WS,
        on_message: Optional[Callable[[Dict[str, Any]], None]] = None,
        reconnect_delay: float = 3.0,
    ):
        self.url = url
        self.on_message = on_message
        self.reconnect_delay = reconnect_delay
        self._subscriptions: List[Dict[str, Any]] = []
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self._ws_lock = threading.Lock()
        self._ws: Optional[websockets.WebSocketClientProtocol] = None
        self._task: Optional[asyncio.Task] = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._loop:
            self._loop.call_soon_threadsafe(self._loop.stop)
        if self._thread:
            self._thread.join(timeout=5)

    def subscribe(self, subscription: Dict[str, Any]) -> None:
        self._subscriptions.append(subscription)
        if self._loop:
            asyncio.run_coroutine_threadsafe(self._send_subscribe(subscription), self._loop)

    def subscribe_trades(self, coin: str) -> None:
        self.subscribe({"type": "trades", "coin": coin})

    def subscribe_l2book(self, coin: str) -> None:
        self.subscribe({"type": "l2Book", "coin": coin})

    def subscribe_candle(self, coin: str, interval: str) -> None:
        self.subscribe({"type": "candle", "coin": coin, "interval": interval})

    def subscribe_active_asset_ctx(self, coin: Optional[str] = None) -> None:
        sub: Dict[str, Any] = {"type": "activeAssetCtx"}
        if coin:
            sub["coin"] = coin
        self.subscribe(sub)

    def _run(self) -> None:
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._task = self._loop.create_task(self._connect_loop())
        try:
            self._loop.run_forever()
        finally:
            if self._task:
                self._task.cancel()
                try:
                    self._loop.run_until_complete(self._task)
                except BaseException:
                    pass
            self._loop.close()

    async def _connect_loop(self) -> None:
        try:
            while not self._stop.is_set():
                try:
                    async with websockets.connect(self.url, ping_interval=20, ping_timeout=20) as ws:
                        with self._ws_lock:
                            self._ws = ws
                        for sub in self._subscriptions:
                            await self._send_subscribe(sub)
                        await self._recv_loop(ws)
                except Exception:
                    with self._ws_lock:
                        self._ws = None
                    await asyncio.sleep(self.reconnect_delay)
        except asyncio.CancelledError:
            return

    async def _send_subscribe(self, subscription: Dict[str, Any]) -> None:
        msg = {"method": "subscribe", "subscription": subscription}
        with self._ws_lock:
            ws = self._ws
        if ws:
            await ws.send(json.dumps(msg))

    async def _recv_loop(self, ws: websockets.WebSocketClientProtocol) -> None:
        async for message in ws:
            try:
                data = json.loads(message)
            except Exception:
                continue
            if self.on_message:
                self.on_message(data)


if __name__ == "__main__":
    client = HyperliquidRESTClient()
    try:
        mids = client.all_mids()
        print(f"Mids keys: {len(mids.get('mids', {}))}")
    except Exception as exc:
        print(f"REST test failed: {exc}")
