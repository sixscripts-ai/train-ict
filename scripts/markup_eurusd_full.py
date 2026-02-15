#!/usr/bin/env python3
"""
VEX CHART MARKUP - EUR/USD Multi-Timeframe ICT Analysis
Shows: Candlesticks, Structure, FVGs, Order Blocks, Liquidity Levels, Premium/Discount
Focus: 1H chart trade setup identification
"""
import os
import sys
sys.path.insert(0, '/Users/villain/Documents/transfer/ICT_WORK/ict_trainer/src')

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from datetime import datetime
import subprocess

from ict_agent.data.oanda_fetcher import OANDAFetcher

plt.style.use('dark_background')
fetcher = OANDAFetcher()

PAIR = "EUR_USD"
PIP_SIZE = 0.0001  # Standard pair


def fetch_data(pair: str, timeframe: str, count: int = 100) -> pd.DataFrame:
    """Fetch data using project's OANDAFetcher."""
    tf_map = {'D': '1d', 'H4': '4h', 'H1': '1h', 'M15': '15m', 'M5': '5m'}
    tf = tf_map.get(timeframe, timeframe)

    df = fetcher.fetch_latest(pair, tf, count)
    df = df.reset_index()
    df.columns = ['time', 'open', 'high', 'low', 'close', 'volume']
    return df


def find_swing_points(df: pd.DataFrame, lookback: int = 2):
    """Find swing highs and lows with configurable lookback."""
    swing_highs = []
    swing_lows = []

    for i in range(lookback, len(df) - lookback):
        is_high = all(
            df['high'].iloc[i] > df['high'].iloc[i - j] and
            df['high'].iloc[i] > df['high'].iloc[i + j]
            for j in range(1, lookback + 1)
        )
        if is_high:
            swing_highs.append({'idx': i, 'price': df['high'].iloc[i]})

        is_low = all(
            df['low'].iloc[i] < df['low'].iloc[i - j] and
            df['low'].iloc[i] < df['low'].iloc[i + j]
            for j in range(1, lookback + 1)
        )
        if is_low:
            swing_lows.append({'idx': i, 'price': df['low'].iloc[i]})

    return swing_highs, swing_lows


def find_fvgs(df: pd.DataFrame):
    """Find Fair Value Gaps (wick-based)."""
    bullish_fvgs = []
    bearish_fvgs = []

    for i in range(2, len(df)):
        # Bullish FVG: candle 3 low > candle 1 high (gap up)
        c1_high = df['high'].iloc[i - 2]
        c3_low = df['low'].iloc[i]

        if c3_low > c1_high:
            fvg = {
                'idx': i - 1,
                'top': c3_low,
                'bottom': c1_high,
                'fifty': (c3_low + c1_high) / 2,
                'mitigated': False
            }
            # Check if mitigated by subsequent candles
            for j in range(i + 1, len(df)):
                if df['low'].iloc[j] <= fvg['fifty']:
                    fvg['mitigated'] = True
                    break
            if not fvg['mitigated']:
                bullish_fvgs.append(fvg)

        # Bearish FVG: candle 1 low > candle 3 high (gap down)
        c1_low = df['low'].iloc[i - 2]
        c3_high = df['high'].iloc[i]

        if c1_low > c3_high:
            fvg = {
                'idx': i - 1,
                'top': c1_low,
                'bottom': c3_high,
                'fifty': (c1_low + c3_high) / 2,
                'mitigated': False
            }
            for j in range(i + 1, len(df)):
                if df['high'].iloc[j] >= fvg['fifty']:
                    fvg['mitigated'] = True
                    break
            if not fvg['mitigated']:
                bearish_fvgs.append(fvg)

    return bullish_fvgs, bearish_fvgs


def find_equal_levels(df: pd.DataFrame, tolerance_pips: float = 3.0):
    """Find equal highs and equal lows (liquidity pools)."""
    swing_highs, swing_lows = find_swing_points(df)

    equal_highs = []
    equal_lows = []

    tol = tolerance_pips * PIP_SIZE

    for i, sh1 in enumerate(swing_highs):
        for sh2 in swing_highs[i + 1:]:
            if abs(sh1['price'] - sh2['price']) <= tol:
                equal_highs.append({
                    'price': (sh1['price'] + sh2['price']) / 2,
                    'idx1': sh1['idx'],
                    'idx2': sh2['idx']
                })
                break

    for i, sl1 in enumerate(swing_lows):
        for sl2 in swing_lows[i + 1:]:
            if abs(sl1['price'] - sl2['price']) <= tol:
                equal_lows.append({
                    'price': (sl1['price'] + sl2['price']) / 2,
                    'idx1': sl1['idx'],
                    'idx2': sl2['idx']
                })
                break

    return equal_highs, equal_lows


def find_order_blocks(df: pd.DataFrame):
    """Find order blocks (last opposite candle before displacement)."""
    bullish_obs = []
    bearish_obs = []

    for i in range(3, len(df)):
        # Bullish OB: bearish candle followed by strong bullish move
        if df['close'].iloc[i - 2] < df['open'].iloc[i - 2]:  # Bearish candle
            if (df['close'].iloc[i - 1] > df['high'].iloc[i - 2] and
                    df['close'].iloc[i] > df['close'].iloc[i - 1]):
                bullish_obs.append({
                    'idx': i - 2,
                    'high': df['high'].iloc[i - 2],
                    'low': df['low'].iloc[i - 2],
                    'fifty': (df['high'].iloc[i - 2] + df['low'].iloc[i - 2]) / 2
                })

        # Bearish OB: bullish candle followed by strong bearish move
        if df['close'].iloc[i - 2] > df['open'].iloc[i - 2]:  # Bullish candle
            if (df['close'].iloc[i - 1] < df['low'].iloc[i - 2] and
                    df['close'].iloc[i] < df['close'].iloc[i - 1]):
                bearish_obs.append({
                    'idx': i - 2,
                    'high': df['high'].iloc[i - 2],
                    'low': df['low'].iloc[i - 2],
                    'fifty': (df['high'].iloc[i - 2] + df['low'].iloc[i - 2]) / 2
                })

    return bullish_obs, bearish_obs


def detect_market_structure(swing_highs, swing_lows):
    """Determine market structure: bullish, bearish, or ranging."""
    if len(swing_highs) < 2 or len(swing_lows) < 2:
        return "NEUTRAL", "⚪"

    hh = swing_highs[-1]['price'] > swing_highs[-2]['price']
    hl = swing_lows[-1]['price'] > swing_lows[-2]['price']
    lh = swing_highs[-1]['price'] < swing_highs[-2]['price']
    ll = swing_lows[-1]['price'] < swing_lows[-2]['price']

    if hh and hl:
        return "BULLISH", "🟢"
    elif lh and ll:
        return "BEARISH", "🔴"
    elif hh and ll:
        return "RANGING", "🟡"
    else:
        return "MIXED", "⚪"


def detect_mss(df, swing_highs, swing_lows):
    """Detect Market Structure Shift — look for most recent BOS/MSS."""
    mss_events = []

    # Check if price broke above last swing high (bullish MSS)
    if len(swing_highs) >= 2:
        last_sh = swing_highs[-2]
        for i in range(last_sh['idx'] + 1, len(df)):
            if df['close'].iloc[i] > last_sh['price']:
                mss_events.append({
                    'idx': i,
                    'price': last_sh['price'],
                    'direction': 'BULLISH',
                    'label': 'MSS ↑'
                })
                break

    # Check if price broke below last swing low (bearish MSS)
    if len(swing_lows) >= 2:
        last_sl = swing_lows[-2]
        for i in range(last_sl['idx'] + 1, len(df)):
            if df['close'].iloc[i] < last_sl['price']:
                mss_events.append({
                    'idx': i,
                    'price': last_sl['price'],
                    'direction': 'BEARISH',
                    'label': 'MSS ↓'
                })
                break

    return mss_events


def plot_chart(df: pd.DataFrame, tf: str, ax):
    """Plot fully marked up chart with ICT concepts."""

    swing_highs, swing_lows = find_swing_points(df)
    bull_fvgs, bear_fvgs = find_fvgs(df)
    equal_highs, equal_lows = find_equal_levels(df)
    bull_obs, bear_obs = find_order_blocks(df)
    mss_events = detect_mss(df, swing_highs, swing_lows)
    structure, emoji = detect_market_structure(swing_highs, swing_lows)

    # Calculate range for PD array zones
    range_high = df['high'].max()
    range_low = df['low'].min()
    equilibrium = (range_high + range_low) / 2

    # Premium/Discount zones
    ax.axhspan(equilibrium, range_high, alpha=0.04, color='red', label='Premium Zone')
    ax.axhspan(range_low, equilibrium, alpha=0.04, color='green', label='Discount Zone')
    ax.axhline(y=equilibrium, color='yellow', linestyle='-', linewidth=1.5, alpha=0.6)
    ax.annotate(f"EQ: {equilibrium:.5f}", (3, equilibrium),
                fontsize=6, color='yellow', alpha=0.8)

    # Plot candlesticks
    for i in range(len(df)):
        color = '#00ff00' if df['close'].iloc[i] >= df['open'].iloc[i] else '#ff0000'
        ax.plot([i, i], [df['low'].iloc[i], df['high'].iloc[i]],
                color=color, linewidth=0.5)

        body_bottom = min(df['open'].iloc[i], df['close'].iloc[i])
        body_top = max(df['open'].iloc[i], df['close'].iloc[i])
        body_height = max(body_top - body_bottom, 0.00001)

        rect = mpatches.Rectangle((i - 0.3, body_bottom), 0.6, body_height,
                                   linewidth=0, facecolor=color)
        ax.add_patch(rect)

    # Plot BULLISH FVGs (green boxes)
    for fvg in bull_fvgs[-3:]:
        rect = mpatches.Rectangle(
            (fvg['idx'], fvg['bottom']),
            len(df) - fvg['idx'], fvg['top'] - fvg['bottom'],
            linewidth=1, facecolor='#00ff00', alpha=0.12, edgecolor='#00ff00'
        )
        ax.add_patch(rect)
        ax.axhline(y=fvg['fifty'], color='#00ff00', linestyle=':', linewidth=0.8, alpha=0.7)
        ax.annotate(f"BISI: {fvg['fifty']:.5f}",
                     (len(df) - 5, fvg['fifty']),
                     fontsize=5.5, color='#00ff00', ha='right')

    # Plot BEARISH FVGs (red boxes)
    for fvg in bear_fvgs[-3:]:
        rect = mpatches.Rectangle(
            (fvg['idx'], fvg['bottom']),
            len(df) - fvg['idx'], fvg['top'] - fvg['bottom'],
            linewidth=1, facecolor='#ff0000', alpha=0.12, edgecolor='#ff0000'
        )
        ax.add_patch(rect)
        ax.axhline(y=fvg['fifty'], color='#ff0000', linestyle=':', linewidth=0.8, alpha=0.7)
        ax.annotate(f"SIBI: {fvg['fifty']:.5f}",
                     (len(df) - 5, fvg['fifty']),
                     fontsize=5.5, color='#ff0000', ha='right')

    # Plot ORDER BLOCKS (thicker boxes)
    for ob in bull_obs[-2:]:
        rect = mpatches.Rectangle(
            (ob['idx'] - 0.5, ob['low']),
            len(df) - ob['idx'], ob['high'] - ob['low'],
            linewidth=2, facecolor='none', edgecolor='#00ffff', linestyle='--'
        )
        ax.add_patch(rect)
        ax.annotate("B-OB", (ob['idx'], ob['low']),
                     fontsize=6, color='#00ffff', fontweight='bold')

    for ob in bear_obs[-2:]:
        rect = mpatches.Rectangle(
            (ob['idx'] - 0.5, ob['low']),
            len(df) - ob['idx'], ob['high'] - ob['low'],
            linewidth=2, facecolor='none', edgecolor='#ff6600', linestyle='--'
        )
        ax.add_patch(rect)
        ax.annotate("S-OB", (ob['idx'], ob['high']),
                     fontsize=6, color='#ff6600', fontweight='bold')

    # Plot EQUAL HIGHS (BSL)
    for eh in equal_highs[-2:]:
        ax.axhline(y=eh['price'], color='#ff00ff', linestyle='--', linewidth=2, alpha=0.8)
        ax.annotate(f"EQH/BSL: {eh['price']:.5f}",
                     (len(df) - 3, eh['price']),
                     fontsize=6.5, color='#ff00ff', ha='right', fontweight='bold')

    # Plot EQUAL LOWS (SSL)
    for el in equal_lows[-2:]:
        ax.axhline(y=el['price'], color='#00ffff', linestyle='--', linewidth=2, alpha=0.8)
        ax.annotate(f"EQL/SSL: {el['price']:.5f}",
                     (len(df) - 3, el['price']),
                     fontsize=6.5, color='#00ffff', ha='right', fontweight='bold')

    # Plot MSS events
    for mss in mss_events[-2:]:
        mss_color = '#00ff00' if mss['direction'] == 'BULLISH' else '#ff0000'
        ax.axhline(y=mss['price'], color=mss_color, linestyle='-.',
                   linewidth=1.5, alpha=0.6)
        ax.annotate(mss['label'],
                     (mss['idx'], mss['price']),
                     fontsize=7, color=mss_color, fontweight='bold',
                     bbox=dict(boxstyle='round,pad=0.2', facecolor='#1a1a1a',
                               edgecolor=mss_color, alpha=0.8))

    # Swing highs/lows
    for sh in swing_highs[-5:]:
        ax.scatter(sh['idx'], sh['price'], marker='v', color='yellow', s=30, zorder=5)
    for sl in swing_lows[-5:]:
        ax.scatter(sl['idx'], sl['price'], marker='^', color='yellow', s=30, zorder=5)

    # Current price
    current = df['close'].iloc[-1]
    zone = "PREMIUM" if current > equilibrium else "DISCOUNT"
    zone_color = '#ff6666' if zone == "PREMIUM" else '#66ff66'

    ax.axhline(y=current, color='white', linestyle='-', linewidth=1.8, alpha=0.9)
    ax.annotate(f"NOW: {current:.5f}",
                 (len(df) - 1, current),
                 fontsize=7, color='white', fontweight='bold', ha='right',
                 bbox=dict(boxstyle='round', facecolor='#333', alpha=0.9))

    ax.set_title(
        f"{tf}: {emoji} {structure} | {zone}\n"
        f"Bull FVG: {len(bull_fvgs)} | Bear FVG: {len(bear_fvgs)} | "
        f"B-OB: {len(bull_obs)} | S-OB: {len(bear_obs)}",
        fontsize=9, fontweight='bold', color=zone_color
    )
    ax.grid(True, alpha=0.12)
    ax.set_ylabel('Price', fontsize=7)

    # X-axis labels
    tick_positions = range(0, len(df), max(1, len(df) // 5))
    tick_labels = [df['time'].iloc[i].strftime('%m/%d %H:%M') for i in tick_positions]
    ax.set_xticks(list(tick_positions))
    ax.set_xticklabels(tick_labels, fontsize=5, rotation=20)

    return {
        'structure': structure,
        'emoji': emoji,
        'zone': zone,
        'current': current,
        'equilibrium': equilibrium,
        'bull_fvgs': bull_fvgs,
        'bear_fvgs': bear_fvgs,
        'bull_obs': bull_obs,
        'bear_obs': bear_obs,
        'equal_highs': equal_highs,
        'equal_lows': equal_lows,
        'mss_events': mss_events,
        'swing_highs': swing_highs,
        'swing_lows': swing_lows,
        'range_high': range_high,
        'range_low': range_low,
    }


def generate_trade_thesis(analysis: dict):
    """Generate a detailed ICT trade thesis from the analysis data."""

    daily = analysis['DAILY']
    h4 = analysis['4-HOUR']
    h1 = analysis['1-HOUR']
    m15 = analysis['15-MIN']

    print(f"\n{'=' * 70}")
    print(f"  📋 VEX ICT TRADE THESIS — EUR/USD")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'=' * 70}")

    # === HTF Bias ===
    print(f"\n{'─' * 50}")
    print(f"  📊 HIGHER TIMEFRAME BIAS")
    print(f"{'─' * 50}")
    print(f"  Daily Structure:  {daily['emoji']} {daily['structure']}")
    print(f"  Daily Zone:       {daily['zone']} ({'Look for longs' if daily['zone'] == 'DISCOUNT' else 'Look for shorts'})")
    print(f"  Daily EQ:         {daily['equilibrium']:.5f}")
    print(f"  4H Structure:     {h4['emoji']} {h4['structure']}")
    print(f"  4H Zone:          {h4['zone']}")
    print(f"  4H EQ:            {h4['equilibrium']:.5f}")

    # Determine overall bias
    htf_bullish = daily['structure'] in ['BULLISH', 'MIXED'] and daily['zone'] == 'DISCOUNT'
    htf_bearish = daily['structure'] in ['BEARISH', 'MIXED'] and daily['zone'] == 'PREMIUM'

    if htf_bullish:
        overall_bias = "BULLISH 🟢"
        bias_direction = "LONG"
    elif htf_bearish:
        overall_bias = "BEARISH 🔴"
        bias_direction = "SHORT"
    else:
        # Use 4H as tiebreaker
        if h4['structure'] == 'BULLISH':
            overall_bias = "LEAN BULLISH 🟢"
            bias_direction = "LONG"
        elif h4['structure'] == 'BEARISH':
            overall_bias = "LEAN BEARISH 🔴"
            bias_direction = "SHORT"
        else:
            overall_bias = "NEUTRAL ⚪"
            bias_direction = "WAIT"

    print(f"\n  ➤ OVERALL BIAS: {overall_bias}")

    # === 1H Setup (Primary Focus) ===
    print(f"\n{'─' * 50}")
    print(f"  🎯 1-HOUR SETUP (PRIMARY)")
    print(f"{'─' * 50}")
    print(f"  1H Structure:     {h1['emoji']} {h1['structure']}")
    print(f"  1H Zone:          {h1['zone']}")
    print(f"  Current Price:    {h1['current']:.5f}")

    # MSS on 1H
    if h1['mss_events']:
        latest_mss = h1['mss_events'][-1]
        print(f"  MSS Detected:     {latest_mss['label']} at {latest_mss['price']:.5f}")
    else:
        print(f"  MSS Detected:     None recent")

    # === Entry Arrays ===
    print(f"\n{'─' * 50}")
    print(f"  📍 ENTRY ARRAYS (PD Arrays)")
    print(f"{'─' * 50}")

    # Choose arrays based on bias
    if bias_direction == "LONG":
        print(f"\n  BULLISH ENTRIES (FVG retracement targets):")
        if h1['bull_fvgs']:
            for fvg in h1['bull_fvgs'][-3:]:
                dist = abs(h1['current'] - fvg['fifty']) / PIP_SIZE
                status = "✅ ACTIVE" if h1['current'] > fvg['fifty'] else "⏳ BELOW (wait for sweep)"
                print(f"    → BISI FVG 50%: {fvg['fifty']:.5f} ({dist:.0f} pips away) {status}")
        else:
            print(f"    → No unmitigated bullish FVGs on 1H")

        if h1['bull_obs']:
            print(f"\n  BULLISH ORDER BLOCKS:")
            for ob in h1['bull_obs'][-2:]:
                print(f"    → B-OB: {ob['low']:.5f} - {ob['high']:.5f} (50%: {ob['fifty']:.5f})")
        else:
            print(f"\n  No bullish OBs on 1H")

        # Targets (BSL)
        print(f"\n  TARGETS (Draw on Liquidity):")
        if h1['equal_highs']:
            for eh in h1['equal_highs'][-2:]:
                dist = abs(eh['price'] - h1['current']) / PIP_SIZE
                print(f"    → BSL (EQH): {eh['price']:.5f} ({dist:.0f} pips)")
        if h4['equal_highs']:
            for eh in h4['equal_highs'][-1:]:
                dist = abs(eh['price'] - h1['current']) / PIP_SIZE
                print(f"    → BSL (4H EQH): {eh['price']:.5f} ({dist:.0f} pips)")
        print(f"    → Range High: {h1['range_high']:.5f}")

        # Stop loss zone (SSL)
        print(f"\n  STOP LOSS ZONE:")
        if h1['swing_lows']:
            recent_sl = h1['swing_lows'][-1]
            sl_price = recent_sl['price'] - 5 * PIP_SIZE
            print(f"    → Below last swing low: {sl_price:.5f}")
            risk_pips = abs(h1['current'] - sl_price) / PIP_SIZE
            print(f"    → Risk: ~{risk_pips:.0f} pips")

    elif bias_direction == "SHORT":
        print(f"\n  BEARISH ENTRIES (FVG retracement targets):")
        if h1['bear_fvgs']:
            for fvg in h1['bear_fvgs'][-3:]:
                dist = abs(h1['current'] - fvg['fifty']) / PIP_SIZE
                status = "✅ ACTIVE" if h1['current'] < fvg['fifty'] else "⏳ ABOVE (wait for retracement)"
                print(f"    → SIBI FVG 50%: {fvg['fifty']:.5f} ({dist:.0f} pips away) {status}")
        else:
            print(f"    → No unmitigated bearish FVGs on 1H")

        if h1['bear_obs']:
            print(f"\n  BEARISH ORDER BLOCKS:")
            for ob in h1['bear_obs'][-2:]:
                print(f"    → S-OB: {ob['low']:.5f} - {ob['high']:.5f} (50%: {ob['fifty']:.5f})")
        else:
            print(f"\n  No bearish OBs on 1H")

        # Targets (SSL)
        print(f"\n  TARGETS (Draw on Liquidity):")
        if h1['equal_lows']:
            for el in h1['equal_lows'][-2:]:
                dist = abs(el['price'] - h1['current']) / PIP_SIZE
                print(f"    → SSL (EQL): {el['price']:.5f} ({dist:.0f} pips)")
        if h4['equal_lows']:
            for el in h4['equal_lows'][-1:]:
                dist = abs(el['price'] - h1['current']) / PIP_SIZE
                print(f"    → SSL (4H EQL): {el['price']:.5f} ({dist:.0f} pips)")
        print(f"    → Range Low: {h1['range_low']:.5f}")

        # Stop loss zone (BSL)
        print(f"\n  STOP LOSS ZONE:")
        if h1['swing_highs']:
            recent_sh = h1['swing_highs'][-1]
            sl_price = recent_sh['price'] + 5 * PIP_SIZE
            print(f"    → Above last swing high: {sl_price:.5f}")
            risk_pips = abs(sl_price - h1['current']) / PIP_SIZE
            print(f"    → Risk: ~{risk_pips:.0f} pips")
    else:
        print(f"\n  ⚠️  NO CLEAR DIRECTIONAL BIAS — STAY FLAT")
        print(f"  Wait for either:")
        if h1['equal_highs']:
            print(f"    → Sweep of BSL at {h1['equal_highs'][-1]['price']:.5f} for short")
        if h1['equal_lows']:
            print(f"    → Sweep of SSL at {h1['equal_lows'][-1]['price']:.5f} for long")

    # === 15M Confirmation ===
    print(f"\n{'─' * 50}")
    print(f"  🔍 15-MIN CONFIRMATION")
    print(f"{'─' * 50}")
    print(f"  15M Structure:    {m15['emoji']} {m15['structure']}")
    if m15['mss_events']:
        latest_mss = m15['mss_events'][-1]
        print(f"  15M MSS:          {latest_mss['label']} at {latest_mss['price']:.5f}")
        aligned = (bias_direction == "LONG" and latest_mss['direction'] == "BULLISH") or \
                  (bias_direction == "SHORT" and latest_mss['direction'] == "BEARISH")
        if aligned:
            print(f"  ✅ 15M confirms {bias_direction} bias!")
        else:
            print(f"  ⚠️  15M NOT yet aligned — wait for confirmation")
    else:
        print(f"  ⚠️  No 15M MSS — await displacement")

    if m15['bull_fvgs'] and bias_direction == "LONG":
        fvg = m15['bull_fvgs'][-1]
        print(f"  15M Entry FVG:    {fvg['bottom']:.5f} - {fvg['top']:.5f} (50%: {fvg['fifty']:.5f})")
    elif m15['bear_fvgs'] and bias_direction == "SHORT":
        fvg = m15['bear_fvgs'][-1]
        print(f"  15M Entry FVG:    {fvg['bottom']:.5f} - {fvg['top']:.5f} (50%: {fvg['fifty']:.5f})")

    # === Final Plan ===
    print(f"\n{'=' * 70}")
    print(f"  📌 TRADE PLAN")
    print(f"{'=' * 70}")
    print(f"  Bias:       {overall_bias}")
    print(f"  Direction:  {bias_direction}")

    if bias_direction == "LONG" and h1['bull_fvgs']:
        entry = h1['bull_fvgs'][-1]['fifty']
        target = h1['range_high']
        if h1['swing_lows']:
            stop = h1['swing_lows'][-1]['price'] - 5 * PIP_SIZE
        else:
            stop = h1['range_low']
        reward = abs(target - entry) / PIP_SIZE
        risk = abs(entry - stop) / PIP_SIZE
        rr = reward / risk if risk > 0 else 0
        print(f"  Entry:      {entry:.5f} (BISI FVG 50%)")
        print(f"  Stop:       {stop:.5f}")
        print(f"  Target:     {target:.5f}")
        print(f"  Risk:       {risk:.0f} pips")
        print(f"  Reward:     {reward:.0f} pips")
        print(f"  R:R =       1:{rr:.1f}")
    elif bias_direction == "SHORT" and h1['bear_fvgs']:
        entry = h1['bear_fvgs'][-1]['fifty']
        target = h1['range_low']
        if h1['swing_highs']:
            stop = h1['swing_highs'][-1]['price'] + 5 * PIP_SIZE
        else:
            stop = h1['range_high']
        reward = abs(entry - target) / PIP_SIZE
        risk = abs(stop - entry) / PIP_SIZE
        rr = reward / risk if risk > 0 else 0
        print(f"  Entry:      {entry:.5f} (SIBI FVG 50%)")
        print(f"  Stop:       {stop:.5f}")
        print(f"  Target:     {target:.5f}")
        print(f"  Risk:       {risk:.0f} pips")
        print(f"  Reward:     {reward:.0f} pips")
        print(f"  R:R =       1:{rr:.1f}")
    else:
        print(f"  ⚠️  No clean setup — PATIENCE")

    print(f"\n{'=' * 70}\n")


def main():
    print(f"\n{'=' * 70}")
    print(f"  VEX CHART MARKUP: EUR/USD — FULL ICT ANALYSIS")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Market: {'OPEN ✅' if datetime.now().weekday() < 5 else 'CLOSED 🔴'}")
    print(f"{'=' * 70}\n")

    # Fetch timeframes
    timeframes = {
        'DAILY': ('D', 60),
        '4-HOUR': ('H4', 100),
        '1-HOUR': ('H1', 100),
        '15-MIN': ('M15', 100),
    }

    data = {}
    for label, (tf, count) in timeframes.items():
        print(f"  Fetching {label}...", end=" ")
        data[label] = fetch_data(PAIR, tf, count)
        print(f"✓ {len(data[label])} candles")

    # Create 2x2 figure
    fig, axes = plt.subplots(2, 2, figsize=(20, 13))
    fig.patch.set_facecolor('#0a0a0a')

    fig.suptitle(
        f"EUR/USD MULTI-TIMEFRAME ICT MARKUP — {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
        f"🟢 Green = Bullish FVG (BISI) | 🔴 Red = Bearish FVG (SIBI) | ⬜ Dotted = 50% CE\n"
        f"🟣 Magenta = EQH (BSL) | 🔵 Cyan = EQL (SSL) / B-OB | 🟠 Orange = S-OB | 🟡 Yellow = EQ",
        fontsize=11, fontweight='bold', color='white'
    )

    positions = [(0, 0), (0, 1), (1, 0), (1, 1)]
    labels = ['DAILY', '4-HOUR', '1-HOUR', '15-MIN']

    analysis = {}
    for i, label in enumerate(labels):
        row, col = positions[i]
        print(f"  Plotting {label}...", end=" ")
        analysis[label] = plot_chart(data[label], label, axes[row, col])
        print(f"✓")

    plt.tight_layout(rect=[0, 0, 1, 0.92])

    # Save
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_path = f"/Users/villain/Documents/transfer/ICT_WORK/ict_trainer/screenshots/EURUSD_markup_{timestamp}.png"
    plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor='#0a0a0a')
    print(f"\n✅ Chart saved: {output_path}")
    plt.close()

    # Open the chart
    subprocess.run(["open", output_path])

    # Generate trade thesis
    generate_trade_thesis(analysis)

    return output_path, analysis


if __name__ == "__main__":
    output_path, analysis = main()
