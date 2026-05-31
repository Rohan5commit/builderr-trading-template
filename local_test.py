"""Run your agent through a 1-week mini-Phase-A locally before submitting.

Hits the SVB-2023 crisis week (Mar 9-17). Coarse 30-min tick interval so it
finishes in ~30s. The real Phase A runs all 3 regimes at 1-min tick interval
with a wider date range.

Prerequisite: builderr package installed in your venv.
    pip install -e /path/to/builderr  # or pip install builderr (once published)

You also need a Polygon (Massive) API key in your env:
    export BUILDERR_POLYGON_KEY=your-key-here

Run:
    python local_test.py
    python local_test.py baseline.py   # to test the baseline instead
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from pathlib import Path


def main() -> int:
    try:
        from builderr.backtest import PhaseACriteria, PhaseARegime, PhaseARunner
        from builderr.data import MarketDataFeed
        from builderr.data.providers import PolygonProvider, YFinanceProvider
    except ImportError:
        print("ERROR: builderr not installed.", file=sys.stderr)
        print("  → pip install -e /path/to/builderr (during private beta)", file=sys.stderr)
        return 2

    if not os.environ.get("BUILDERR_POLYGON_KEY"):
        print("ERROR: BUILDERR_POLYGON_KEY not set.", file=sys.stderr)
        print("  → export BUILDERR_POLYGON_KEY=your-key-from-massive.com", file=sys.stderr)
        return 2

    agent_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent / "agent.py"
    if not agent_path.exists():
        print(f"ERROR: {agent_path} not found", file=sys.stderr)
        return 2

    print(f"Running {agent_path.name} through SVB-2023 mini-regime (~30s)...\n")

    feed = MarketDataFeed([PolygonProvider(), YFinanceProvider()])
    smoke_regime = PhaseARegime(
        name="svb_mini",
        public_shape="local smoke test",
        start=datetime(2023, 3, 9, tzinfo=timezone.utc),
        end=datetime(2023, 3, 17, tzinfo=timezone.utc),
        universe=(
            "SPY", "QQQ", "KRE", "XLF", "TQQQ", "SOXL",
            "SMH", "NVDA", "MSFT", "AAPL", "META", "GOOGL", "AMZN", "TSLA", "XLK",
        ),
    )
    runner = PhaseARunner(
        feed=feed,
        regimes=(smoke_regime,),
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
        print("✓ Would PASS Phase A under these criteria (1 regime tested, not all 3).")
    else:
        print("✗ Would FAIL Phase A. Reason:", result.reason)
        print("  Note: this is 1 regime + coarse ticks. Real Phase A is harder.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
