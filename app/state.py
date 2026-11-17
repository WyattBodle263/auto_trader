from __future__ import annotations

import json
import os


def load(path: str) -> dict:
    if not os.path.exists(path):
        return {}
    with open(path) as f:
        return json.load(f)


def save(path: str, state: dict) -> None:
    with open(path, "w") as f:
        json.dump(state, f, indent=2)


def last_action(state: dict, symbol: str) -> str | None:
    entry = state.get(symbol)
    return entry.get("action") if entry else None


def set_action(state: dict, symbol: str, action: str) -> None:
    state.setdefault(symbol, {})["action"] = action


def get_peak_price(state: dict, symbol: str) -> float | None:
    entry = state.get(symbol)
    return entry.get("peak_price") if entry else None


def set_peak_price(state: dict, symbol: str, price: float) -> None:
    state.setdefault(symbol, {})["peak_price"] = price


def clear_peak_price(state: dict, symbol: str) -> None:
    if symbol in state:
        state[symbol].pop("peak_price", None)
