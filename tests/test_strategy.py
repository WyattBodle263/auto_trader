import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.strategy import evaluate


class FakeConfig:
    SMA_FAST = 5
    SMA_SLOW = 10
    RSI_PERIOD = 14
    RSI_OVERBOUGHT = 70
    RSI_OVERSOLD = 30
    MACD_FAST = 12
    MACD_SLOW = 26
    MACD_SIGNAL = 9


def _series(values):
    idx = pd.date_range("2024-01-01", periods=len(values))
    return pd.Series(values, index=idx)


def test_sustained_uptrend_can_buy():
    # Enough history for SMA_SLOW/MACD to warm up, then a clean uptrend.
    flat = [100.0] * 30
    uptrend = list(100 + np.arange(1, 31) * 1.5)
    closes = _series(flat + uptrend)
    signal = evaluate("TEST", closes, FakeConfig())
    assert signal.action in ("BUY", "HOLD")  # never a false SELL in an uptrend
    print(signal)


def test_sustained_downtrend_never_buys():
    flat = [100.0] * 30
    downtrend = list(100 - np.arange(1, 31) * 1.5)
    closes = _series(flat + downtrend)
    signal = evaluate("TEST", closes, FakeConfig())
    assert signal.action != "BUY"
    print(signal)


def test_insufficient_history_holds():
    closes = _series([100.0, 101.0, 99.0])
    signal = evaluate("TEST", closes, FakeConfig())
    assert signal.action == "HOLD"
    print(signal)


if __name__ == "__main__":
    test_sustained_uptrend_can_buy()
    test_sustained_downtrend_never_buys()
    test_insufficient_history_holds()
    print("all tests passed")
