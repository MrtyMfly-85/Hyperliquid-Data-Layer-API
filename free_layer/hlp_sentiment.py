"""HLP vault sentiment with z-scores."""

from __future__ import annotations

import threading
import time
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional

import numpy as np

from .client import HyperliquidRESTClient
from .config import HLP_VAULT, POLL_INTERVAL_HLP, TRACKED_COINS


@dataclass
class HLPSignal:
    coin: str
    hlp_exposure: float
    z_score: float
    direction: str
    is_extreme: bool
    timestamp: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class HLPSentiment:
    def __init__(self, coins: Optional[List[str]] = None):
        self.coins = coins or TRACKED_COINS
        self.rest = HyperliquidRESTClient()
        self._history: Dict[str, List[tuple]] = {coin: [] for coin in self.coins}
        self._latest: Dict[str, HLPSignal] = {}
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
            time.sleep(POLL_INTERVAL_HLP)

    def _poll_once(self) -> None:
        now = time.time()
        try:
            vault = self.rest.vault_details(HLP_VAULT)
            # Also get HLP positions via clearinghouseState
            hlp_state = self.rest.clearinghouse_state(HLP_VAULT)
            mids_resp = self.rest.all_mids()
            # all_mids returns dict with coin->price directly (no "mids" key sometimes)
            if isinstance(mids_resp, dict) and "mids" not in mids_resp:
                mids = mids_resp  # direct coin->price mapping
            else:
                mids = mids_resp.get("mids", mids_resp) if isinstance(mids_resp, dict) else {}
        except Exception:
            return
        exposures: Dict[str, float] = {coin: 0.0 for coin in self.coins}
        # Use clearinghouseState positions (more reliable)
        positions_list = hlp_state.get("assetPositions", [])
        for item in positions_list:
            pos = item.get("position", item)
            coin = pos.get("coin")
            if coin not in exposures:
                continue
            szi = float(pos.get("szi", 0.0))
            mid = float(mids.get(coin, 0.0))
            exposures[coin] = szi * mid
        # vault.portfolio is [["day", {...}], ...] — not useful for positions
        # clearinghouseState above is the reliable source
        with self._lock:
            for coin, exposure in exposures.items():
                hist = self._history[coin]
                hist.append((now, exposure))
                cutoff = now - 7 * 24 * 3600
                self._history[coin] = [(t, v) for t, v in hist if t >= cutoff]
                values = [v for _, v in self._history[coin]]
                z_score = 0.0
                if len(values) >= 5 and np.std(values) > 0:
                    z_score = (exposure - float(np.mean(values))) / float(np.std(values))
                direction = "FLAT"
                if exposure > 0:
                    direction = "LONG"
                elif exposure < 0:
                    direction = "SHORT"
                is_extreme = abs(z_score) >= 2.0
                self._latest[coin] = HLPSignal(
                    coin=coin,
                    hlp_exposure=exposure,
                    z_score=z_score,
                    direction=direction,
                    is_extreme=is_extreme,
                    timestamp=now,
                )

    def get_signals(self) -> List[HLPSignal]:
        with self._lock:
            return list(self._latest.values())


if __name__ == "__main__":
    hlp = HLPSentiment()
    hlp.start()
    try:
        time.sleep(5)
        sigs = hlp.get_signals()
        print(sigs[0].to_dict() if sigs else "No HLP signal yet.")
    finally:
        hlp.stop()
