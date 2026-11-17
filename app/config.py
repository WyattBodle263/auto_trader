import os

from dotenv import load_dotenv

load_dotenv()


def _int(name: str, default: int) -> int:
    return int(os.environ.get(name, default))


def _float(name: str, default: float) -> float:
    return float(os.environ.get(name, default))


def _bool(name: str, default: bool) -> bool:
    val = os.environ.get(name)
    return default if val is None else val.strip().lower() in ("1", "true", "yes")


class Config:
    """Env vars are read on demand (not required at import time) since
    main.py (advisory) and auto_trade.py (execution) each need a different
    subset -- each script validates what it actually requires.
    """

    # --- Plaid: used by main.py to read Fidelity holdings (advisory mode only) ---
    PLAID_CLIENT_ID = os.environ.get("PLAID_CLIENT_ID")
    PLAID_SECRET = os.environ.get("PLAID_SECRET")
    PLAID_ENV = os.environ.get("PLAID_ENV", "sandbox")
    PLAID_ACCESS_TOKEN = os.environ.get("PLAID_ACCESS_TOKEN")

    # --- Alpaca: used by auto_trade.py for positions, equity, and order execution ---
    ALPACA_API_KEY = os.environ.get("ALPACA_API_KEY")
    ALPACA_SECRET_KEY = os.environ.get("ALPACA_SECRET_KEY")
    ALPACA_PAPER = _bool("ALPACA_PAPER", True)

    ALPHAVANTAGE_API_KEY = os.environ.get("ALPHAVANTAGE_API_KEY")

    TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID")
    TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")
    TWILIO_FROM_NUMBER = os.environ.get("TWILIO_FROM_NUMBER")
    TWILIO_TO_NUMBER = os.environ.get("TWILIO_TO_NUMBER")

    # Comma-separated symbols auto_trade.py considers for new BUYs
    # (existing Alpaca positions are always checked for SELL regardless).
    WATCHLIST_SYMBOLS = [
        s.strip().upper()
        for s in os.environ.get("WATCHLIST_SYMBOLS", "").split(",")
        if s.strip()
    ]

    SMA_FAST = _int("SMA_FAST", 20)
    SMA_SLOW = _int("SMA_SLOW", 50)
    RSI_PERIOD = _int("RSI_PERIOD", 14)
    RSI_OVERBOUGHT = _int("RSI_OVERBOUGHT", 70)
    RSI_OVERSOLD = _int("RSI_OVERSOLD", 30)
    MACD_FAST = _int("MACD_FAST", 12)
    MACD_SLOW = _int("MACD_SLOW", 26)
    MACD_SIGNAL = _int("MACD_SIGNAL", 9)

    # --- Risk controls for auto_trade.py ---
    # Fraction of account equity to spend on any single new BUY.
    POSITION_SIZE_PCT = _float("POSITION_SIZE_PCT", 0.05)
    # Kill switch: if today's account drawdown reaches this fraction, no new
    # orders are placed for the rest of the run -- you get a text instead.
    MAX_DAILY_LOSS_PCT = _float("MAX_DAILY_LOSS_PCT", 0.03)
    # Trailing stop: sell a held position once price pulls back this fraction
    # from its peak since purchase (independent of the trend-reversal SELL).
    TRAILING_STOP_PCT = _float("TRAILING_STOP_PCT", 0.08)

    # Screener: scan the S&P 500 for new BUY candidates beyond WATCHLIST_SYMBOLS.
    SCREENER_ENABLED = _bool("SCREENER_ENABLED", False)
    # Cap on how many brand-new positions the screener can open in one run.
    MAX_NEW_SCREENER_POSITIONS = _int("MAX_NEW_SCREENER_POSITIONS", 3)

    STATE_FILE = os.environ.get("STATE_FILE", "state.json")

    def require(self, *names: str) -> None:
        missing = [n for n in names if not getattr(self, n)]
        if missing:
            raise RuntimeError(f"Missing required env vars: {', '.join(missing)}")
