"""Whale tracker using leaderboard + position monitoring."""

from __future__ import annotations

import threading
import time
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional

from .client import HyperliquidRESTClient
from .config import DEFAULT_WHALES, POLL_INTERVAL_POSITIONS, TRACKED_COINS


@dataclass
class WhaleChange:
    address: str
    coin: str
    prev_size: float
    new_size: float
    timestamp: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class WhaleSignal:
    coin: str
    whale_long_pct: float
    whale_short_pct: float
    recent_changes: List[WhaleChange]
    timestamp: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "coin": self.coin,
            "whale_long_pct": self.whale_long_pct,
            "whale_short_pct": self.whale_short_pct,
            "recent_changes": [c.to_dict() for c in self.recent_changes],
            "timestamp": self.timestamp,
        }


class WhaleTracker:
    def __init__(self, coins: Optional[List[str]] = None):
        self.coins = coins or TRACKED_COINS
        self.rest = HyperliquidRESTClient()
        self.whales: List[str] = []
        self._last_positions: Dict[str, Dict[str, float]] = {}
        self._recent_changes: List[WhaleChange] = []
        self._lock = threading.Lock()
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()

    def add_whale(self, address: str) -> None:
        with self._lock:
            if address not in self.whales:
                self.whales.append(address)

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        # Bootstrap whales in background to avoid blocking
        bootstrap_thread = threading.Thread(target=self._bootstrap_whales, daemon=True)
        bootstrap_thread.start()
        self._thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=5)

    def _bootstrap_whales(self) -> None:
        self.whales = list(DEFAULT_WHALES)
        leaderboard = self._fetch_leaderboard()
        for addr in leaderboard:
            if addr not in self.whales:
                self.whales.append(addr)
            if len(self.whales) >= 50:
                break

    def _fetch_leaderboard(self) -> List[str]:
        candidates: List[str] = []
        for leaderboard_type in ("leaderboard", "traderLeaderboard", "topTraders"):
            try:
                resp = self.rest._post({"type": leaderboard_type}).response
            except Exception:
                continue
            if isinstance(resp, list):
                candidates = resp
            elif isinstance(resp, dict):
                candidates = (
                    resp.get("leaders")
                    or resp.get("entries")
                    or resp.get("data")
                    or []
                )
            if candidates:
                break
        addresses: List[str] = []
        for item in candidates:
            if isinstance(item, str):
                addresses.append(item)
            elif isinstance(item, dict):
                addr = item.get("address") or item.get("user")
                if addr:
                    addresses.append(addr)
        return addresses

    def _poll_loop(self) -> None:
        while not self._stop.is_set():
            self._poll_positions()
            time.sleep(POLL_INTERVAL_POSITIONS)

    def _poll_positions(self) -> None:
        now = time.time()
        for addr in list(self.whales):
            try:
                state = self.rest.clearinghouse_state(addr)
            except Exception:
                continue
            positions = {}
            for item in state.get("assetPositions", []):
                pos = item.get("position", item)
                coin = pos.get("coin")
                if not coin:
                    continue
                size = float(pos.get("szi", 0.0))
                positions[coin] = size
            with self._lock:
                prev = self._last_positions.get(addr, {})
                for coin, new_size in positions.items():
                    prev_size = float(prev.get(coin, 0.0))
                    if new_size != prev_size:
                        self._recent_changes.append(
                            WhaleChange(
                                address=addr,
                                coin=coin,
                                prev_size=prev_size,
                                new_size=new_size,
                                timestamp=now,
                            )
                        )
                for coin, prev_size in prev.items():
                    if coin not in positions and prev_size != 0.0:
                        self._recent_changes.append(
                            WhaleChange(
                                address=addr,
                                coin=coin,
                                prev_size=prev_size,
                                new_size=0.0,
                                timestamp=now,
                            )
                        )
                self._last_positions[addr] = positions
                self._recent_changes = self._recent_changes[-200:]

    def get_signals(self) -> List[WhaleSignal]:
        now = time.time()
        with self._lock:
            changes = list(self._recent_changes)
            signals: List[WhaleSignal] = []
            for coin in self.coins:
                long_count = 0
                short_count = 0
                for addr in self.whales:
                    size = self._last_positions.get(addr, {}).get(coin, 0.0)
                    if size > 0:
                        long_count += 1
                    elif size < 0:
                        short_count += 1
                total = long_count + short_count
                long_pct = (long_count / total) * 100 if total else 0.0
                short_pct = (short_count / total) * 100 if total else 0.0
                signals.append(
                    WhaleSignal(
                        coin=coin,
                        whale_long_pct=long_pct,
                        whale_short_pct=short_pct,
                        recent_changes=changes[-20:],
                        timestamp=now,
                    )
                )
        return signals


if __name__ == "__main__":
    tracker = WhaleTracker()
    tracker.start()
    try:
        time.sleep(5)
        print(f"Whales tracked: {len(tracker.whales)}")
        sigs = tracker.get_signals()
        print(sigs[0].to_dict() if sigs else "No whale signals yet.")
    finally:
        tracker.stop()
