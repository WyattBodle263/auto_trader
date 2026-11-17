from datetime import datetime, timedelta

import pandas as pd
import requests
from alpaca.data.enums import DataFeed
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame

ALPHA_VANTAGE_URL = "https://www.alphavantage.co/query"


class MarketDataError(Exception):
    pass


def get_daily_closes_alpaca(symbol: str, cfg, lookback_days: int = 150) -> pd.Series:
    """Returns daily closing prices for `symbol`, oldest -> newest, using
    Alpaca's own market data (free with any Alpaca account, much higher rate
    limit than Alpha Vantage's free tier). Used by auto_trade.py.
    """
    client = StockHistoricalDataClient(cfg.ALPACA_API_KEY, cfg.ALPACA_SECRET_KEY)
    request = StockBarsRequest(
        symbol_or_symbols=symbol,
        timeframe=TimeFrame.Day,
        start=datetime.utcnow() - timedelta(days=lookback_days),
        feed=DataFeed.IEX,
    )
    bars = client.get_stock_bars(request)
    rows = bars.data.get(symbol, [])
    if not rows:
        raise MarketDataError(f"No price data for {symbol}")

    closes = {bar.timestamp: float(bar.close) for bar in rows}
    return pd.Series(closes).sort_index()


def get_daily_closes(symbol: str, api_key: str, outputsize: str = "compact") -> pd.Series:
    """Returns daily closing prices for `symbol`, oldest -> newest.

    outputsize="compact" = last ~100 trading days (enough for SMA50/RSI14/MACD).
    Use "full" if you raise SMA_SLOW above ~80.
    """
    resp = requests.get(
        ALPHA_VANTAGE_URL,
        params={
            "function": "TIME_SERIES_DAILY",
            "symbol": symbol,
            "outputsize": outputsize,
            "apikey": api_key,
        },
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()

    series = data.get("Time Series (Daily)")
    if series is None:
        raise MarketDataError(f"No price data for {symbol}: {data}")

    closes = {date: float(values["4. close"]) for date, values in series.items()}
    s = pd.Series(closes).sort_index()
    s.index = pd.to_datetime(s.index)
    return s
