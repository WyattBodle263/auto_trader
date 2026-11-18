from __future__ import annotations


def kill_switch_tripped(day_pl_pct: float, cfg) -> bool:
    """True once today's account drawdown breaches the configured limit.
    While tripped, the bot must not place any new orders."""
    return day_pl_pct <= -cfg.MAX_DAILY_LOSS_PCT


def dynamic_position_size_usd(equity: float, conviction: float, cfg) -> float:
    """Dollar amount to spend on a new BUY, scaled by how strong that
    specific signal's conviction score is (see strategy._buy_conviction):
    a weak-but-still-qualifying signal gets MIN_POSITION_SIZE_PCT of equity,
    a maximally strong one gets MAX_POSITION_SIZE_PCT, linearly in between.
    Does not compound across multiple same-day signals.
    """
    size_pct = cfg.MIN_POSITION_SIZE_PCT + conviction * (
        cfg.MAX_POSITION_SIZE_PCT - cfg.MIN_POSITION_SIZE_PCT
    )
    return equity * size_pct


def trailing_stop_tripped(current_price: float, peak_price: float, cfg) -> bool:
    """True once price has pulled back cfg.TRAILING_STOP_PCT from the highest
    price seen since the position was opened. Lets a winner run while it's
    still climbing, exits once it gives back too much from its peak -- this
    fires independently of (and before) the trend-reversal SELL signal."""
    if peak_price <= 0:
        return False
    drawdown = (peak_price - current_price) / peak_price
    return drawdown >= cfg.TRAILING_STOP_PCT
