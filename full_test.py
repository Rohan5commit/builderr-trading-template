"""Run your agent through all 3 hidden regimes (full Phase A) at 30-min ticks.

Coarser than the real Phase A (which runs at 1-min ticks across the FULL 30-day
window per regime), but representative — usually ~5 min total. Use this as the
last gate before submitting.

Run:  python full_test.py [agent.py]
"""
from __future__ import annotations

import os
import sys
from pathlib import Path


def _load_env() -> None:
    env = Path(__file__).parent.parent / "builderr" / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            if line.strip() and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


_load_env()

from builderr.backtest import REGIMES_V0, PhaseACriteria, PhaseARunner
from builderr.data import MarketDataFeed
from builderr.data.providers import PolygonProvider, YFinanceProvider


def main() -> int:
    if not os.environ.get("BUILDERR_POLYGON_KEY"):
        print("ERROR: BUILDERR_POLYGON_KEY not set in env", file=sys.stderr)
        return 2

    agent_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent / "agent.py"
    if not agent_path.exists():
        print(f"ERROR: {agent_path} not found", file=sys.stderr)
        return 2

    print(f"Running {agent_path.name} through ALL 3 hidden Phase A regimes (~5 min)...\n")

    feed = MarketDataFeed([PolygonProvider(), YFinanceProvider()])
    runner = PhaseARunner(
        feed=feed,
        regimes=REGIMES_V0,
        starting_cash=100_000,
        criteria=PhaseACriteria(),
        tick_interval_minutes=30,
        lookback_minutes=60,
        per_tick_timeout=5.0,
    )
    result = runner.run(agent_path)
    print(result.summary())
    print()
    if result.passed:
        print("✓✓✓ PASSES Phase A. Ready to submit.")
    else:
        print("✗ FAILS Phase A:", result.reason)
        print("  ↑ this is the same scoring you'll see when you submit.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
