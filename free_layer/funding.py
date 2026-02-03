"""Funding rate anomaly detector."""

from __future__ import annotations

import threading
import time
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional

import numpy as np

from .client import HyperliquidRESTClient
from .config import POLL_INTERVAL_FUNDING, TRACKED_COINS


@dataclass
class FundingSignal:
    coin: str
    funding_rate: float
    funding_zscore: float
    oi: float
    oi_change_pct: float
    is_anomaly: bool
    timestamp: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class FundingAnomalyDetector:
    def __init__(self, coins: Optional[List[str]] = None):
        self.coins = coins or TRACKED_COINS
        self.rest = HyperliquidRESTClient()
        self._history: Dict[str, List[tuple]] = {coin: [] for coin in self.coins}
        self._latest: Dict[str, FundingSignal] = {}
        self._last_oi: Dict[str, float] = {}
        self._lock = threading.Lock()
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=5)

    def _poll_loop(self) -> None:
        while not self._stop.is_set():
            self._poll_once()
            time.sleep(POLL_INTERVAL_FUNDING)

    def _poll_once(self) -> None:
        now = time.time()
        try:
            resp = self.rest.meta_and_asset_ctxs()
        except Exception:
            return
        # Response is [meta_dict, [asset_ctx, ...]]
        if isinstance(resp, list) and len(resp) >= 2:
            meta = resp[0]
            asset_ctxs = resp[1]
            # Get coin names from meta.universe
            universe = meta.get("universe", [])
            coin_names = [u.get("name", "") for u in universe]
        else:
            return
        for i, ctx in enumerate(asset_ctxs):
            coin = coin_names[i] if i < len(coin_names) else None
            if coin not in self.coins:
                continue
            funding = ctx.get("funding") or ctx.get("fundingRate") or ctx.get("fundingRateHourly")
            try:
                funding_rate = float(funding)
            except Exception:
                funding_rate = 0.0
            oi_raw = ctx.get("openInterest") or ctx.get("openInterestUsd") or ctx.get("oi") or 0.0
            try:
                oi = float(oi_raw)
            except Exception:
                oi = 0.0
            with self._lock:
                hist = self._history[coin]
                hist.append((now, funding_rate))
                cutoff = now - 7 * 24 * 3600
                self._history[coin] = [(t, v) for t, v in hist if t >= cutoff]
                values = [v for _, v in self._history[coin]]
                zscore = 0.0
                if len(values) >= 5 and np.std(values) > 0:
                    zscore = (funding_rate - float(np.mean(values))) / float(np.std(values))
                prev_oi = self._last_oi.get(coin)
                oi_change_pct = 0.0
                if prev_oi and prev_oi != 0:
                    oi_change_pct = ((oi - prev_oi) / prev_oi) * 100.0
                self._last_oi[coin] = oi
                is_anomaly = abs(zscore) >= 2.0 or abs(oi_change_pct) >= 20.0
                self._latest[coin] = FundingSignal(
                    coin=coin,
                    funding_rate=funding_rate,
                    funding_zscore=zscore,
                    oi=oi,
                    oi_change_pct=oi_change_pct,
                    is_anomaly=is_anomaly,
                    timestamp=now,
                )

    def get_signals(self) -> List[FundingSignal]:
        with self._lock:
            return list(self._latest.values())


if __name__ == "__main__":
    detector = FundingAnomalyDetector()
    detector.start()
    try:
        time.sleep(5)
        sigs = detector.get_signals()
        print(sigs[0].to_dict() if sigs else "No funding signal yet.")
    finally:
        detector.stop()
