"""Quick TREND_DOWN smoke test — verifies crash guard fires correctly."""
import modal

app = modal.App("td-quick-test")

image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install("requests")
    .add_local_python_source("agent")
)

@app.function(image=image, secrets=[modal.Secret.from_name("nvidia-nim-key")], timeout=60, cpu=2)
def run():
    import os, sys, math
    sys.path.insert(0, "/root")
    os.environ.setdefault("NVIDIA_NIM_API_KEY", os.environ.get("NVIDIA_NIM_API_KEY", ""))

    from agent import decide

    def make_spy_bars(target_ret20, target_z20, target_vol20, target_dd):
        """Generate bars that cross crash guard thresholds."""
        import random
        random.seed(42)
        n = 220
        closes = [500.0] * n

        # Pre-200: flat at 500
        for i in range(0, 200):
            closes[i] = 500.0

        # Last 20: steep volatile decline
        # Target: ret20 < -0.08, z20 < -1.5, vol20 > 0.028, dd > 0.10
        start_price = 500.0
        end_price = 380.0  # 24% decline → dd=0.24, ret20=-0.24

        for i in range(20):
            base = start_price + (end_price - start_price) * (i / 19.0)
            noise = random.gauss(0, 8)  # ±8 dollar noise
            closes[200 + i] = base + noise

        bars = []
        for i in range(n):
            c = max(closes[i], 1.0)
            ts = f"2024-{(i//28)%12+1:02d}-{(i%28)+1:02d}"
            bars.append({"ts": ts, "open": c, "high": c, "low": c, "close": c, "volume": 1000000})
        return bars

    # Test scenarios — features designed to cross guard thresholds
    # Guard: ret20 < -0.08, z20 < -2.0, vol20 > 0.028
    # Override: ret20 < -0.05, z20 < -1.5, dd > 0.10, mom5 < -0.03
    scenarios = [
        ("TD_crash",      2, "SELL"),
        ("TD_no_pos",     0, "HOLD"),
        ("TD_tech_bear",  3, "SELL"),
    ]

    results = []
    for name, n_pos, exp_act in scenarios:
        spy_bars = make_spy_bars(0, 0, 0, 0)
        market_state = {"SPY": spy_bars, "QQQ": spy_bars}

        # Debug: compute features
        from statistics import mean, pstdev
        cs = [float(b["close"]) for b in spy_bars]
        r20 = cs[-1] / cs[-21] - 1.0
        w = cs[-20:]
        mu = mean(w)
        sig = pstdev(w) if len(w) > 1 else 0.0001
        z = (cs[-1] - mu) / sig if sig > 0 else 0.0
        rets = [(cs[i]/cs[i-1]-1.0) for i in range(-20, 0)]
        vol = pstdev(rets) if len(rets) > 1 else 0.0
        pk = max(cs)
        dd = (pk - cs[-1]) / pk if pk > 0 else 0.0
        mom5 = (cs[-1] / cs[-6] - 1.0) if len(cs) >= 6 else 0.0

        positions = [{"ticker": f"T{i}", "quantity": 100, "avg_cost": 450.0} for i in range(n_pos)]
        last_prices = {f"T{i}": 400.0 for i in range(n_pos)}
        portfolio_state = {
            "cash": 20000,
            "positions": positions,
            "last_prices": last_prices,
        }

        orders = decide(market_state, portfolio_state, 20000)
        sides = [o["side"] for o in orders]
        got = "SELL" if "sell" in sides else ("BUY" if "buy" in sides else "HOLD")
        ok = got == exp_act
        results.append((name, exp_act, got, ok))
        icon = "PASS" if ok else "FAIL"
        print(f"  [{icon}] {name:25s} expected={exp_act:5s} got={got:5s}  orders={len(orders)}")

    passed = sum(1 for _, _, _, ok in results if ok)
    total = len(results)
    print(f"\n  {passed}/{total} TREND_DOWN scenarios passed")
    return {"passed": passed, "total": total}


@app.local_entrypoint()
def main():
    run.remote()

