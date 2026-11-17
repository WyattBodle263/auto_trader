from __future__ import annotations

import os

from . import market_data
from .strategy import Signal, evaluate

_TICKERS_PATH = os.path.join(os.path.dirname(__file__), "sp500_tickers.txt")


def load_universe() -> list[str]:
    """S&P 500 tickers, as a static snapshot bundled with the app (avoids
    scraping a ticker list at runtime). Refresh sp500_tickers.txt
    periodically to track index changes.
    """
    with open(_TICKERS_PATH) as f:
        return [line.strip() for line in f if line.strip()]


def find_new_buy_candidates(
    exclude_symbols: set, cfg, max_candidates: int
) -> list[tuple]:
    """Scans the universe (minus symbols already held/watched) for fresh BUY
    signals, using the exact same strategy as the watchlist. Returns at most
    `max_candidates` (Signal, current_price) pairs, ranked by RSI ascending
    (further from overbought = preferred among otherwise-equal signals) --
    a simple, transparent tie-break, not a claim that it picks the "best" ones.
    """
    universe = [s for s in load_universe() if s not in exclude_symbols]
    price_data = market_data.get_daily_closes_batch(universe, cfg)

    candidates = []
    for symbol, closes in price_data.items():
        signal = evaluate(symbol, closes, cfg)
        if signal.action == "BUY":
            candidates.append((signal, float(closes.iloc[-1])))

    candidates.sort(key=lambda pair: _rsi_from_reason(pair[0].reason))
    return candidates[:max_candidates]


def _rsi_from_reason(reason: str) -> float:
    """Strategy.Signal doesn't carry structured fields, so pull the RSI back
    out of its human-readable reason string for ranking purposes."""
    try:
        return float(reason.rsplit("RSI ", 1)[1].split(" ")[0])
    except (IndexError, ValueError):
        return 50.0
