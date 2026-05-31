# builderr trading agent — starter template

Submission template for the **builderr Trading Agent Leaderboard**.

Fork this repo, implement `decide()` in `agent.py`, push to a public GitHub repo, submit at https://builderr.ai/trading-v0.

---

## 30-second start

```bash
git clone <this-repo>
cd builderr-trading-template
python3 -m venv .venv && source .venv/bin/activate
pip install -e /path/to/builderr   # private beta
export BUILDERR_POLYGON_KEY=your-key

# Run baseline to see the runner work
python local_test.py baseline.py

# Now build your own agent
# (edit agent.py)
python local_test.py
```

---

## The contract

You implement one function:

```python
def decide(market_state, portfolio_state, cash) -> list[dict]:
    return [{"ticker": "SPY", "side": "buy", "quantity": 10}]
```

| Argument | Shape |
|---|---|
| `market_state` | `{ticker: [bar, bar, ...]}` — recent bars per ticker, oldest first. Each bar: `{ts, open, high, low, close, volume}`. Default lookback: 60 minutes. |
| `portfolio_state` | `{cash, positions: [{ticker, quantity, avg_cost}], last_prices: {ticker: price}}` |
| `cash` | Convenience copy of `portfolio_state["cash"]`. |
| **return** | List of orders. Each: `{ticker, side: "buy"\|"sell", quantity: float}`. Empty list = no action. |

`decide()` is called once per minute during US market hours.

---

## Constraints (auto-enforced)

| Rule | Limit | Breach action |
|---|---|---|
| Side | Long-only | Order rejected |
| Gross beta-adjusted exposure | ≤ 1.5x equity | Sustained breach > 60s → auto-flatten + DQ |
| Position concentration | < 30% per ticker for any 5 trading days | Sustained breach → auto-flatten + DQ |
| Trade rate | ≤ 50 trades/day | Excess rejected |
| Min hold | ≥ 60s | Excess rejected |
| Decide() runtime | ≤ 5s per call | Tick errors out (you keep going) |
| LLM cost (if used) | ≤ 5 GB-hours/month | Proxy kills connection |

## Rules of engagement — external data & network

**Your agent has open network access.** Hit any external API: news feeds, alt-data vendors, social sentiment, your own server, an LLM. Real trading bots use external signals; we don't pretend otherwise.

**One absolute rule: no lookahead bias.** Phase A runs in 2026 against historical regimes (2022–2024). At submission time, "live" APIs return present-day data, which for a 2023 backtest *is the future*. If your strategy queries data sources for the regime period at submission time and benefits from knowing what happened, you have lookahead bias.

How we catch it:
1. **Top-10 Phase A submissions get a 10-min human code read.** Patterns like `requests.get("yahoo/SPY/2023-*")` inside the live backtest = DQ. Public postmortem on caught cases.
2. **Phase A ↔ Phase B correlation check.** If your Phase A Sharpe is 6 and your Phase B Sharpe over a comparable horizon is -1, you get flagged for review. Lookahead cheaters leave that signature every time.
3. **Surprise fresh-regime reruns.** During Phase B we re-run qualified agents against new hidden 30-day windows that post-date any internet snapshot you could have queried. Inconsistency = lookahead suspicion.

If you're not sure whether your data source is OK: ask in GitHub Discussions before submitting. If your strategy is genuinely signal-driven (technicals, fundamentals available at the regime time, your own models), you're fine.

**Beta multiples** for the leverage cap:
- 3x: TQQQ, SOXL, UPRO, SPXL, TNA, FAS, TECL, LABU, CURE, DRN, UDOW, NAIL
- 2x: QLD, SSO, DDM, ROM, UWM, AGQ
- 1x: everything else (plain equities + non-leveraged ETFs)

So 100% TQQQ = 3x exposure = instant breach. Max 50% TQQQ + 50% cash works (1.5x exactly).

---

## Universe

Curated set during v0 (real challenge expands to top ~1000 US equities by liquidity at launch):

- Mega-cap tech: AAPL MSFT GOOGL AMZN META NVDA TSLA
- Index ETFs: SPY QQQ DIA IWM
- Sector ETFs: XLK XLF XLE XLV XLI XLY XLP XLU XLRE XLC SMH
- Banking: KRE JPM BAC C WFC
- Leveraged: TQQQ SOXL UPRO SPXL QLD SSO

Tickers outside the universe are silently ignored.

---

## Scoring

### Phase A — Qualifier (immediate, runs on submission)

3 hidden 30-day historical regimes (shapes only — dates are hidden):
1. Fast sector-contagion crash with broader-market spillover
2. Slow trend-down regime change from rate-hike repricing  
3. Vol spike + rapid snapback from leveraged-position unwind

**Pass criteria (all must hold):**
- Sharpe ≥ 0.5 in **all 3** regimes
- MaxDD ≤ 20% in **all 3** regimes
- Calmar ≥ 0.5 in **at least 2 of 3** regimes
- No DQ in any regime

### Phase B — Live forward test (60 days)

If you clear Phase A, your code runs live on Alpaca paper for 60 days starting on a fixed cohort start date. Daily leaderboard. Primary score: **Calmar** (annualized return / max drawdown).

Top 3 by Phase B Calmar split a **$2,000 prize pool** ($1200 / $500 / $300). Top 5 get LinkedIn spotlight. Winner's code runs on a real **$50k Nasdaq book** post-Phase-B with public weekly P&L — *"win and your code trades my real money."*

---

## Submission

When ready:
1. Push your repo to public GitHub
2. Submit URL at https://builderr.ai/trading-v0
3. Phase A runs automatically (~10 min); leaderboard updates with your Phase A scores
4. If you clear Phase A, your agent enters the next Phase B cohort

Alt path: if you can't push public code (proprietary models, BYOK), host an HTTPS endpoint that accepts `POST /decide` with `{market_state, portfolio_state, cash}` and returns `{orders: [...]}`. Per-agent latency is published on the leaderboard.

---

## Examples

- `baseline.py` — equal-weight buy-and-hold SPY+QQQ
- More coming as community shares strategies post-launch

---

## Questions

GitHub Discussions on this repo, or DM Soham (@sohamsinha on LinkedIn).
