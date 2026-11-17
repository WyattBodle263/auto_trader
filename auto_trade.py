"""Fully automated entry point: checks a daily loss kill-switch, evaluates
the strategy for every open Alpaca position plus your watchlist, and places
orders directly through Alpaca -- no text-and-wait-for-you step.

READ THIS FIRST:
- Defaults to Alpaca's PAPER trading (simulated money). Do not set
  ALPACA_PAPER=false until you've watched it run unattended for a while and
  are comfortable with what it does.
- A tripped daily-loss kill switch stops ALL new orders for the rest of the
  run and just texts you instead.
- A held position exits on EITHER a trailing stop (price down
  TRAILING_STOP_PCT from its peak since purchase) OR the trend-reversal
  signal, whichever comes first. The trailing stop lets a winner keep
  running while it's still climbing, and locks in gains once it pulls back.
- If SCREENER_ENABLED=true, it also scans the S&P 500 (beyond
  WATCHLIST_SYMBOLS) for fresh BUY signals and can open up to
  MAX_NEW_SCREENER_POSITIONS brand-new positions per run in companies you
  never explicitly chose. Off by default -- this materially increases risk
  (unfamiliar names, more capital in play) and should only be turned on
  once you trust the watchlist-only behavior.
- Intended to be invoked once per run (e.g. a Railway cron trigger shortly
  after market close), not run as a perpetual loop.
"""

import sys

from app import alpaca_client, market_data, notifier, risk, screener, state
from app.config import Config
from app.strategy import Signal, evaluate


def _text(cfg, message: str) -> None:
    print(message)
    if cfg.TWILIO_ACCOUNT_SID and cfg.TWILIO_FROM_NUMBER and cfg.TWILIO_TO_NUMBER:
        try:
            notifier.send_signal(Signal("ACCOUNT", "INFO", message), cfg)
        except Exception as exc:
            print(f"SMS send failed (trading logic unaffected): {exc}", file=sys.stderr)


def _handle_held_position(client, cfg, signal_state, symbol, position, current_price, actions_taken):
    """Returns True if a trailing-stop SELL was placed (caller should skip
    the trend-based evaluation for this symbol this run)."""
    held_qty = float(position.qty)
    prior_peak = state.get_peak_price(signal_state, symbol) or float(position.avg_entry_price)
    peak = max(prior_peak, current_price)
    state.set_peak_price(signal_state, symbol, peak)

    if not risk.trailing_stop_tripped(current_price, peak, cfg):
        return False

    drawdown_pct = (peak - current_price) / peak
    reason = f"trailing stop: {drawdown_pct:.1%} off peak ${peak:.2f}"
    print(f"[{symbol}] SELL (trailing stop): {reason} (held: {held_qty})")
    try:
        alpaca_client.submit_sell_all(client, symbol, held_qty)
        _text(cfg, f"SOLD {held_qty} shares of {symbol}: {reason}")
        state.set_action(signal_state, symbol, "SELL")
        state.clear_peak_price(signal_state, symbol)
        actions_taken.append(f"SOLD {symbol} (trailing stop, {drawdown_pct:.1%} off peak)")
    except Exception as exc:
        print(f"[{symbol}] sell order failed: {exc}", file=sys.stderr)
    return True


def main() -> None:
    cfg = Config()
    cfg.require("ALPACA_API_KEY", "ALPACA_SECRET_KEY")
    if not (cfg.TWILIO_ACCOUNT_SID and cfg.TWILIO_FROM_NUMBER and cfg.TWILIO_TO_NUMBER):
        print("Twilio not fully configured -- logging actions to console only, no SMS.")
    client = alpaca_client.get_client(cfg)

    day_pl_pct = alpaca_client.get_day_pl_pct(client)
    if risk.kill_switch_tripped(day_pl_pct, cfg):
        _text(
            cfg,
            f"Kill switch tripped: account down {day_pl_pct:.1%} today "
            f"(limit {cfg.MAX_DAILY_LOSS_PCT:.1%}). No orders placed this run.",
        )
        return

    equity = alpaca_client.get_equity(client)
    signal_state = state.load(cfg.STATE_FILE)
    actions_taken: list[str] = []

    positions_by_symbol = {p.symbol: p for p in client.get_all_positions()}
    symbols = sorted(set(positions_by_symbol) | set(cfg.WATCHLIST_SYMBOLS))

    if not symbols:
        print("No open positions and no WATCHLIST_SYMBOLS configured -- nothing to do.")
        return

    for symbol in symbols:
        try:
            closes = market_data.get_daily_closes_alpaca(symbol, cfg)
        except Exception as exc:
            print(f"[{symbol}] skipped, price fetch failed: {exc}", file=sys.stderr)
            continue

        current_price = float(closes.iloc[-1])
        position = positions_by_symbol.get(symbol)

        if position is not None:
            if _handle_held_position(client, cfg, signal_state, symbol, position, current_price, actions_taken):
                continue

        signal = evaluate(symbol, closes, cfg)
        previous = state.last_action(signal_state, symbol)
        held_qty = float(position.qty) if position else 0.0
        print(f"[{symbol}] {signal.action}: {signal.reason} (held: {held_qty})")

        if signal.action == "BUY" and signal.action != previous and held_qty == 0:
            notional = risk.position_size_usd(equity, cfg)
            try:
                alpaca_client.submit_buy(client, symbol, notional)
                _text(cfg, f"BOUGHT ~${notional:.2f} of {symbol}: {signal.reason}")
                state.set_peak_price(signal_state, symbol, current_price)
                actions_taken.append(f"BOUGHT ~${notional:.2f} {symbol}")
            except Exception as exc:
                print(f"[{symbol}] buy order failed: {exc}", file=sys.stderr)

        elif signal.action == "SELL" and signal.action != previous and held_qty > 0:
            try:
                alpaca_client.submit_sell_all(client, symbol, held_qty)
                _text(cfg, f"SOLD {held_qty} shares of {symbol}: {signal.reason}")
                state.clear_peak_price(signal_state, symbol)
                actions_taken.append(f"SOLD {symbol} (trend reversal)")
            except Exception as exc:
                print(f"[{symbol}] sell order failed: {exc}", file=sys.stderr)

        state.set_action(signal_state, symbol, signal.action)

    if cfg.SCREENER_ENABLED:
        already_tracked = set(positions_by_symbol) | set(cfg.WATCHLIST_SYMBOLS)
        try:
            candidates = screener.find_new_buy_candidates(
                already_tracked, cfg, cfg.MAX_NEW_SCREENER_POSITIONS
            )
        except Exception as exc:
            print(f"Screener scan failed: {exc}", file=sys.stderr)
            candidates = []

        for signal, current_price in candidates:
            notional = risk.position_size_usd(equity, cfg)
            print(f"[{signal.symbol}] BUY (screener): {signal.reason}")
            try:
                alpaca_client.submit_buy(client, signal.symbol, notional)
                _text(cfg, f"BOUGHT ~${notional:.2f} of {signal.symbol} (screener pick): {signal.reason}")
                state.set_action(signal_state, signal.symbol, "BUY")
                state.set_peak_price(signal_state, signal.symbol, current_price)
                actions_taken.append(f"BOUGHT ~${notional:.2f} {signal.symbol} (screener)")
            except Exception as exc:
                print(f"[{signal.symbol}] screener buy order failed: {exc}", file=sys.stderr)

    state.save(cfg.STATE_FILE, signal_state)

    closing_equity = alpaca_client.get_equity(client)
    held_count = len(client.get_all_positions())
    actions_summary = "; ".join(actions_taken) if actions_taken else "no trades"
    _text(
        cfg,
        f"Daily summary: equity ${closing_equity:,.2f} ({day_pl_pct:+.1%} today), "
        f"{held_count} positions held. Actions: {actions_summary}.",
    )


if __name__ == "__main__":
    main()
