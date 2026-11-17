"""Entry point: fetch your Fidelity holdings, evaluate the strategy for each,
and text you about anything whose signal changed since the last run.

Intended to be invoked once per run (e.g. by a Railway cron trigger shortly
after market close) rather than run as a perpetual loop.
"""

import sys
import time

from app import market_data, notifier, plaid_client, state
from app.config import Config
from app.strategy import evaluate

ALPHA_VANTAGE_DELAY_SECONDS = 15  # stay under the free-tier rate limit


def main() -> None:
    cfg = Config()
    cfg.require(
        "PLAID_CLIENT_ID", "PLAID_SECRET", "PLAID_ACCESS_TOKEN",
        "ALPHAVANTAGE_API_KEY",
        "TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "TWILIO_FROM_NUMBER", "TWILIO_TO_NUMBER",
    )

    try:
        symbols = plaid_client.get_held_tickers(cfg)
    except Exception as exc:
        print(f"Failed to fetch holdings from Plaid: {exc}", file=sys.stderr)
        sys.exit(1)

    if not symbols:
        print("No tickered holdings found.")
        return

    signal_state = state.load(cfg.STATE_FILE)

    for i, symbol in enumerate(symbols):
        if i > 0:
            time.sleep(ALPHA_VANTAGE_DELAY_SECONDS)

        try:
            closes = market_data.get_daily_closes(symbol, cfg.ALPHAVANTAGE_API_KEY)
        except Exception as exc:
            print(f"[{symbol}] skipped, price fetch failed: {exc}", file=sys.stderr)
            continue

        signal = evaluate(symbol, closes, cfg)
        print(f"[{symbol}] {signal.action}: {signal.reason}")

        previous = state.last_action(signal_state, symbol)
        is_actionable = signal.action in ("BUY", "SELL")
        is_new = signal.action != previous

        if is_actionable and is_new:
            notifier.send_signal(signal, cfg)
            print(f"  -> texted (changed from {previous!r})")

        state.set_action(signal_state, symbol, signal.action)

    state.save(cfg.STATE_FILE, signal_state)


if __name__ == "__main__":
    main()
