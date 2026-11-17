import pandas as pd


def sma(prices: pd.Series, period: int) -> pd.Series:
    return prices.rolling(window=period).mean()


def ema(prices: pd.Series, period: int) -> pd.Series:
    return prices.ewm(span=period, adjust=False).mean()


def rsi(prices: pd.Series, period: int) -> pd.Series:
    delta = prices.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()

    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def macd(prices: pd.Series, fast: int, slow: int, signal: int) -> pd.DataFrame:
    macd_line = ema(prices, fast) - ema(prices, slow)
    signal_line = ema(macd_line, signal)
    return pd.DataFrame({
        "macd": macd_line,
        "signal": signal_line,
        "histogram": macd_line - signal_line,
    })


def compute_all(prices: pd.Series, cfg) -> pd.DataFrame:
    """prices: closing prices indexed oldest -> newest."""
    out = pd.DataFrame(index=prices.index)
    out["close"] = prices
    out["sma_fast"] = sma(prices, cfg.SMA_FAST)
    out["sma_slow"] = sma(prices, cfg.SMA_SLOW)
    out["rsi"] = rsi(prices, cfg.RSI_PERIOD)

    macd_df = macd(prices, cfg.MACD_FAST, cfg.MACD_SLOW, cfg.MACD_SIGNAL)
    out["macd"] = macd_df["macd"]
    out["macd_signal"] = macd_df["signal"]
    out["macd_hist"] = macd_df["histogram"]
    return out
