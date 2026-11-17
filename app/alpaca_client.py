from __future__ import annotations

from alpaca.trading.client import TradingClient
from alpaca.trading.enums import OrderSide, TimeInForce
from alpaca.trading.requests import MarketOrderRequest


def get_client(cfg) -> TradingClient:
    return TradingClient(cfg.ALPACA_API_KEY, cfg.ALPACA_SECRET_KEY, paper=cfg.ALPACA_PAPER)


def get_equity(client: TradingClient) -> float:
    return float(client.get_account().equity)


def get_day_pl_pct(client: TradingClient) -> float:
    """Unrealized + realized change in account equity since yesterday's close,
    as a fraction (e.g. -0.02 = down 2% today)."""
    account = client.get_account()
    last_equity = float(account.last_equity)
    if last_equity == 0:
        return 0.0
    return (float(account.equity) - last_equity) / last_equity


def get_position_qty(client: TradingClient, symbol: str) -> float:
    try:
        position = client.get_open_position(symbol)
    except Exception:
        return 0.0
    return float(position.qty)


def submit_buy(client: TradingClient, symbol: str, notional_usd: float) -> None:
    client.submit_order(MarketOrderRequest(
        symbol=symbol,
        notional=round(notional_usd, 2),
        side=OrderSide.BUY,
        time_in_force=TimeInForce.DAY,
    ))


def submit_sell_all(client: TradingClient, symbol: str, qty: float) -> None:
    client.submit_order(MarketOrderRequest(
        symbol=symbol,
        qty=qty,
        side=OrderSide.SELL,
        time_in_force=TimeInForce.DAY,
    ))
