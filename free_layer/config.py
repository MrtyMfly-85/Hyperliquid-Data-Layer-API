"""Configuration constants for the free Hyperliquid data layer."""

HYPERLIQUID_REST = "https://api.hyperliquid.xyz/info"
HYPERLIQUID_WS = "wss://api.hyperliquid.xyz/ws"

HLP_VAULT = "0xdfc24b077bc1425ad1dea75bcb6f8158e10df303"

TRACKED_COINS = ["ETH", "SOL"]
LARGE_TRADE_THRESHOLD = {"ETH": 50000, "SOL": 25000}  # USD

POLL_INTERVAL_POSITIONS = 60  # seconds
POLL_INTERVAL_FUNDING = 300  # seconds
POLL_INTERVAL_HLP = 300  # seconds

ORDERFLOW_WINDOWS = [300, 900, 3600, 14400]  # 5m, 15m, 1h, 4h in seconds

SIGNAL_WEIGHTS = {
    "orderflow": 0.3,
    "whales": 0.25,
    "hlp": 0.25,
    "funding": 0.2,
}

# Optional manual whales can be added here.
DEFAULT_WHALES = []

