"""Your agent. Implement `decide()`. That's the whole contract.

The builderr harness calls `decide()` once per tick (default: every minute during
US market hours). You return a list of orders to submit at the next bar's open.

CONSTRAINTS — enforced automatically; orders that breach them will DQ you:
  * Long-only (no shorts, no inverse ETFs)
  * Gross beta-adjusted exposure ≤ 1.5x equity
      - TQQQ, SOXL, UPRO, SPXL, TNA, FAS, TECL, LABU = 3x
      - QLD, SSO, DDM, ROM = 2x
      - Plain equities + 1x ETFs = 1x
  * No single ticker > 30% of equity for > 5 trading days
  * Max 50 trades/day, min 60s holding period
  * LLM API cost ≤ 5 GB-hours/month if you use the proxy

Brief sustained breach of any cap triggers auto-flatten (kill switch).

Implementation tips:
  * State persistence between ticks: use module-level variables
  * Logging: print to stdout will be captured (but each tick is JSON, so keep
    print() out of decide() — use stderr for logs)
  * Speed: each call should return in <5s (the per-tick timeout)
"""
from __future__ import annotations


def decide(
    market_state: dict,        # ticker -> list of recent bars (oldest..newest)
    portfolio_state: dict,     # {"cash": float, "positions": [...], "last_prices": {...}}
    cash: float,               # convenience: portfolio_state["cash"]
) -> list[dict]:
    """Return list of orders. Each order is a dict with keys: ticker, side, quantity.

    Order shape:
        {"ticker": "SPY", "side": "buy", "quantity": 10}
        {"ticker": "TQQQ", "side": "sell", "quantity": 50}

    market_state shape:
        {
            "SPY":  [{"ts": "2024-08-05T13:30:00+00:00", "open": 540.2, "high": 540.5,
                      "low": 540.1, "close": 540.3, "volume": 12345.0}, ...],
            "QQQ":  [...],
            ...
        }

    portfolio_state shape:
        {
            "cash": 87532.10,
            "positions": [
                {"ticker": "SPY", "quantity": 22.0, "avg_cost": 548.75},
            ],
            "last_prices": {"SPY": 551.20, "QQQ": 463.10},
        }

    Return [] to do nothing this tick.
    """
    # ------------------------------------------------------------------
    # YOUR LOGIC GOES HERE
    # ------------------------------------------------------------------
    return []
