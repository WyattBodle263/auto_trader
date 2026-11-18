from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from . import indicators


@dataclass
class Signal:
    symbol: str
    action: str  # "BUY", "SELL", or "HOLD"
    reason: str
    # 0-1 "how strong does this particular BUY signal look", meaningful only
    # when action == "BUY" -- used to scale position size (see risk.py).
    # This is a transparent heuristic blend of the same three indicators
    # already used to decide the signal, not a model prediction and not a
    # claim about expected return.
    conviction: float = 0.0


def _macd_crossed(row, prev_row) -> str | None:
    if prev_row["macd"] <= prev_row["macd_signal"] and row["macd"] > row["macd_signal"]:
        return "bullish"
    if prev_row["macd"] >= prev_row["macd_signal"] and row["macd"] < row["macd_signal"]:
        return "bearish"
    return None


def _clamp01(x: float) -> float:
    return min(max(x, 0.0), 1.0)


def _buy_conviction(row, cfg) -> float:
    """Blends three signals already computed for the BUY decision into a
    single 0-1 score: how far the trend has separated, how strong the MACD
    histogram is relative to price, and how much RSI headroom is left before
    overbought. Each component is capped at a somewhat arbitrary "full score"
    threshold -- this is a simple, auditable heuristic, not a fitted model.
    """
    trend_gap = (row["sma_fast"] - row["sma_slow"]) / row["sma_slow"]
    trend_score = _clamp01(trend_gap / 0.05)  # >=5% SMA separation = full score

    macd_strength = row["macd_hist"] / row["close"]
    macd_score = _clamp01(macd_strength / 0.02)  # >=2% of price = full score

    rsi_headroom = (cfg.RSI_OVERBOUGHT - row["rsi"]) / cfg.RSI_OVERBOUGHT
    rsi_score = _clamp01(rsi_headroom)

    return (trend_score + macd_score + rsi_score) / 3


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
        conviction = _buy_conviction(row, cfg)
        return Signal(
            symbol, "BUY",
            f"uptrend (SMA{cfg.SMA_FAST} > SMA{cfg.SMA_SLOW}) + fresh bullish MACD "
            f"crossover, RSI {row['rsi']:.0f} (not overbought), conviction {conviction:.2f}",
            conviction=conviction,
        )

    if trend_bearish and macd_cross == "bearish" and row["rsi"] > cfg.RSI_OVERSOLD:
        return Signal(
            symbol, "SELL",
            f"downtrend (SMA{cfg.SMA_FAST} < SMA{cfg.SMA_SLOW}) + fresh bearish MACD "
            f"crossover, RSI {row['rsi']:.0f} (not oversold)",
        )

    return Signal(symbol, "HOLD", f"no confirmed signal (RSI {row['rsi']:.0f})")
