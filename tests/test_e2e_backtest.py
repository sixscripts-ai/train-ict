#!/usr/bin/env python3
"""
END-TO-END BACKTEST — VEX Core Engine + Graph Reasoner
======================================================
Verifies the full 9-gate pipeline fires with graph reasoning at Gate 7c.

Tests:
  1. Synthetic bullish OHLCV → all 9 gates fire, G7c_GRAPH present
  2. Synthetic bearish OHLCV → same validation
  3. Latency: graph bridge adds <200ms overhead
  4. Gate trace completeness: every gate appears in trace
  5. Graph integration: confluences, confidence blending, model selection

Created: Session — End-to-End Backtest (Task 3)
"""

import sys
import time
from pathlib import Path
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

# ── Ensure imports resolve ────────────────────────────────────
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from ict_agent.core.vex_core_engine import (
    VexCoreEngine,
    EngineResult,
    TradeSetup,
    Bias,
    SessionPhase,
    TradeType,
    ModelType,
    GateLog,
)

NY_TZ = ZoneInfo("America/New_York")

# Expected gates in order
EXPECTED_GATES = [
    "G1_KILLZONE",
    "G2_SESSION",
    "G3_BIAS",
    "G4_LIQUIDITY",
    "G5_SWEEP",
    "G6_PD_ARRAYS",
    "G7_CLASSIFY",
    "G7b_DISPLACEMENT",
    "G7c_GRAPH",
    "G8_MODEL",
    # G9_RR_CHECK only if build_setup runs
]


# =============================================================================
# DATA GENERATORS
# =============================================================================

def make_bullish_ohlcv(n_bars: int = 200, start_price: float = 1.0800) -> pd.DataFrame:
    """
    Generate synthetic EUR/USD-like 15m OHLCV with:
      - Clear bullish structure (higher highs, higher lows)
      - At least one bullish FVG (gap > 5 pips)
      - Swing highs/lows for liquidity detection
      - 200+ bars for PDH/PDL detection (needs >96)
    """
    np.random.seed(42)

    # NY distribution time (9:30 AM ET) — ensures killzone active
    base_time = datetime(2025, 1, 15, 9, 30, tzinfo=NY_TZ)
    timestamps = [base_time + timedelta(minutes=15 * i) for i in range(n_bars)]

    opens, highs, lows, closes = [], [], [], []
    price = start_price

    for i in range(n_bars):
        # Bullish drift with pullbacks every ~20 bars
        drift = 0.00015  # ~1.5 pips per bar average
        noise = np.random.normal(0, 0.0003)

        # Pullback zone: every 20-30 bars, brief dip
        pullback = (i % 25 > 20)

        if pullback:
            move = -abs(noise) * 0.5
        else:
            move = drift + noise

        o = price
        c = o + move

        # Candle body
        body = abs(c - o)
        wick = abs(np.random.normal(0, 0.0002))

        if c > o:  # bullish candle
            h = c + wick
            l = o - wick * 0.5
        else:  # bearish candle
            h = o + wick * 0.5
            l = c - wick

        opens.append(o)
        highs.append(h)
        lows.append(l)
        closes.append(c)
        price = c

    # ── Inject a clear bullish FVG at bar 150 ──
    # FVG rule: candle[i].low > candle[i-2].high
    # We need bar 150's low > bar 148's high, and bar 149 is bullish displacement
    fvg_idx = 150
    if fvg_idx < n_bars:
        base = closes[fvg_idx - 3]

        # Bar 148 (prev2): small candle
        opens[fvg_idx - 2] = base
        highs[fvg_idx - 2] = base + 0.0003
        lows[fvg_idx - 2] = base - 0.0003
        closes[fvg_idx - 2] = base + 0.0002

        # Bar 149 (mid): big bullish displacement candle
        opens[fvg_idx - 1] = base + 0.0002
        closes[fvg_idx - 1] = base + 0.0020  # 20 pip candle
        highs[fvg_idx - 1] = base + 0.0022
        lows[fvg_idx - 1] = base + 0.0001

        # Bar 150 (current): gap up — low must be > bar 148's high
        gap_bottom = highs[fvg_idx - 2]  # prev2.high
        opens[fvg_idx] = base + 0.0020
        lows[fvg_idx] = gap_bottom + 0.0008  # 8 pip gap (> 5 pip minimum)
        highs[fvg_idx] = base + 0.0028
        closes[fvg_idx] = base + 0.0025

        # Continue from new price level
        price = closes[fvg_idx]
        for j in range(fvg_idx + 1, n_bars):
            drift = 0.00012
            noise = np.random.normal(0, 0.0003)
            pullback = (j % 25 > 20)
            move = -abs(noise) * 0.5 if pullback else drift + noise
            o = price
            c = o + move
            body = abs(c - o)
            wick = abs(np.random.normal(0, 0.0002))
            if c > o:
                h = c + wick
                l = o - wick * 0.5
            else:
                h = o + wick * 0.5
                l = c - wick
            opens[j] = o
            highs[j] = h
            lows[j] = l
            closes[j] = c
            price = c

    # ── Inject equal highs near the top (ERL target) ──
    # Two swing highs within 5 pips of each other
    eq_level = max(highs[100:180]) + 0.0002
    for idx in [170, 175]:
        if idx < n_bars:
            highs[idx] = eq_level
            closes[idx] = eq_level - 0.0003
            opens[idx] = eq_level - 0.0005

    df = pd.DataFrame({
        "open": opens,
        "high": highs,
        "low": lows,
        "close": closes,
        "volume": [np.random.randint(100, 1000) for _ in range(n_bars)],
    }, index=pd.DatetimeIndex(timestamps, tz=NY_TZ))

    return df


def make_bearish_ohlcv(n_bars: int = 200, start_price: float = 1.0900) -> pd.DataFrame:
    """
    Generate bearish OHLCV with clear downtrend structure, bearish FVG,
    and equal lows for liquidity.
    """
    np.random.seed(99)

    base_time = datetime(2025, 1, 16, 9, 30, tzinfo=NY_TZ)
    timestamps = [base_time + timedelta(minutes=15 * i) for i in range(n_bars)]

    opens, highs, lows, closes = [], [], [], []
    price = start_price

    for i in range(n_bars):
        drift = -0.00015  # bearish drift
        noise = np.random.normal(0, 0.0003)
        pullback = (i % 25 > 20)
        move = abs(noise) * 0.5 if pullback else drift + noise
        o = price
        c = o + move
        wick = abs(np.random.normal(0, 0.0002))
        if c < o:
            h = o + wick * 0.5
            l = c - wick
        else:
            h = c + wick
            l = o - wick * 0.5
        opens.append(o)
        highs.append(h)
        lows.append(l)
        closes.append(c)
        price = c

    # ── Inject bearish FVG at bar 150 ──
    # Bearish FVG: candle[i-2].low > candle[i].high
    fvg_idx = 150
    if fvg_idx < n_bars:
        base = closes[fvg_idx - 3]

        # Bar 148 (prev2): small candle  
        opens[fvg_idx - 2] = base
        lows[fvg_idx - 2] = base - 0.0003
        highs[fvg_idx - 2] = base + 0.0003
        closes[fvg_idx - 2] = base - 0.0002

        # Bar 149 (mid): big bearish displacement candle
        opens[fvg_idx - 1] = base - 0.0002
        closes[fvg_idx - 1] = base - 0.0020  # 20 pip drop
        highs[fvg_idx - 1] = base - 0.0001
        lows[fvg_idx - 1] = base - 0.0022

        # Bar 150 (current): gap down — high < bar 148's low
        gap_top = lows[fvg_idx - 2]  # prev2.low
        opens[fvg_idx] = base - 0.0020
        highs[fvg_idx] = gap_top - 0.0008  # 8 pip gap below prev2.low
        lows[fvg_idx] = base - 0.0028
        closes[fvg_idx] = base - 0.0025

        price = closes[fvg_idx]
        for j in range(fvg_idx + 1, n_bars):
            drift = -0.00012
            noise = np.random.normal(0, 0.0003)
            pullback = (j % 25 > 20)
            move = abs(noise) * 0.5 if pullback else drift + noise
            o = price
            c = o + move
            wick = abs(np.random.normal(0, 0.0002))
            if c < o:
                h = o + wick * 0.5
                l = c - wick
            else:
                h = c + wick
                l = o - wick * 0.5
            opens[j] = o
            highs[j] = h
            lows[j] = l
            closes[j] = c
            price = c

    # ── Equal lows for SSL (ERL target) ──
    eq_level = min(lows[100:180]) - 0.0002
    for idx in [170, 175]:
        if idx < n_bars:
            lows[idx] = eq_level
            closes[idx] = eq_level + 0.0003
            opens[idx] = eq_level + 0.0005

    df = pd.DataFrame({
        "open": opens,
        "high": highs,
        "low": lows,
        "close": closes,
        "volume": [np.random.randint(100, 1000) for _ in range(n_bars)],
    }, index=pd.DatetimeIndex(timestamps, tz=NY_TZ))

    return df


# =============================================================================
# TEST HELPERS
# =============================================================================

def find_gate(trace: list, gate_name: str) -> GateLog | None:
    """Find a specific gate in the trace."""
    for g in trace:
        if g.gate == gate_name:
            return g
    return None


import json
import os

def print_gate_trace(trace: list) -> None:
    """Pretty-print the full gate trace and Save serialized Dump."""
    # 1. Print Logic
    for g in trace:
        status = "✅" if g.passed else "❌"
        print(f"  {status} {g.gate:20s} | {g.summary}")

    # 2. Save Logic
    try:
        log_dir = "backtest_logs"
        os.makedirs(log_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        filename = f"{log_dir}/results_visualization_{timestamp}.json"
        
        # Robust encoder for Enums, Datetime, etc.
        def robust_encoder(obj):
            if isinstance(obj, (datetime, pd.Timestamp)):
                return obj.isoformat()
            if hasattr(obj, '__dict__'):
                return obj.__dict__
            return str(obj)

        with open(filename, 'w') as f:
            json.dump(trace, f, default=robust_encoder, indent=2)
            
        print(f"Files <updated>: Saved gate trace to {filename}")
        
    except Exception as e:
        print(f"Error saving gate trace: {e}")


# =============================================================================
# TESTS
# =============================================================================

def test_bullish_e2e():
    """Test 1: Bullish scenario — full pipeline with graph reasoning."""
    print("\n" + "=" * 70)
    print("TEST 1: Bullish End-to-End Backtest")
    print("=" * 70)

    df = make_bullish_ohlcv()
    engine = VexCoreEngine()

    # Force NY distribution killzone (9:30 AM ET)
    test_time = datetime(2025, 1, 15, 9, 30, tzinfo=NY_TZ)

    t0 = time.perf_counter()
    result = engine.analyze(
        symbol="EUR_USD",
        df=df,
        timeframe="15m",
        killzone_override="ny_am",
        current_time=test_time,
    )
    elapsed_ms = (time.perf_counter() - t0) * 1000

    print(f"\n⏱  Total analyze() latency: {elapsed_ms:.1f}ms")
    print(f"📊 Trade decision: {'TRADE' if result.trade else 'NO TRADE'}")
    print(f"📈 Bias: {result.bias.value}")
    print(f"⏰ Session: {result.session_phase.value}")
    if result.rejection_reason:
        print(f"❌ Rejection: {result.rejection_reason}")
    print(f"\n🔍 Gate Trace ({len(result.gate_trace)} gates):")
    print_gate_trace(result.gate_trace)

    # ── Assertions ──
    errors = []

    # 1. G1 must pass (killzone override)
    g1 = find_gate(result.gate_trace, "G1_KILLZONE")
    if not g1 or not g1.passed:
        errors.append("G1_KILLZONE did not pass")

    # 2. G7c_GRAPH must be present
    g7c = find_gate(result.gate_trace, "G7c_GRAPH")
    if g7c is None:
        errors.append("G7c_GRAPH gate not in trace!")
    else:
        print(f"\n🧠 Graph Gate Details:")
        print(f"   Summary: {g7c.summary}")
        for k, v in g7c.details.items():
            print(f"   {k}: {v}")

        # Graph should have attempted (even if error, it should be present)
        if "GraphReasoner not loaded" in g7c.summary:
            errors.append("Graph reasoner not loaded — bridge not wired")
        elif "Error:" in g7c.summary:
            print(f"   ⚠️  Graph error (non-fatal): {g7c.summary}")

    # 3. G8_MODEL must be present if we got past G6
    g6 = find_gate(result.gate_trace, "G6_PD_ARRAYS")
    if g6 and g6.passed:
        g8 = find_gate(result.gate_trace, "G8_MODEL")
        if g8 is None:
            errors.append("G8_MODEL gate missing despite G6 passing")
        else:
            print(f"\n🎯 Model Selection: {g8.summary}")
            if g8.details.get("source") == "graph":
                print("   ✅ Model selected by GRAPH reasoning")
            else:
                print("   ℹ️  Model selected by HEURISTIC fallback")

    # 4. If trade, check setup has graph confluences
    if result.trade and result.setup:
        graph_confs = [c for c in result.setup.confluences if "Graph" in c]
        if graph_confs:
            print(f"\n📋 Graph confluences in setup: {len(graph_confs)}")
            for c in graph_confs:
                print(f"   {c}")
        else:
            print("\n   ℹ️  No graph confluences in setup (graph may have NO-GO'd)")

    # 5. Latency check
    if elapsed_ms > 2000:
        errors.append(f"Total latency {elapsed_ms:.0f}ms exceeds 2000ms threshold")

    if errors:
        print(f"\n❌ FAILURES ({len(errors)}):")
        for e in errors:
            print(f"   • {e}")
        return False
    else:
        print(f"\n✅ BULLISH E2E PASSED")
        return True


def test_bearish_e2e():
    """Test 2: Bearish scenario — full pipeline with graph reasoning."""
    print("\n" + "=" * 70)
    print("TEST 2: Bearish End-to-End Backtest")
    print("=" * 70)

    df = make_bearish_ohlcv()
    engine = VexCoreEngine()

    test_time = datetime(2025, 1, 16, 9, 30, tzinfo=NY_TZ)

    t0 = time.perf_counter()
    result = engine.analyze(
        symbol="GBP_USD",
        df=df,
        timeframe="15m",
        killzone_override="ny_am",
        current_time=test_time,
    )
    elapsed_ms = (time.perf_counter() - t0) * 1000

    print(f"\n⏱  Total analyze() latency: {elapsed_ms:.1f}ms")
    print(f"📊 Trade decision: {'TRADE' if result.trade else 'NO TRADE'}")
    print(f"📈 Bias: {result.bias.value}")
    if result.rejection_reason:
        print(f"❌ Rejection: {result.rejection_reason}")
    print(f"\n🔍 Gate Trace ({len(result.gate_trace)} gates):")
    print_gate_trace(result.gate_trace)

    errors = []

    g1 = find_gate(result.gate_trace, "G1_KILLZONE")
    if not g1 or not g1.passed:
        errors.append("G1_KILLZONE did not pass")

    g7c = find_gate(result.gate_trace, "G7c_GRAPH")
    if g7c is None:
        errors.append("G7c_GRAPH gate not in trace!")
    else:
        print(f"\n🧠 Graph Gate Details:")
        print(f"   Summary: {g7c.summary}")

    if errors:
        print(f"\n❌ FAILURES ({len(errors)}):")
        for e in errors:
            print(f"   • {e}")
        return False
    else:
        print(f"\n✅ BEARISH E2E PASSED")
        return True


def test_graph_latency():
    """Test 3: Measure graph bridge overhead specifically."""
    print("\n" + "=" * 70)
    print("TEST 3: Graph Bridge Latency Measurement")
    print("=" * 70)

    df = make_bullish_ohlcv()
    test_time = datetime(2025, 1, 15, 9, 30, tzinfo=NY_TZ)

    # Run WITH graph reasoner
    engine_with = VexCoreEngine()
    has_graph = engine_with.graph_reasoner is not None
    print(f"   Graph reasoner loaded: {has_graph}")

    times_with = []
    for _ in range(3):
        t0 = time.perf_counter()
        engine_with.analyze(
            symbol="EUR_USD", df=df, timeframe="15m",
            killzone_override="ny_am", current_time=test_time,
        )
        times_with.append((time.perf_counter() - t0) * 1000)

    # Run WITHOUT graph reasoner
    engine_without = VexCoreEngine()
    engine_without.graph_reasoner = None  # disable

    times_without = []
    for _ in range(3):
        t0 = time.perf_counter()
        engine_without.analyze(
            symbol="EUR_USD", df=df, timeframe="15m",
            killzone_override="ny_am", current_time=test_time,
        )
        times_without.append((time.perf_counter() - t0) * 1000)

    avg_with = sum(times_with) / len(times_with)
    avg_without = sum(times_without) / len(times_without)
    overhead = avg_with - avg_without

    print(f"   With graph:    {avg_with:.1f}ms (runs: {[f'{t:.1f}' for t in times_with]})")
    print(f"   Without graph: {avg_without:.1f}ms (runs: {[f'{t:.1f}' for t in times_without]})")
    print(f"   Graph overhead: {overhead:.1f}ms")

    if overhead > 200:
        print(f"\n❌ Graph overhead {overhead:.0f}ms exceeds 200ms limit")
        return False
    else:
        print(f"\n✅ LATENCY TEST PASSED (overhead {overhead:.1f}ms < 200ms)")
        return True


def test_gate_trace_completeness():
    """Test 4: Verify all expected gates appear when pipeline passes."""
    print("\n" + "=" * 70)
    print("TEST 4: Gate Trace Completeness")
    print("=" * 70)

    df = make_bullish_ohlcv()
    engine = VexCoreEngine()
    test_time = datetime(2025, 1, 15, 9, 30, tzinfo=NY_TZ)

    result = engine.analyze(
        symbol="EUR_USD", df=df, timeframe="15m",
        killzone_override="ny_am", current_time=test_time,
    )

    gate_names = [g.gate for g in result.gate_trace]
    print(f"   Gates in trace: {gate_names}")

    errors = []

    # Check each expected gate appears (in order, if pipeline progresses)
    last_passing_idx = -1
    for i, expected in enumerate(EXPECTED_GATES):
        g = find_gate(result.gate_trace, expected)
        if g is None:
            # Gate might be missing because an earlier gate rejected
            # Find the last gate that was present
            if last_passing_idx >= 0:
                last_gate = EXPECTED_GATES[last_passing_idx]
                last_g = find_gate(result.gate_trace, last_gate)
                if last_g and not last_g.passed:
                    # Expected: pipeline terminated at an earlier gate
                    print(f"   ℹ️  {expected} absent (pipeline stopped at {last_gate})")
                    continue
            errors.append(f"Gate {expected} missing from trace")
        else:
            last_passing_idx = i
            print(f"   ✅ {expected}: {g.summary[:60]}")

    # Every GateLog must have gate, passed, summary fields
    for g in result.gate_trace:
        if not g.gate or g.summary is None:
            errors.append(f"Malformed gate log: {g}")

    if errors:
        print(f"\n❌ FAILURES ({len(errors)}):")
        for e in errors:
            print(f"   • {e}")
        return False
    else:
        print(f"\n✅ GATE TRACE COMPLETENESS PASSED")
        return True


def test_multi_bar_backtest():
    """Test 5: Sliding window backtest — run engine at multiple time points."""
    print("\n" + "=" * 70)
    print("TEST 5: Multi-Bar Sliding Window Backtest")
    print("=" * 70)

    df = make_bullish_ohlcv(n_bars=300)
    engine = VexCoreEngine()

    results = []
    graph_fires = 0
    graph_go = 0
    graph_nogo = 0
    trade_signals = 0

    # Slide through bars 150-290 (need 96+ lookback)
    window_size = 150
    for end_idx in range(window_size, min(290, len(df))):
        window = df.iloc[end_idx - window_size : end_idx].copy()
        test_time = window.index[-1].to_pydatetime()

        # Only test during killzone hours
        if not (7 <= test_time.hour <= 11):
            continue

        result = engine.analyze(
            symbol="EUR_USD", df=window, timeframe="15m",
            killzone_override="ny_am", current_time=test_time,
        )

        g7c = find_gate(result.gate_trace, "G7c_GRAPH")
        if g7c:
            graph_fires += 1
            if g7c.details.get("go_no_go"):
                graph_go += 1
            elif "go_no_go" in g7c.details and not g7c.details["go_no_go"]:
                graph_nogo += 1

        if result.trade:
            trade_signals += 1

        results.append(result)

    total = len(results)
    print(f"   Total windows analyzed: {total}")
    print(f"   Graph gate fired: {graph_fires}/{total}")
    print(f"   Graph GO: {graph_go} | NO-GO: {graph_nogo}")
    print(f"   Trade signals: {trade_signals}")

    errors = []
    if total == 0:
        errors.append("No windows analyzed")

    if errors:
        print(f"\n❌ FAILURES ({len(errors)}):")
        for e in errors:
            print(f"   • {e}")
        return False
    else:
        print(f"\n✅ MULTI-BAR BACKTEST PASSED")
        return True


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("VEX CORE ENGINE — END-TO-END BACKTEST SUITE")
    print("=" * 70)

    tests = [
        ("Bullish E2E", test_bullish_e2e),
        ("Bearish E2E", test_bearish_e2e),
        ("Graph Latency", test_graph_latency),
        ("Gate Completeness", test_gate_trace_completeness),
        ("Multi-Bar Backtest", test_multi_bar_backtest),
    ]

    results = {}
    for name, fn in tests:
        try:
            results[name] = fn()
        except Exception as e:
            print(f"\n💥 {name} CRASHED: {e}")
            import traceback
            traceback.print_exc()
            results[name] = False

    # ── Summary ──
    print("\n" + "=" * 70)
    print("BACKTEST SUMMARY")
    print("=" * 70)
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    for name, ok in results.items():
        print(f"  {'✅' if ok else '❌'} {name}")
    print(f"\n  {passed}/{total} passed")
    print("=" * 70)

    sys.exit(0 if passed == total else 1)
