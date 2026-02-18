"""OANDA Data Fetcher

Fetches live and historical OHLCV data from OANDA's v20 REST API.
"""

import os
import requests
from datetime import datetime, timedelta
from typing import Optional, List
import pandas as pd
from dataclasses import dataclass, field

from ict_agent.data.fetcher import BaseDataFetcher, DataConfig


def _env_api_key() -> str:
    return os.environ.get("OANDA_API_KEY", "")


def _env_account_id() -> str:
    return os.environ.get("OANDA_ACCOUNT_ID", "")


def _env_environment() -> str:
    return os.environ.get("OANDA_ENV", "practice")


@dataclass
class OANDAConfig:
    """OANDA API Configuration — reads from env vars by default"""

    api_key: str = field(default_factory=_env_api_key)
    account_id: str = field(default_factory=_env_account_id)
    environment: str = field(default_factory=_env_environment)

    @property
    def base_url(self) -> str:
        # Check OANDA_ENV (case-insensitive)
        if self.environment.lower() == "live":
            return "https://api-fxtrade.oanda.com"
        return "https://api-fxpractice.oanda.com"

    @property
    def stream_url(self) -> str:
        if self.environment.lower() == "live":
            return "https://stream-fxtrade.oanda.com"
        return "https://stream-fxpractice.oanda.com"


class OANDAFetcher(BaseDataFetcher):
    """Fetch data from OANDA v20 API"""

    # OANDA instrument naming
    FOREX_SYMBOLS = {
        "EURUSD": "EUR_USD",
        "GBPUSD": "GBP_USD",
        "USDJPY": "USD_JPY",
        "AUDUSD": "AUD_USD",
        "USDCAD": "USD_CAD",
        "USDCHF": "USD_CHF",
        "NZDUSD": "NZD_USD",
        "EURGBP": "EUR_GBP",
        "EURJPY": "EUR_JPY",
        "GBPJPY": "GBP_JPY",
        "XAUUSD": "XAU_USD",
        "XAGUSD": "XAG_USD",
        "US30": "US30_USD",
        "SPX500": "SPX500_USD",
        "NAS100": "NAS100_USD",
    }

    # OANDA granularity mapping
    TIMEFRAME_MAP = {
        "1m": "M1",
        "5m": "M5",
        "15m": "M15",
        "30m": "M30",
        "1h": "H1",
        "4h": "H4",
        "1d": "D",
        "1w": "W",
        "1M": "M",
        # Also accept OANDA format directly
        "M1": "M1",
        "M5": "M5",
        "M15": "M15",
        "M30": "M30",
        "H1": "H1",
        "H4": "H4",
        "D": "D",
        "W": "W",
    }

    def __init__(self, config: Optional[OANDAConfig] = None):
        self.config = config or OANDAConfig()
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json",
            }
        )

    def _get_instrument(self, symbol: str) -> str:
        """Convert symbol to OANDA instrument format"""
        symbol_upper = symbol.upper().replace("/", "").replace("_", "")
        return self.FOREX_SYMBOLS.get(symbol_upper, symbol.replace("/", "_"))

    def _get_granularity(self, timeframe: str) -> str:
        """Convert timeframe to OANDA granularity"""
        return self.TIMEFRAME_MAP.get(timeframe, timeframe)

    def fetch(self, config: DataConfig) -> pd.DataFrame:
        """
        Fetch OHLCV data from OANDA.

        Args:
            config: DataConfig with symbol, timeframe, dates, limit

        Returns:
            DataFrame with OHLCV data and DatetimeIndex
        """
        instrument = self._get_instrument(config.symbol)
        granularity = self._get_granularity(config.timeframe)

        params = {
            "granularity": granularity,
            "price": "MBA",  # Mid, Bid, Ask
        }

        if config.start_date and config.end_date:
            params["from"] = config.start_date.strftime("%Y-%m-%dT%H:%M:%SZ")
            params["to"] = config.end_date.strftime("%Y-%m-%dT%H:%M:%SZ")
        else:
            params["count"] = min(config.limit, 5000)  # OANDA max is 5000

        url = f"{self.config.base_url}/v3/instruments/{instrument}/candles"

        response = self.session.get(url, params=params)
        response.raise_for_status()

        data = response.json()

        return self._parse_candles(data.get("candles", []))

    def _parse_candles(self, candles: List[dict]) -> pd.DataFrame:
        """Parse OANDA candle response to DataFrame"""

        if not candles:
            return pd.DataFrame()

        rows = []
        for candle in candles:
            if not candle.get("complete", True):
                continue  # Skip incomplete candles

            # Use mid prices
            mid = candle.get("mid", {})

            rows.append(
                {
                    "timestamp": pd.to_datetime(candle["time"]),
                    "open": float(mid.get("o", 0)),
                    "high": float(mid.get("h", 0)),
                    "low": float(mid.get("l", 0)),
                    "close": float(mid.get("c", 0)),
                    "volume": int(candle.get("volume", 0)),
                }
            )

        df = pd.DataFrame(rows)
        if not df.empty:
            df.set_index("timestamp", inplace=True)
            df.sort_index(inplace=True)

        return df

    def fetch_latest(
        self,
        symbol: str,
        timeframe: str = "5m",
        count: int = 100,
    ) -> pd.DataFrame:
        """
        Fetch latest candles for a symbol.

        Args:
            symbol: Trading symbol (e.g., "EURUSD")
            timeframe: Candle timeframe
            count: Number of candles to fetch

        Returns:
            DataFrame with OHLCV data
        """
        config = DataConfig(
            symbol=symbol,
            timeframe=timeframe,
            limit=count,
        )
        return self.fetch(config)

    def get_current_price(self, symbol: str) -> dict:
        """
        Get current bid/ask price for a symbol.

        Args:
            symbol: Trading symbol

        Returns:
            Dict with bid, ask, mid prices
        """
        instrument = self._get_instrument(symbol)
        url = f"{self.config.base_url}/v3/instruments/{instrument}/candles"

        params = {
            "granularity": "S5",  # 5-second candles
            "count": 1,
            "price": "MBA",
        }

        response = self.session.get(url, params=params)
        response.raise_for_status()

        data = response.json()
        candles = data.get("candles", [])

        if candles:
            candle = candles[-1]
            return {
                "bid": float(candle.get("bid", {}).get("c", 0)),
                "ask": float(candle.get("ask", {}).get("c", 0)),
                "mid": float(candle.get("mid", {}).get("c", 0)),
                "time": candle.get("time"),
            }

        return {}

    def get_spread(self, symbol: str) -> float:
        """Get current spread in pips"""
        price = self.get_current_price(symbol)
        if price:
            spread = price["ask"] - price["bid"]
            # Convert to pips
            if "JPY" in symbol.upper():
                return spread * 100
            return spread * 10000
        return 0.0

    def get_available_symbols(self) -> List[str]:
        """Get list of available instruments"""
        url = f"{self.config.base_url}/v3/accounts/{self.config.account_id}/instruments"

        try:
            response = self.session.get(url)
            response.raise_for_status()
            data = response.json()
            return [inst["name"] for inst in data.get("instruments", [])]
        except:
            # Return default forex pairs if account not set
            return list(self.FOREX_SYMBOLS.values())

    def get_account_summary(self) -> dict:
        """Get account summary (requires account_id)"""
        if not self.config.account_id:
            return {"error": "account_id not configured"}

        url = f"{self.config.base_url}/v3/accounts/{self.config.account_id}/summary"
        response = self.session.get(url)
        response.raise_for_status()
        return response.json()


# Convenience function
def get_oanda_data(
    symbol: str,
    timeframe: str = "5m",
    count: int = 200,
) -> pd.DataFrame:
    """
    Quick function to fetch OANDA data.

    Args:
        symbol: Trading symbol (e.g., "EURUSD", "EUR_USD")
        timeframe: Candle timeframe (e.g., "1m", "5m", "15m", "1h", "4h", "1d")
        count: Number of candles

    Returns:
        DataFrame with OHLCV data

    Example:
        df = get_oanda_data("EURUSD", "5m", 200)
    """
    fetcher = OANDAFetcher()
    return fetcher.fetch_latest(symbol, timeframe, count)


def get_current_price(symbol: str) -> dict:
    """
    Quick function to get current price for a symbol.

    Args:
        symbol: Trading symbol (e.g., "EUR_USD", "EURUSD")

    Returns:
        Dict with 'bid', 'ask', 'mid' prices

    Example:
        price = get_current_price("EUR_USD")
        print(f"Bid: {price['bid']}, Ask: {price['ask']}")
    """
    fetcher = OANDAFetcher()
    return fetcher.get_current_price(symbol)


# Quick test
if __name__ == "__main__":
    print("Testing OANDA connection...")

    fetcher = OANDAFetcher()

    # Test fetching EUR/USD
    print("\nFetching EUR/USD 5m candles...")
    df = fetcher.fetch_latest("EURUSD", "5m", 10)

    if not df.empty:
        print(f"✅ Successfully fetched {len(df)} candles")
        print(f"\nLatest candles:")
        print(df.tail())

        # Get current price
        print("\nCurrent price:")
        price = fetcher.get_current_price("EURUSD")
        print(f"  Bid: {price.get('bid')}")
        print(f"  Ask: {price.get('ask')}")
        print(f"  Spread: {fetcher.get_spread('EURUSD'):.1f} pips")
    else:
        print("❌ No data returned")
