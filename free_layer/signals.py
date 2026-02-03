"""Unified signal aggregator combining all sources."""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional

from .config import SIGNAL_WEIGHTS, TRACKED_COINS
from .funding import FundingAnomalyDetector, FundingSignal
from .hlp_sentiment import HLPSentiment, HLPSignal
from .orderflow import OrderFlowImbalance, OrderFlowSignal
from .whales import WhaleSignal, WhaleTracker


@dataclass
class CompositeSignal:
    coin: str
    score: float
    components: Dict[str, float]
    timestamp: float
    recommendation: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class SignalAggregator:
    def __init__(
        self,
        coins: Optional[List[str]] = None,
        orderflow: Optional[OrderFlowImbalance] = None,
        whales: Optional[WhaleTracker] = None,
        hlp: Optional[HLPSentiment] = None,
        funding: Optional[FundingAnomalyDetector] = None,
    ):
        self.coins = coins or TRACKED_COINS
        self.orderflow = orderflow or OrderFlowImbalance(self.coins)
        self.whales = whales or WhaleTracker(self.coins)
        self.hlp = hlp or HLPSentiment(self.coins)
        self.funding = funding or FundingAnomalyDetector(self.coins)

    def start(self) -> None:
        self.orderflow.start()
        self.whales.start()
        self.hlp.start()
        self.funding.start()

    def stop(self) -> None:
        self.orderflow.stop()
        self.whales.stop()
        self.hlp.stop()
        self.funding.stop()

    def _orderflow_score(self, signals: List[OrderFlowSignal]) -> float:
        if not signals:
            return 0.0
        return sum(s.imbalance for s in signals) / len(signals)

    def _whale_score(self, signal: Optional[WhaleSignal]) -> float:
        if not signal:
            return 0.0
        return (signal.whale_long_pct - signal.whale_short_pct) / 100.0

    def _hlp_score(self, signal: Optional[HLPSignal]) -> float:
        if not signal:
            return 0.0
        if signal.direction == "LONG":
            return -min(1.0, abs(signal.z_score) / 2.0)
        if signal.direction == "SHORT":
            return min(1.0, abs(signal.z_score) / 2.0)
        return 0.0

    def _funding_score(self, signal: Optional[FundingSignal]) -> float:
        if not signal:
            return 0.0
        if signal.funding_zscore > 0:
            return -min(1.0, abs(signal.funding_zscore) / 2.0)
        if signal.funding_zscore < 0:
            return min(1.0, abs(signal.funding_zscore) / 2.0)
        return 0.0

    def get_composite_signals(self) -> List[CompositeSignal]:
        now = time.time()
        orderflow_signals = self.orderflow.get_signals()
        whale_signals = {s.coin: s for s in self.whales.get_signals()}
        hlp_signals = {s.coin: s for s in self.hlp.get_signals()}
        funding_signals = {s.coin: s for s in self.funding.get_signals()}

        composites: List[CompositeSignal] = []
        for coin in self.coins:
            of = [s for s in orderflow_signals if s.coin == coin]
            orderflow_score = self._orderflow_score(of)
            whale_score = self._whale_score(whale_signals.get(coin))
            hlp_score = self._hlp_score(hlp_signals.get(coin))
            funding_score = self._funding_score(funding_signals.get(coin))

            weights = SIGNAL_WEIGHTS
            weighted = (
                orderflow_score * weights.get("orderflow", 0.0)
                + whale_score * weights.get("whales", 0.0)
                + hlp_score * weights.get("hlp", 0.0)
                + funding_score * weights.get("funding", 0.0)
            )
            recommendation = "NEUTRAL"
            if weighted >= 0.6:
                recommendation = "STRONG_LONG"
            elif weighted >= 0.2:
                recommendation = "LEAN_LONG"
            elif weighted <= -0.6:
                recommendation = "STRONG_SHORT"
            elif weighted <= -0.2:
                recommendation = "LEAN_SHORT"

            composites.append(
                CompositeSignal(
                    coin=coin,
                    score=weighted,
                    components={
                        "orderflow": orderflow_score,
                        "whales": whale_score,
                        "hlp": hlp_score,
                        "funding": funding_score,
                    },
                    timestamp=now,
                    recommendation=recommendation,
                )
            )
        return composites


if __name__ == "__main__":
    agg = SignalAggregator()
    agg.start()
    try:
        time.sleep(10)
        signals = agg.get_composite_signals()
        print(signals[0].to_dict() if signals else "No composite signals yet.")
    finally:
        agg.stop()
