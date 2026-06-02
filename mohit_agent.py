"""Mohit — "No-Crash AI Momentum" (risk-on, lightly levered).

Thesis (Mohit's view): no crash in the next month. So lean into the Nasdaq + AI
story — QQQ and a capped slice of TQQQ for leverage, plus the AI/semis leaders
(NVDA, SMH, MSFT, META, XLK). Each day, reallocate toward whatever's carrying the
most momentum. Only step out of the way if the market actually starts breaking —
then cut the leverage, rotate to plain QQQ + an energy/defensive hedge (XLE / XLP
/ XLU) and cash, and wait.

It's an aggressive, fair-weather bot on purpose — but it is built to NOT blow up:
  * Hard per-name cap (24%) so nothing breaches the 30% concentration rule.
  * Beta-adjusted gross is scaled to stay <= 1.4x (the cap is 1.5x). TQQQ counts 3x.
  * A fast crash brake de-levers the whole book the moment stress shows up, so a
    bad week can't run the drawdown to a blow-up.

Long-only, stdlib only, no network, no LLM, no API keys.
"""
from __future__ import annotations

from statistics import pstdev

# Risk-on book — the Nasdaq + AI/semis story. (All in the v0 universe.)
GROWTH = ("QQQ", "NVDA", "SMH", "MSFT", "META", "AAPL", "XLK")
LEVER = "TQQQ"                       # 3x Nasdaq — the leverage sleeve, capped small
# De-risk book — plain index + energy/defensive hedge (no gold in the universe).
DEFENSIVE = ("QQQ", "XLE", "XLP", "XLU")

BETA = {"TQQQ": 3.0, "SOXL": 3.0, "UPRO": 3.0, "SPXL": 3.0, "QLD": 2.0, "SSO": 2.0}

# ---- knobs ------------------------------------------------------------------
TREND_SMA = 100
MOM_DAYS = 63                # ~3-month momentum for the daily re-rank
NAME_CAP = 0.24              # per-name weight cap (< 30% rule)
TQQQ_CAP = 0.22              # extra cap on the 3x sleeve
GROSS_CAP = 1.30             # beta-adjusted gross ceiling (rule is 1.50; margin for intraday drift)
RISKON_NAMES = 5             # how many growth names to hold alongside the levered sleeve
REBALANCE_EVERY = 1          # reallocate daily (the thesis)
DEAD_BAND = 0.02
VOL_LOOKBACK = 10
# crash brake — step out only when the market is actually breaking
BRAKE_3D, BRAKE_5D = -0.05, -0.08
BRAKE_VOL_10D = 0.50

_ANN = 252 ** 0.5
_tick = 0
_last_rebalance = -10**9


def _beta(t):
    return BETA.get(t, 1.0)


def _closes(bars):
    return [float(b["close"]) for b in bars] if bars else []


def _sma(closes, n):
    return sum(closes[-n:]) / n if len(closes) >= n else None


def _ret(closes, days):
    if len(closes) < days + 1 or closes[-(days + 1)] <= 0:
        return None
    return closes[-1] / closes[-(days + 1)] - 1.0


def _ann_vol(closes, n):
    if len(closes) < n + 1:
        return None
    rets = [closes[i] / closes[i - 1] - 1.0 for i in range(len(closes) - n, len(closes)) if closes[i - 1] > 0]
    return pstdev(rets) * _ANN if len(rets) >= 2 else None


def _scale_to_gross(weights):
    """Cap each name, then scale the whole book so beta-adjusted gross <= GROSS_CAP."""
    w = {t: min(NAME_CAP, x) for t, x in weights.items()}
    w[LEVER] = min(w.get(LEVER, 0.0), TQQQ_CAP)
    gross = sum(x * _beta(t) for t, x in w.items())
    if gross > GROSS_CAP:
        f = GROSS_CAP / gross
        w = {t: x * f for t, x in w.items()}
    return {t: x for t, x in w.items() if x > 0.005}


def _crashing(market_state):
    qqq = _closes(market_state.get("QQQ") or [])
    if not qqq:
        return True
    r3, r5, v10 = _ret(qqq, 3), _ret(qqq, 5), _ann_vol(qqq, VOL_LOOKBACK)
    if (r3 is not None and r3 < BRAKE_3D) or (r5 is not None and r5 < BRAKE_5D) or (v10 and v10 > BRAKE_VOL_10D):
        return True
    spy = _closes(market_state.get("SPY") or [])
    spy_sma, qqq_sma = _sma(spy, TREND_SMA), _sma(qqq, TREND_SMA)
    # below the long trend = treat as risk-off too
    if spy_sma and qqq_sma and (spy[-1] < spy_sma or qqq[-1] < qqq_sma):
        return True
    return False


def _target_weights(market_state):
    if _crashing(market_state):
        # de-risk: plain QQQ + energy/defensive hedge, low gross, no leverage
        avail = [t for t in DEFENSIVE if market_state.get(t)]
        if not avail:
            return {}
        per = min(NAME_CAP, 0.55 / len(avail))
        return _scale_to_gross({t: per for t in avail})

    # risk-on: TQQQ leverage sleeve + the strongest growth/AI names by momentum
    ranked = []
    for t in GROWTH:
        m = _ret(_closes(market_state.get(t) or []), MOM_DAYS)
        if m is not None:
            ranked.append((m, t))
    ranked.sort(reverse=True)
    winners = [t for _, t in ranked[:RISKON_NAMES]]

    weights = {}
    if market_state.get(LEVER):
        weights[LEVER] = TQQQ_CAP                       # lever into Nasdaq
    if winners:
        share = (1.0 - TQQQ_CAP) / len(winners)
        for t in winners:
            weights[t] = share
    return _scale_to_gross(weights) if weights else {}


def decide(market_state, portfolio_state, cash):
    global _tick, _last_rebalance
    _tick += 1
    positions = {p["ticker"]: p for p in portfolio_state.get("positions", [])}
    last_prices = portfolio_state.get("last_prices", {})
    equity = portfolio_state.get("cash", cash)
    for tk, pos in positions.items():
        equity += pos["quantity"] * last_prices.get(tk, pos.get("avg_cost", 0))
    if equity <= 0 or (_tick - _last_rebalance < REBALANCE_EVERY):
        return []

    targets = _target_weights(market_state)

    orders = []
    for ticker, pos in positions.items():
        if ticker not in targets and pos["quantity"] > 0:
            orders.append({"ticker": ticker, "side": "sell", "quantity": pos["quantity"]})
    for ticker, weight in targets.items():
        bars = market_state.get(ticker)
        if not bars:
            continue
        px = float(bars[-1]["close"])
        if px <= 0:
            continue
        cur = positions.get(ticker, {}).get("quantity", 0)
        delta = int((equity * weight - cur * px) // px)
        if abs(delta * px) < DEAD_BAND * equity:
            continue
        if delta > 0:
            orders.append({"ticker": ticker, "side": "buy", "quantity": delta})
        elif delta < 0 and cur > 0:
            orders.append({"ticker": ticker, "side": "sell", "quantity": min(abs(delta), cur)})

    if orders:
        _last_rebalance = _tick
    return orders
