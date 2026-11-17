from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from . import indicators


@dataclass
class Signal:
    symbol: str
    action: str  # "BUY", "SELL", or "HOLD"
    reason: str


def _macd_crossed(row, prev_row) -> str | None:
    if prev_row["macd"] <= prev_row["macd_signal"] and row["macd"] > row["macd_signal"]:
        return "bullish"
    if prev_row["macd"] >= prev_row["macd_signal"] and row["macd"] < row["macd_signal"]:
        return "bearish"
    return None


def evaluate(symbol: str, closes: pd.Series, cfg) -> Signal:
    """Trend (SMA fast/slow) confirmed by momentum (MACD crossover), with RSI
    as a guard rail against chasing an already-overbought/oversold move.

    A signal only fires when trend direction and a fresh MACD crossover agree.
    Everything else is HOLD -- this is deliberately conservative to cut down
    on false positives.
    """
    df = indicators.compute_all(closes, cfg)
    if len(df) < 2 or df.iloc[-1].isna().any():
        return Signal(symbol, "HOLD", "not enough price history yet")

    row, prev_row = df.iloc[-1], df.iloc[-2]
    trend_bullish = row["sma_fast"] > row["sma_slow"]
    trend_bearish = row["sma_fast"] < row["sma_slow"]
    macd_cross = _macd_crossed(row, prev_row)

    if trend_bullish and macd_cross == "bullish" and row["rsi"] < cfg.RSI_OVERBOUGHT:
        return Signal(
            symbol, "BUY",
            f"uptrend (SMA{cfg.SMA_FAST} > SMA{cfg.SMA_SLOW}) + fresh bullish MACD "
            f"crossover, RSI {row['rsi']:.0f} (not overbought)",
        )

    if trend_bearish and macd_cross == "bearish" and row["rsi"] > cfg.RSI_OVERSOLD:
        return Signal(
            symbol, "SELL",
            f"downtrend (SMA{cfg.SMA_FAST} < SMA{cfg.SMA_SLOW}) + fresh bearish MACD "
            f"crossover, RSI {row['rsi']:.0f} (not oversold)",
        )

    return Signal(symbol, "HOLD", f"no confirmed signal (RSI {row['rsi']:.0f})")
