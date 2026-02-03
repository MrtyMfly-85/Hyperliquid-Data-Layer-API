"""Live dashboard showing all signals."""

from __future__ import annotations

import sys
import time

# Force unbuffered output
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(line_buffering=True)

from .client import HyperliquidRESTClient
from .config import TRACKED_COINS
from .signals import SignalAggregator


def _fmt_float(value: float) -> str:
    return f"{value:.4f}"


def run_dashboard() -> None:
    rest = HyperliquidRESTClient()
    aggregator = SignalAggregator()
    aggregator.start()
    print("Starting data layer... (first signals may take a few seconds)")
    import time as _t; _t.sleep(3)  # Give pollers a moment to fetch
    try:
        first = True
        while True:
            try:
                mids_resp = rest.all_mids()
                # all_mids returns flat dict {coin: price} directly
                mids = mids_resp if isinstance(mids_resp, dict) else {}
            except Exception:
                mids = {}
            orderflow = aggregator.orderflow.get_signals()
            whales = {s.coin: s for s in aggregator.whales.get_signals()}
            hlp = {s.coin: s for s in aggregator.hlp.get_signals()}
            funding = {s.coin: s for s in aggregator.funding.get_signals()}
            composite = {s.coin: s for s in aggregator.get_composite_signals()}

            print("\n" + "=" * 92)
            print(f"Hyperliquid Free Data Layer | {time.strftime('%Y-%m-%d %H:%M:%S')}")
            print("=" * 92)
            header = (
                "COIN  PRICE     OFLOW(5m)  WHALES(L/S)     HLP(Z)     FUND(Z)    SCORE  RECO"
            )
            print(header)
            for coin in TRACKED_COINS:
                price = float(mids.get(coin, 0.0))
                oflow_5m = 0.0
                for sig in orderflow:
                    if sig.coin == coin and sig.window == 300:
                        oflow_5m = sig.imbalance
                        break
                whale_sig = whales.get(coin)
                whale_str = "0/0"
                if whale_sig:
                    whale_str = f"{whale_sig.whale_long_pct:.0f}/{whale_sig.whale_short_pct:.0f}"
                hlp_sig = hlp.get(coin)
                hlp_z = hlp_sig.z_score if hlp_sig else 0.0
                funding_sig = funding.get(coin)
                fund_z = funding_sig.funding_zscore if funding_sig else 0.0
                comp = composite.get(coin)
                score = comp.score if comp else 0.0
                reco = comp.recommendation if comp else "NEUTRAL"
                line = (
                    f"{coin:<4}  {price:>8.2f}  {_fmt_float(oflow_5m):>9}  "
                    f"{whale_str:>12}  {_fmt_float(hlp_z):>7}  {_fmt_float(fund_z):>7}  "
                    f"{_fmt_float(score):>6}  {reco}"
                )
                print(line)
            if first:
                first = False
            time.sleep(30)
    except KeyboardInterrupt:
        print("\nStopping dashboard...")
    finally:
        aggregator.stop()


if __name__ == "__main__":
    run_dashboard()
