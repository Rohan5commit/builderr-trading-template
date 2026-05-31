"""Baseline strategy: equal-weight buy-and-hold of SPY + QQQ on the first tick.

This is the reference any submission has to beat to qualify as "interesting."
~50% in SPY, ~50% in QQQ, then hold. No leverage, no rebalance.

To use as your starting point: rename to agent.py and tweak.
"""
from __future__ import annotations

_bought = False
_TARGETS = ("SPY", "QQQ")


def decide(market_state, portfolio_state, cash):
    global _bought
    if _bought:
        return []

    orders = []
    per_ticker_cash = cash / len(_TARGETS)
    for t in _TARGETS:
        bars = market_state.get(t) or []
        if not bars:
            return []  # data not ready yet; try again next tick
        last_close = float(bars[-1]["close"])
        if last_close <= 0:
            return []
        qty = int(per_ticker_cash // last_close)
        if qty > 0:
            orders.append({"ticker": t, "side": "buy", "quantity": qty})

    if orders:
        _bought = True
    return orders
