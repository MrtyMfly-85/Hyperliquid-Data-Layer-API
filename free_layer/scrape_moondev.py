#!/usr/bin/env python3
"""
MoonDev API Scraper — Hit every endpoint, cache all responses.
Run this the moment you get an API key from the Zoom stream.

Usage:
    python scrape_moondev.py YOUR_API_KEY

Saves all responses to free_layer/moondev_cache/
"""

import json
import os
import sys
import time
from datetime import datetime

import requests

BASE_URL = "https://api.moondev.com"
CACHE_DIR = os.path.join(os.path.dirname(__file__), "moondev_cache")

# All endpoints to hit, grouped by priority
ENDPOINTS = {
    # PRIORITY 1: Unique data we can't get elsewhere
    "smart_money_rankings": "/api/smart_money/rankings.json",
    "smart_money_leaderboard": "/api/smart_money/leaderboard.json",
    "smart_money_signals_10m": "/api/smart_money/signals_10m.json",
    "smart_money_signals_1h": "/api/smart_money/signals_1h.json",
    "smart_money_signals_24h": "/api/smart_money/signals_24h.json",
    "whale_addresses": "/api/whale_addresses.txt",
    "depositors": "/api/depositors.json",

    # PRIORITY 2: HLP analytics
    "hlp_positions": "/api/hlp/positions",
    "hlp_positions_summary": "/api/hlp/positions?include_strategies=false",
    "hlp_trades": "/api/hlp/trades?limit=500",
    "hlp_trades_stats": "/api/hlp/trades/stats",
    "hlp_positions_history_24h": "/api/hlp/positions/history?hours=24",
    "hlp_positions_history_168h": "/api/hlp/positions/history?hours=168",
    "hlp_liquidators": "/api/hlp/liquidators",
    "hlp_deltas_24h": "/api/hlp/deltas?hours=24",
    "hlp_deltas_168h": "/api/hlp/deltas?hours=168",
    "hlp_sentiment": "/api/hlp/sentiment",
    "hlp_liquidators_status": "/api/hlp/liquidators/status",
    "hlp_market_maker": "/api/hlp/market-maker",
    "hlp_timing": "/api/hlp/timing",
    "hlp_correlation": "/api/hlp/correlation",

    # PRIORITY 3: Multi-exchange liquidations
    "all_liquidations_stats": "/api/all_liquidations/stats.json",
    "all_liquidations_1h": "/api/all_liquidations/1h.json",
    "all_liquidations_24h": "/api/all_liquidations/24h.json",
    "all_liquidations_7d": "/api/all_liquidations/7d.json",
    "binance_liquidations_stats": "/api/binance_liquidations/stats.json",
    "binance_liquidations_1h": "/api/binance_liquidations/1h.json",
    "bybit_liquidations_stats": "/api/bybit_liquidations/stats.json",
    "bybit_liquidations_1h": "/api/bybit_liquidations/1h.json",
    "okx_liquidations_stats": "/api/okx_liquidations/stats.json",
    "okx_liquidations_1h": "/api/okx_liquidations/1h.json",

    # PRIORITY 4: Hyperliquid liquidations
    "hl_liquidations_stats": "/api/liquidations/stats.json",
    "hl_liquidations_scan": "/api/liquidations/scan_summary.json",
    "hl_liquidations_1h": "/api/liquidations/1h.json",
    "hl_liquidations_24h": "/api/liquidations/24h.json",
    "hl_liquidations_7d": "/api/liquidations/7d.json",

    # PRIORITY 5: HIP3 TradFi
    "hip3_liquidations_stats": "/api/hip3_liquidations/stats.json",
    "hip3_liquidations_1h": "/api/hip3_liquidations/1h.json",
    "hip3_meta": "/api/hip3/meta",
    "hip3_prices": "/api/hip3/prices",
    "hip3_candles_symbols": "/api/hip3/candles/symbols",
    "hip3_ticks_stats": "/api/hip3_ticks/stats.json",

    # PRIORITY 6: Order flow & trades
    "trades": "/api/trades.json",
    "large_trades": "/api/large_trades.json",
    "orderflow": "/api/orderflow.json",
    "orderflow_stats": "/api/orderflow/stats.json",
    "imbalance_5m": "/api/imbalance/5m.json",
    "imbalance_15m": "/api/imbalance/15m.json",
    "imbalance_1h": "/api/imbalance/1h.json",
    "imbalance_4h": "/api/imbalance/4h.json",
    "imbalance_24h": "/api/imbalance/24h.json",

    # PRIORITY 7: Core data
    "positions": "/api/positions.json",
    "positions_all": "/api/positions/all.json",
    "whales": "/api/whales.json",
    "buyers": "/api/buyers.json",
    "events": "/api/events.json",
    "contracts": "/api/contracts.json",

    # PRIORITY 8: Market data (we can get free, but compare formats)
    "prices": "/api/prices",
    "price_btc": "/api/price/BTC",
    "price_eth": "/api/price/ETH",
    "price_sol": "/api/price/SOL",
    "ticks_stats": "/api/ticks/stats.json",
    "ticks_latest": "/api/ticks/latest.json",
    "ticks_btc_1h": "/api/ticks/btc_1h.json",
    "ticks_eth_1h": "/api/ticks/eth_1h.json",
    "ticks_sol_1h": "/api/ticks/sol_1h.json",

    # Health
    "health": "/health",
}


def scrape(api_key: str) -> None:
    os.makedirs(CACHE_DIR, exist_ok=True)
    session = requests.Session()
    session.headers["X-API-Key"] = api_key

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results = {"timestamp": timestamp, "endpoints": {}}
    total = len(ENDPOINTS)
    success = 0
    failed = 0

    print(f"🚀 MoonDev API Scraper — {total} endpoints")
    print(f"   Key: {api_key[:8]}...{api_key[-4:]}")
    print(f"   Cache: {CACHE_DIR}/")
    print("=" * 60)

    for name, path in ENDPOINTS.items():
        url = f"{BASE_URL}{path}"
        try:
            t0 = time.time()
            resp = session.get(url, timeout=30)
            elapsed = time.time() - t0

            # Save response
            is_text = path.endswith(".txt")
            ext = "txt" if is_text else "json"
            filename = f"{name}.{ext}"
            filepath = os.path.join(CACHE_DIR, filename)

            if is_text:
                with open(filepath, "w") as f:
                    f.write(resp.text)
                size = len(resp.text)
            else:
                try:
                    data = resp.json()
                    with open(filepath, "w") as f:
                        json.dump(data, f, indent=2)
                    size = len(json.dumps(data))
                except Exception:
                    with open(filepath, "w") as f:
                        f.write(resp.text)
                    size = len(resp.text)

            status = "✅" if resp.status_code == 200 else f"⚠️ {resp.status_code}"
            print(f"  {status} {name} ({size:,} bytes, {elapsed:.1f}s)")
            results["endpoints"][name] = {
                "url": url,
                "status": resp.status_code,
                "size": size,
                "elapsed": round(elapsed, 2),
            }
            success += 1

        except Exception as e:
            print(f"  ❌ {name}: {e}")
            results["endpoints"][name] = {"url": url, "error": str(e)}
            failed += 1

        # Small delay to be polite
        time.sleep(0.1)

    # Save manifest
    manifest_path = os.path.join(CACHE_DIR, f"_manifest_{timestamp}.json")
    with open(manifest_path, "w") as f:
        json.dump(results, f, indent=2)

    print("=" * 60)
    print(f"Done! {success}/{total} succeeded, {failed} failed")
    print(f"Manifest: {manifest_path}")

    # Summary of most valuable data
    print("\n🏆 Key files to review:")
    for key in ["smart_money_rankings", "whale_addresses", "hlp_sentiment",
                 "all_liquidations_stats", "imbalance_1h"]:
        fp = os.path.join(CACHE_DIR, f"{key}.json")
        if not fp.endswith(".json"):
            fp = os.path.join(CACHE_DIR, f"{key}.txt")
        if os.path.exists(fp):
            sz = os.path.getsize(fp)
            print(f"  📁 {key}: {sz:,} bytes")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scrape_moondev.py YOUR_API_KEY")
        print("\nGet the key from MoonDev's Zoom stream, then run this immediately.")
        sys.exit(1)

    scrape(sys.argv[1])
