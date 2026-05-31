"""Soham-Style AI Basket — first dogfood.

Inspired by Soham's portfolio-assistant skill: AI Industrial Stack tilt
(Brian BWB) + TQQQ conviction. Buy on first tick, hold. No timing, no
signal — pure thematic exposure. Tests whether Phase A correctly filters
naive bold bets.

Beta-adjusted gross:
  0.25(1) + 0.20(1) + 0.15(1) + 0.10(1)*3 + 0.10(1) + 0.10(1) + 0.10(3)
  = 0.25 + 0.20 + 0.15 + 0.30 + 0.10 + 0.10 + 0.30
  = 1.40x  (just under the 1.5x cap)

Concentration: max single position 25% (QQQ) — under 30% cap.
"""
from __future__ import annotations

_bought = False

# Weights chosen to (a) reflect Soham's stated tilt and (b) sit ~1.4x beta-adjusted.
_ALLOCATION = {
    "QQQ":  0.25,
    "SMH":  0.20,
    "NVDA": 0.15,
    "MSFT": 0.10,
    "AAPL": 0.10,
    "META": 0.10,
    "TQQQ": 0.10,  # conviction tilt; 3x leveraged
}


def decide(market_state, portfolio_state, cash):
    global _bought
    if _bought:
        return []

    # Filter to only tickers we have data for; skip missing rather than abort.
    available = {t: w for t, w in _ALLOCATION.items() if market_state.get(t)}
    if not available:
        return []

    orders = []
    for ticker, weight in available.items():
        bars = market_state[ticker]
        last_close = float(bars[-1]["close"])
        if last_close <= 0:
            continue
        target_dollars = cash * weight
        qty = int(target_dollars // last_close)
        if qty > 0:
            orders.append({"ticker": ticker, "side": "buy", "quantity": qty})

    if orders:
        _bought = True
    return orders
