"""Soham-Style AI Basket v2 — adds three signal-driven defenses.

What changed vs v1:
1. **Trend filter on TQQQ.** Only hold when 20-day SMA > 50-day SMA on QQQ.
   Saves us from holding 3x leveraged tech into a rate-regime down-grind.
2. **Defensive ballast.** Adds XLP (consumer staples) + XLU (utilities) at
   20% combined. Cuts portfolio beta, reduces drawdown in trend-down regimes.
3. **Vol-aware sizing.** When realized 20-day vol on QQQ > annualized 30%,
   halve the leveraged TQQQ allocation. Saves us from blow-ups in Aug-2024-style
   vol shocks.

Target beta-adjusted (in calm regime):
  0.20(1) + 0.15(1) + 0.10(1) + 0.10(1) + 0.10(1) + 0.10(1) + 0.10(3) + 0.10(1) + 0.10(1)
  = 0.20 + 0.15 + 0.10 + 0.10 + 0.10 + 0.10 + 0.30 + 0.10 + 0.10 = 1.25x

In stressed regime (TQQQ off): drops to ~0.95x. Well under 1.5x cap.

Rebalance: monthly (every 21 trading days * 390 min/day / tick interval). For
30-min ticks that's 21*390/30 = 273 ticks between rebalances.
"""
from __future__ import annotations

from statistics import mean, stdev

# Target weights at full risk (calm regime). TQQQ optional based on signals.
_BASE = {
    "QQQ":  0.20,
    "SMH":  0.15,
    "NVDA": 0.10,
    "MSFT": 0.10,
    "AAPL": 0.10,
    "META": 0.10,
    "TQQQ": 0.10,  # gated by trend + vol filters
    "XLP":  0.10,  # defensive ballast
    "XLU":  0.10,  # defensive ballast
}

# State across ticks (module-level globals persist within subprocess)
_last_rebalance_tick = -10**9
_tick_count = 0
REBALANCE_EVERY_TICKS = 273  # monthly at 30-min ticks


def _sma(values: list[float], n: int) -> float | None:
    if len(values) < n:
        return None
    return mean(values[-n:])


def _annualized_vol_from_bars(bars: list[dict], n_minutes: int = 20 * 390) -> float | None:
    """Annualized realized vol from minute-bar returns. n_minutes = ~20 trading days."""
    if len(bars) < 30:
        return None
    closes = [float(b["close"]) for b in bars[-n_minutes:]]
    if len(closes) < 30:
        return None
    rets = [(closes[i] / closes[i-1] - 1) for i in range(1, len(closes))]
    if len(rets) < 30:
        return None
    s = stdev(rets)
    # rets are per-bar; bars are minute; ~390/day; ~252 trading days/yr
    return s * (390 * 252) ** 0.5


def _daily_closes_from_minute_bars(bars: list[dict]) -> list[float]:
    """Sample 1 close per ~390 bars (one trading day). Coarse but cheap."""
    if not bars:
        return []
    step = 390
    sampled = [float(b["close"]) for b in bars[::step]]
    if bars and (len(bars) % step != 0):
        sampled.append(float(bars[-1]["close"]))
    return sampled


def _compute_target_weights(market_state: dict) -> dict[str, float]:
    """Apply trend + vol filters to base weights. Renormalize ballast on cut TQQQ."""
    weights = dict(_BASE)

    qqq_bars = market_state.get("QQQ") or []
    qqq_daily = _daily_closes_from_minute_bars(qqq_bars)
    sma20 = _sma(qqq_daily, 20)
    sma50 = _sma(qqq_daily, 50)
    vol_annual = _annualized_vol_from_bars(qqq_bars)

    # Filter 1: trend (QQQ 20-day SMA > 50-day SMA)
    trend_ok = sma20 is not None and sma50 is not None and sma20 > sma50

    # Filter 2: realized vol (QQQ annualized < 30%)
    vol_ok = vol_annual is None or vol_annual < 0.30

    if not trend_ok:
        weights["TQQQ"] = 0.0
    elif not vol_ok:
        weights["TQQQ"] *= 0.5  # halve in high-vol regime

    # Reallocate freed weight to defensive ballast (50/50 XLP/XLU)
    freed = _BASE["TQQQ"] - weights["TQQQ"]
    if freed > 0:
        weights["XLP"] += freed / 2
        weights["XLU"] += freed / 2

    return weights


def decide(market_state, portfolio_state, cash):
    global _tick_count, _last_rebalance_tick
    _tick_count += 1

    if _tick_count - _last_rebalance_tick < REBALANCE_EVERY_TICKS:
        return []

    target_weights = _compute_target_weights(market_state)
    available = {t: w for t, w in target_weights.items() if w > 0 and market_state.get(t)}
    if not available:
        return []

    # Current equity for sizing
    positions = {p["ticker"]: p for p in portfolio_state.get("positions", [])}
    last_prices = portfolio_state.get("last_prices", {})
    equity = portfolio_state.get("cash", cash)
    for tk, pos in positions.items():
        equity += pos["quantity"] * last_prices.get(tk, pos.get("avg_cost", 0))

    orders = []
    for ticker, weight in available.items():
        bars = market_state[ticker]
        last_close = float(bars[-1]["close"])
        if last_close <= 0:
            continue

        target_dollars = equity * weight
        current_qty = positions.get(ticker, {}).get("quantity", 0)
        current_dollars = current_qty * last_close
        delta_dollars = target_dollars - current_dollars
        delta_qty = int(delta_dollars // last_close)

        # Only trade if delta is material (>2% of equity per Soham's style)
        if abs(delta_dollars) < 0.02 * equity:
            continue

        if delta_qty > 0:
            orders.append({"ticker": ticker, "side": "buy", "quantity": delta_qty})
        elif delta_qty < 0 and current_qty > 0:
            orders.append({"ticker": ticker, "side": "sell", "quantity": min(abs(delta_qty), current_qty)})

    # Close any held positions no longer in target (e.g. TQQQ when trend flips)
    for ticker, pos in positions.items():
        if ticker in target_weights and target_weights[ticker] > 0:
            continue
        qty = pos["quantity"]
        if qty > 0:
            orders.append({"ticker": ticker, "side": "sell", "quantity": qty})

    if orders:
        _last_rebalance_tick = _tick_count
    return orders
