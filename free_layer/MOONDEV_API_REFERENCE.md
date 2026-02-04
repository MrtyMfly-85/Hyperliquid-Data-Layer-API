# MoonDev API Full Reference (scraped 2026-02-03)

Base URL: `https://api.moondev.com`
Auth: `X-API-Key` header or `?api_key=` query param
Rate Limit: 60 req/sec sustained, burst 200
Last updated: 2026-01-14

## Endpoint Catalog (90+ endpoints)

### Market Data (Hyperliquid proxy)
| Endpoint | Description | Free Alternative? |
|---|---|---|
| `GET /api/prices` | All 228 coin prices + funding + OI | ✅ `metaAndAssetCtxs` |
| `GET /api/price/{coin}` | Single coin bid/ask/spread | ✅ `allMids` + `l2Book` |
| `GET /api/orderbook/{coin}` | L2 book ~20 levels | ✅ `l2Book` |
| `GET /api/account/{address}` | Wallet state | ✅ `clearinghouseState` |
| `GET /api/fills/{address}` | Trade fills | ✅ `userFills` |
| `GET /api/candles/{coin}?interval=` | OHLCV candles | ✅ `candleSnapshot` |

### Core Data (Unique Value)
| Endpoint | Description | Free Alternative? |
|---|---|---|
| `GET /api/positions.json` | Top 50 positions ALL symbols (1s updates) | ⚠️ Partial - need whale addresses |
| `GET /api/positions/all.json` | All 148 symbols × top 50 positions (500KB) | ❌ No equivalent |
| `GET /api/whales.json` | Whale trades $25k+ (75 symbols incl HIP-3) | ⚠️ Partial - WS trade stream |
| `GET /api/buyers.json` | Buyers only $5k+ (HYPE/SOL/XRP/ETH) | ⚠️ WS trade stream |
| `GET /api/depositors.json` | ALL Hyperliquid depositors (125k+ addresses) | ❌ No equivalent |
| `GET /api/whale_addresses.txt` | 22,500+ whale addresses | ❌ This is THE goldmine |

### Tick Data (129 symbols)
| Endpoint | Description | Free Alternative? |
|---|---|---|
| `GET /api/ticks/{symbol}.json` | Current ticks | ✅ WS stream |
| `GET /api/ticks/{symbol}_{timeframe}.json` | Historical (10m-7d) | ⚠️ Limited via candleSnapshot |
| `GET /api/ticks/latest.json` | All 129 assets latest | ✅ allMids |
| `GET /api/ticks/stats.json` | Collection stats | ❌ |

### Trades & Order Flow (130 symbols) ⭐
| Endpoint | Description | Free Alternative? |
|---|---|---|
| `GET /api/trades.json` | Recent 1000 trades | ⚠️ WS stream (real-time only) |
| `GET /api/large_trades.json` | Trades >$100k | ⚠️ Filter WS stream |
| `GET /api/orderflow.json` | Order flow metrics | ✅ We built this! |
| `GET /api/orderflow/stats.json` | Flow statistics | ✅ We built this! |
| `GET /api/imbalance/{5m,15m,1h,4h,24h}.json` | Buy/sell imbalance ALL 130 symbols | ⚠️ We built for ETH/SOL only |

Data retention: Raw trades = 90 days, Hourly aggregates = permanent

### Hyperliquid Liquidations
| Endpoint | Description | Free Alternative? |
|---|---|---|
| `GET /api/liquidations/stats.json` | HL liquidation stats | ❌ |
| `GET /api/liquidations/{timeframe}.json` | HL liquidations (10m-30d) | ❌ |
| `GET /api/liquidations/scan_summary.json` | Recent scan results | ❌ |

### Multi-Exchange Liquidations ⭐⭐
| Endpoint | Description | Free Alternative? |
|---|---|---|
| `GET /api/all_liquidations/stats.json` | Combined Binance+Bybit+OKX | ❌ CoinGlass $29/mo |
| `GET /api/all_liquidations/{timeframe}.json` | Combined (10m-30d) | ❌ |
| `GET /api/binance_liquidations/{timeframe}.json` | Binance only | ❌ |
| `GET /api/bybit_liquidations/{timeframe}.json` | Bybit only | ❌ |
| `GET /api/okx_liquidations/{timeframe}.json` | OKX only | ❌ |

### HIP3 TradFi Liquidations
| Endpoint | Description | Free Alternative? |
|---|---|---|
| `GET /api/hip3_liquidations/stats.json` | TradFi liquidation stats | ❌ |
| `GET /api/hip3_liquidations/{timeframe}.json` | (10m, 1h, 24h, 7d) | ❌ |

### HIP3 Market Data (58 symbols across 5 dexes) ⭐
| Endpoint | Description | Free Alternative? |
|---|---|---|
| `GET /api/hip3/meta` | All 58 symbols + prices by dex | ❌ |
| `GET /api/hip3/prices` | All HIP3 prices | ❌ |
| `GET /api/hip3/price/{coin}` | Single HIP3 price | ❌ |
| `GET /api/hip3/candles/{coin}?interval=` | TradFi OHLCV | ❌ |
| `GET /api/hip3/ticks/{coin}?duration=` | TradFi tick data | ❌ |
| `GET /api/hip3_ticks/{dex}_{ticker}.json` | Per-dex tick data | ❌ |
| `GET /api/hip3_ticks/stats.json` | Tick collector stats | ❌ |

Dexes: xyz (27 stocks/commodities/FX), flx (7), vntl (7 pre-IPO/indices), hyna (12 crypto), km (5 US indices)
Notable: vntl:OPENAI, vntl:ANTHROPIC, vntl:SPACEX pre-IPO perps!

### Smart Money ⭐⭐⭐
| Endpoint | Description | Free Alternative? |
|---|---|---|
| `GET /api/smart_money/rankings.json` | Top 100 smart + Bottom 100 dumb money | ❌ THE goldmine |
| `GET /api/smart_money/leaderboard.json` | Top 50 performers + metrics | ❌ |
| `GET /api/smart_money/signals_{10m,1h,24h}.json` | Smart money trade signals | ❌ |

Rankings include: address, total_pnl, win_rate, total_trades
Signals include: address, action (open_long/short), coin, size, price, leverage

### HLP Analytics ⭐⭐⭐
| Endpoint | Description | Free Alternative? |
|---|---|---|
| `GET /api/hlp/positions` | All 7 HLP strategy positions + net exposure | ⚠️ clearinghouseState (no strategy breakdown) |
| `GET /api/hlp/trades?limit=N` | HLP trade fills (5,000+ collected) | ❌ |
| `GET /api/hlp/trades/stats` | Volume + fee statistics | ❌ |
| `GET /api/hlp/positions/history?hours=N` | Position snapshots over time | ❌ |
| `GET /api/hlp/liquidators` | Liquidator activation events | ❌ |
| `GET /api/hlp/deltas?hours=N` | Net exposure changes over time | ❌ |
| `GET /api/hlp/sentiment` | **Z-scores + trading signals** | ⚠️ We built basic version |
| `GET /api/hlp/liquidators/status` | Real-time liquidator active/idle + PnL | ❌ |
| `GET /api/hlp/market-maker` | Strategy B tracker (BTC/ETH/SOL) | ❌ |
| `GET /api/hlp/timing` | Hourly + session profitability | ❌ |
| `GET /api/hlp/correlation` | Delta-price correlation by coin | ❌ |

HLP has 7 strategies, $210M+ AUM. Sentiment endpoint is the crown jewel — z-score signals with confidence levels.

### Blockchain & Contracts
| Endpoint | Description | Free Alternative? |
|---|---|---|
| `GET /api/events.json` | Decoded blockchain events | ❌ |
| `GET /api/contracts.json` | 27 smart contracts registry | ❌ |

### User Data
| Endpoint | Description | Free Alternative? |
|---|---|---|
| `GET /api/user/{address}/positions` | Any wallet positions | ✅ clearinghouseState |
| `GET /api/user/{address}/fills?limit=N` | Any wallet fills (limit=-1 for ALL) | ✅ userFills |

## What's Actually Unique (Can't Replicate Free)

1. **Smart Money Rankings** — 3,488 tracked addresses, top 100 smart/bottom 100 dumb by PnL
2. **Smart Money Signals** — Real-time alerts when smart money opens/closes positions
3. **22,500+ Whale Addresses** — Continuously scanned with 200 threads
4. **Multi-Exchange Liquidations** — Binance + Bybit + OKX combined
5. **HLP Strategy Breakdown** — 7 individual strategies decomposed (not just aggregate)
6. **HLP Sentiment Z-Scores** — Pre-computed with confidence levels
7. **HLP Timing Analysis** — Hourly profitability patterns
8. **HIP-3 TradFi Data** — Stocks, commodities, FX, pre-IPO on Hyperliquid
9. **125k+ Depositor List** — Every wallet that ever bridged to Hyperliquid
10. **Historical Trade Data** — 90 days raw, permanent hourly aggregates

## What We Already Built (Free Layer)

1. ✅ Order flow imbalance (ETH/SOL via WebSocket)
2. ✅ Funding rate anomaly detection
3. ✅ HLP sentiment (basic — no strategy breakdown)
4. ✅ Whale tracking (needs address list — API has 22,500!)
5. ✅ Composite signal aggregator

## Priority Endpoints When We Get API Key

1. `/api/smart_money/rankings.json` — Get the address list, seed our whale tracker
2. `/api/whale_addresses.txt` — 22,500 addresses, immediate upgrade
3. `/api/hlp/sentiment` — Compare their z-scores to ours
4. `/api/all_liquidations/stats.json` — Multi-exchange liquidation data
5. `/api/imbalance/1h.json` — Compare their 130-symbol flow to our 2-symbol flow
6. `/api/hlp/positions` — Full 7-strategy breakdown

## API Key Scraper Script (for tomorrow's Zoom)

When we get the key, run `free_layer/scrape_moondev.py` to hit all endpoints and cache responses.
