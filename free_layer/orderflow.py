"""Real-time order flow imbalance from WebSocket trade stream."""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque
from dataclasses import asdict, dataclass
from typing import Any, Deque, Dict, List, Optional, Tuple

from .client import HyperliquidWSClient
from .config import LARGE_TRADE_THRESHOLD, ORDERFLOW_WINDOWS, TRACKED_COINS


@dataclass
class OrderFlowSignal:
    coin: str
    window: int
    imbalance: float
    large_buy_count: int
    large_sell_count: int
    net_large_flow: float
    timestamp: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class OrderFlowImbalance:
    def __init__(self, coins: Optional[List[str]] = None):
        self.coins = coins or TRACKED_COINS
        self._trades: Dict[str, Deque[Tuple[float, str, float]]] = {
            coin: deque() for coin in self.coins
        }
        self._lock = threading.Lock()
        self._ws = HyperliquidWSClient(on_message=self._on_message)

    def start(self) -> None:
        self._ws.start()
        for coin in self.coins:
            self._ws.subscribe_trades(coin)

    def stop(self) -> None:
        self._ws.stop()

    def _on_message(self, msg: Dict[str, Any]) -> None:
        data = msg.get("data")
        if not data:
            return
        channel = msg.get("channel") or msg.get("type")
        if channel != "trades":
            return
        trades = data if isinstance(data, list) else data.get("trades", [])
        now = time.time()
        with self._lock:
            for trade in trades:
                coin = trade.get("coin") or trade.get("symbol")
                if coin not in self.coins:
                    continue
                side = trade.get("side") or trade.get("dir") or trade.get("takerSide")
                side = "B" if str(side).upper().startswith("B") else "S"
                px = float(trade.get("px") or trade.get("price") or 0.0)
                sz = float(trade.get("sz") or trade.get("size") or trade.get("qty") or 0.0)
                usd = float(trade.get("usd")) if trade.get("usd") is not None else px * sz
                self._trades[coin].append((now, side, usd))
        self._trim(now)

    def _trim(self, now: float) -> None:
        max_window = max(ORDERFLOW_WINDOWS)
        cutoff = now - max_window
        with self._lock:
            for coin in self.coins:
                dq = self._trades[coin]
                while dq and dq[0][0] < cutoff:
                    dq.popleft()

    def get_signals(self) -> List[OrderFlowSignal]:
        now = time.time()
        signals: List[OrderFlowSignal] = []
        with self._lock:
            for coin in self.coins:
                trades = list(self._trades[coin])
                for window in ORDERFLOW_WINDOWS:
                    cutoff = now - window
                    buy_vol = 0.0
                    sell_vol = 0.0
                    large_buy = 0
                    large_sell = 0
                    net_large_flow = 0.0
                    threshold = LARGE_TRADE_THRESHOLD.get(coin, 0)
                    for ts, side, usd in trades:
                        if ts < cutoff:
                            continue
                        if side == "B":
                            buy_vol += usd
                        else:
                            sell_vol += usd
                        if usd >= threshold and threshold > 0:
                            if side == "B":
                                large_buy += 1
                                net_large_flow += usd
                            else:
                                large_sell += 1
                                net_large_flow -= usd
                    denom = buy_vol + sell_vol
                    imbalance = (buy_vol - sell_vol) / denom if denom > 0 else 0.0
                    signals.append(
                        OrderFlowSignal(
                            coin=coin,
                            window=window,
                            imbalance=imbalance,
                            large_buy_count=large_buy,
                            large_sell_count=large_sell,
                            net_large_flow=net_large_flow,
                            timestamp=now,
                        )
                    )
        return signals


if __name__ == "__main__":
    of = OrderFlowImbalance()
    of.start()
    try:
        for _ in range(3):
            time.sleep(10)
            sigs = of.get_signals()
            print(f"Orderflow signals: {len(sigs)}")
            if sigs:
                print(sigs[0].to_dict())
    finally:
        of.stop()
