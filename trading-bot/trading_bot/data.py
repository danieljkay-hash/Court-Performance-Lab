"""Historical and latest price bars.

Pulls from Alpaca's market-data API and caches to CSV so repeated backtests
work offline. CSV cache lives in ./data_cache (gitignored).
"""
from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

import pandas as pd

CACHE_DIR = Path(os.getenv("DATA_CACHE_DIR", "data_cache"))

_TIMEFRAME_MAP = {
    "1Min": ("Minute", 1),
    "5Min": ("Minute", 5),
    "15Min": ("Minute", 15),
    "1Hour": ("Hour", 1),
    "1Day": ("Day", 1),
}


def _alpaca_timeframe(timeframe: str):
    from alpaca.data.timeframe import TimeFrame, TimeFrameUnit

    if timeframe not in _TIMEFRAME_MAP:
        raise ValueError(
            f"Unsupported timeframe {timeframe!r}. Choose from {list(_TIMEFRAME_MAP)}"
        )
    unit_name, amount = _TIMEFRAME_MAP[timeframe]
    return TimeFrame(amount, getattr(TimeFrameUnit, unit_name))


def _cache_path(symbol: str, timeframe: str, start: str, end: str) -> Path:
    return CACHE_DIR / f"{symbol}_{timeframe}_{start}_{end}.csv"


def get_historical_bars(
    symbol: str,
    timeframe: str,
    start: str,
    end: str,
    api_key: str | None = None,
    secret_key: str | None = None,
    use_cache: bool = True,
) -> pd.DataFrame:
    """Return OHLCV bars indexed by timestamp.

    Dates are 'YYYY-MM-DD'. Uses CSV cache when available unless use_cache=False.
    """
    cache = _cache_path(symbol, timeframe, start, end)
    if use_cache and cache.exists():
        df = pd.read_csv(cache, parse_dates=["timestamp"], index_col="timestamp")
        return df

    from alpaca.data.historical import StockHistoricalDataClient
    from alpaca.data.requests import StockBarsRequest

    key = api_key or os.getenv("ALPACA_API_KEY")
    secret = secret_key or os.getenv("ALPACA_SECRET_KEY")
    if not key or not secret:
        raise ValueError(
            "No cached data and no API keys available to fetch it. Set "
            "ALPACA_API_KEY / ALPACA_SECRET_KEY."
        )

    client = StockHistoricalDataClient(key, secret)
    req = StockBarsRequest(
        symbol_or_symbols=symbol,
        timeframe=_alpaca_timeframe(timeframe),
        start=datetime.fromisoformat(start),
        end=datetime.fromisoformat(end),
    )
    bars = client.get_stock_bars(req)
    df = bars.df
    if df.empty:
        raise ValueError(f"No data returned for {symbol} {start}..{end}")
    # Multi-index (symbol, timestamp) -> single symbol frame indexed by time.
    if isinstance(df.index, pd.MultiIndex):
        df = df.xs(symbol, level="symbol")
    df.index.name = "timestamp"
    df = df[["open", "high", "low", "close", "volume"]]

    if use_cache:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        df.to_csv(cache)
    return df


def get_latest_bars(
    symbol: str, timeframe: str, lookback: int, api_key: str, secret_key: str
) -> pd.DataFrame:
    """Return the most recent `lookback` bars for live/paper signal generation."""
    from alpaca.data.historical import StockHistoricalDataClient
    from alpaca.data.requests import StockBarsRequest

    client = StockHistoricalDataClient(api_key, secret_key)
    # Pull a generous window and trim; Day bars need calendar slack for weekends.
    multiplier = {"Minute": 1, "Hour": 1, "Day": 2}[_TIMEFRAME_MAP[timeframe][0]]
    span_days = max(5, lookback * multiplier)
    req = StockBarsRequest(
        symbol_or_symbols=symbol,
        timeframe=_alpaca_timeframe(timeframe),
        start=pd.Timestamp.utcnow() - pd.Timedelta(days=span_days),
    )
    df = client.get_stock_bars(req).df
    if df.empty:
        raise ValueError(f"No recent data for {symbol}")
    if isinstance(df.index, pd.MultiIndex):
        df = df.xs(symbol, level="symbol")
    df.index.name = "timestamp"
    return df[["open", "high", "low", "close", "volume"]].tail(lookback)
