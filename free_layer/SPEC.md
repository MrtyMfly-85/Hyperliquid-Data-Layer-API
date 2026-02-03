# Free Hyperliquid Data Layer — Build Spec

## Overview
Build a Python data layer on top of Hyperliquid's free public API (REST + WebSocket) that replicates the most valuable signals from MoonDev's paid API. Zero cost, no auth required.

## Architecture

### Module: `free_layer/`
```
free_layer/
├── __init__.py
├── client.py          # Base REST + WebSocket client
├── orderflow.py       # Real-time order flow imbalance
├── whales.py          # Whale tracker (leaderboard + position monitoring)
├── hlp_sentiment.py   # HLP vault sentiment monitor
├── funding.py         # Funding rate anomaly detector
├── signals.py         # Unified signal aggregator
├── config.py          # Constants and configuration
└── demo.py            # Demo script showing all signals
```

## API Endpoints Used (all free, no auth)

### REST (`POST https://api.hyperliquid.xyz/info`)
- `allMids` — current mid prices for all assets
- `metaAndAssetCtxs` — metadata + funding rates + open interest for all 228 assets
- `l2Book` — order book (20 levels/side)
- `candleSnapshot` — OHLCV candles (1m to 1M, up to 5000 per request)
- `clearinghouseState` — user/vault positions, margin, PnL
- `vaultDetails` — HLP vault portfolio, APR, followers
- `userFills` / `userFillsByTime` — trade history for any address
- `historicalOrders` — order history for any address
- `fundingHistory` — historical funding rates per coin

### WebSocket (`wss://api.hyperliquid.xyz/ws`)
- `trades` — real-time trade stream (per coin)
- `l2Book` — real-time order book updates
- `activeAssetCtx` — real-time funding/OI changes
- `candle` — real-time candle updates

## Component Specs

### 1. `client.py` — Base Client
- REST client with rate limiting (best practice: ≤10 req/sec)
- WebSocket client with auto-reconnect
- Connection pooling via `requests.Session`
- Error handling and retries (3x with exponential backoff)
- All responses typed with dataclasses or TypedDicts

### 2. `orderflow.py` — Order Flow Imbalance
- Subscribe to WebSocket `trades` stream for ETH and SOL
- Aggregate buy vs sell volume in rolling windows: 5m, 15m, 1h, 4h
- Calculate imbalance ratio: `(buy_vol - sell_vol) / (buy_vol + sell_vol)`
- Track large trades (>$50k for ETH, >$25k for SOL)
- Output: `OrderFlowSignal(coin, window, imbalance, large_buy_count, large_sell_count, net_large_flow)`

### 3. `whales.py` — Whale Tracker
- On startup: fetch top traders from Hyperliquid leaderboard (scrape or API if available)
- Maintain a list of ~50 known whale addresses
- Poll positions every 60 seconds via `clearinghouseState`
- Detect position changes: new positions, size increases/decreases, closes
- Calculate whale consensus: % of tracked whales long vs short per coin
- Output: `WhaleSignal(coin, whale_long_pct, whale_short_pct, recent_changes: List[WhaleChange])`
- Allow manual addition of whale addresses (config file or method)

### 4. `hlp_sentiment.py` — HLP Sentiment
- Poll HLP vault (`0xdfc24b077bc1425ad1dea75bcb6f8158e10df303`) every 5 minutes
- Track portfolio value changes, position changes
- Calculate HLP positioning: what coins is HLP long/short?
- Compute z-score of HLP exposure vs rolling 7-day mean
- When HLP is heavily positioned one way, retail is likely the other side
- Output: `HLPSignal(coin, hlp_exposure, z_score, direction, is_extreme)`

### 5. `funding.py` — Funding Rate Anomaly
- Poll `metaAndAssetCtxs` every 5 minutes for all assets
- Track funding rate history in rolling 7-day window
- Calculate z-score of current funding vs recent history
- Extreme positive funding = too many longs (bearish signal)
- Extreme negative funding = too many shorts (bullish signal)
- Also track open interest changes (sudden OI drops = liquidation cascades)
- Output: `FundingSignal(coin, funding_rate, funding_zscore, oi, oi_change_pct, is_anomaly)`

### 6. `signals.py` — Unified Signal Aggregator
- Combines all signal sources into a single `MarketSignal` per coin
- Signal scoring: each component contributes -1 to +1 score
  - Order flow imbalance → bullish/bearish based on direction
  - Whale consensus → follow smart money direction
  - HLP sentiment → contrarian (fade HLP positioning)
  - Funding anomaly → contrarian (extreme funding = reversal)
- Composite score: weighted average (configurable weights)
- Default weights: orderflow=0.3, whales=0.25, hlp=0.25, funding=0.2
- Output: `CompositeSignal(coin, score, components: dict, timestamp, recommendation: str)`
  - recommendation: "STRONG_LONG" / "LEAN_LONG" / "NEUTRAL" / "LEAN_SHORT" / "STRONG_SHORT"

### 7. `config.py` — Configuration
```python
HYPERLIQUID_REST = "https://api.hyperliquid.xyz/info"
HYPERLIQUID_WS = "wss://api.hyperliquid.xyz/ws"
HLP_VAULT = "0xdfc24b077bc1425ad1dea75bcb6f8158e10df303"
TRACKED_COINS = ["ETH", "SOL"]
LARGE_TRADE_THRESHOLD = {"ETH": 50000, "SOL": 25000}  # USD
POLL_INTERVAL_POSITIONS = 60   # seconds
POLL_INTERVAL_FUNDING = 300    # seconds
POLL_INTERVAL_HLP = 300        # seconds
ORDERFLOW_WINDOWS = [300, 900, 3600, 14400]  # 5m, 15m, 1h, 4h in seconds
SIGNAL_WEIGHTS = {"orderflow": 0.3, "whales": 0.25, "hlp": 0.25, "funding": 0.2}
```

### 8. `demo.py` — Demo Script
- Starts all monitors
- Prints live dashboard to terminal every 30 seconds
- Shows: current price, order flow, whale consensus, HLP sentiment, funding, composite signal
- Runs until Ctrl+C

## Technical Requirements
- Python 3.9+
- Dependencies: `requests`, `websockets` (or `websocket-client`), `pandas`, `numpy`
- No paid API keys
- All data from Hyperliquid public endpoints
- Thread-safe (WebSocket in background thread, REST polling in main or separate threads)

## Integration Points
- Signal output should be importable by `backtest/ensemble_strategy.py`
- JSON-serializable signals for logging/storage
- Optional: save signals to CSV for later backtesting

## Testing
- `demo.py` should run standalone and show live data
- Each module should have a `if __name__ == '__main__'` block for standalone testing
- Verify all endpoints return expected data before building logic on top
