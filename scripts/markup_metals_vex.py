#!/usr/bin/env python3
"""
VEX CHART - XAU/USD & XAG/USD Individual timeframe charts WITH PREDICTIONS.
Based on the original vex_chart.py style.

Usage: python markup_metals_vex.py XAU_USD H1
       python markup_metals_vex.py XAG_USD ALL
       python markup_metals_vex.py ALL H1
"""

import os
import sys
sys.path.insert(0, '/Users/villain/Documents/transfer/ICT_WORK/ict_trainer/src')

os.environ.setdefault('OANDA_API_KEY', '4d4e1570f95fc098a40fe90c7ca3c757-c68e27913fd46c5e690381d56fed375c')
os.environ.setdefault('OANDA_ACCOUNT_ID', '101-001-21727967-002')

from ict_agent.data.oanda_fetcher import OANDAFetcher
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from datetime import datetime
import subprocess

plt.style.use('dark_background')

# Metal-specific configs
METAL_CONFIG = {
    'XAU_USD': {'pip_size': 0.10, 'decimals': 2, 'eq_tol_pips': 30.0, 'target_band': 2.0,   'name': 'Gold'},
    'XAG_USD': {'pip_size': 0.001, 'decimals': 3, 'eq_tol_pips': 20.0, 'target_band': 0.05, 'name': 'Silver'},
}


def get_config(pair):
    """Get pip/decimal config for a pair. Defaults to standard forex."""
    if pair in METAL_CONFIG:
        return METAL_CONFIG[pair]
    if 'JPY' in pair:
        return {'pip_size': 0.01, 'decimals': 3, 'eq_tol_pips': 3.0, 'target_band': 0.03, 'name': pair}
    return {'pip_size': 0.0001, 'decimals': 5, 'eq_tol_pips': 1.5, 'target_band': 0.0003, 'name': pair}


def fetch_data(pair: str, timeframe: str, count: int = 100) -> pd.DataFrame:
    fetcher = OANDAFetcher()
    if '_' not in pair and len(pair) == 6:
        pair = f"{pair[:3]}_{pair[3:]}"

    df = fetcher.fetch_latest(pair, timeframe, count)
    if df is not None and not df.empty:
        df = df.reset_index()
        if 'time' not in df.columns:
            if 'index' in df.columns:
                df.rename(columns={'index': 'time'}, inplace=True)
            elif 'timestamp' in df.columns:
                df.rename(columns={'timestamp': 'time'}, inplace=True)
            else:
                df.rename(columns={df.columns[0]: 'time'}, inplace=True)
        return df
    return pd.DataFrame()


def find_swing_points(df: pd.DataFrame):
    swing_highs = []
    swing_lows = []
    for i in range(2, len(df) - 2):
        if (df['high'].iloc[i] > df['high'].iloc[i-1] and
            df['high'].iloc[i] > df['high'].iloc[i-2] and
            df['high'].iloc[i] > df['high'].iloc[i+1] and
            df['high'].iloc[i] > df['high'].iloc[i+2]):
            swing_highs.append({'idx': i, 'price': df['high'].iloc[i]})
        if (df['low'].iloc[i] < df['low'].iloc[i-1] and
            df['low'].iloc[i] < df['low'].iloc[i-2] and
            df['low'].iloc[i] < df['low'].iloc[i+1] and
            df['low'].iloc[i] < df['low'].iloc[i+2]):
            swing_lows.append({'idx': i, 'price': df['low'].iloc[i]})
    return swing_highs, swing_lows


def find_fvgs(df: pd.DataFrame):
    """Find Fair Value Gaps (using WICKS). Only UNMITIGATED, nearest to price."""
    bullish_fvgs = []
    bearish_fvgs = []
    current_price = df['close'].iloc[-1]

    for i in range(2, len(df)):
        c1_high = df['high'].iloc[i-2]
        c3_low = df['low'].iloc[i]
        if c3_low > c1_high:
            fvg = {'idx': i-1, 'top': c3_low, 'bottom': c1_high,
                    'fifty': (c3_low + c1_high) / 2, 'mitigated': False}
            for j in range(i, len(df)):
                if df['low'].iloc[j] <= fvg['fifty']:
                    fvg['mitigated'] = True
                    break
            if not fvg['mitigated']:
                fvg['distance'] = abs(fvg['fifty'] - current_price)
                bullish_fvgs.append(fvg)

        c1_low = df['low'].iloc[i-2]
        c3_high = df['high'].iloc[i]
        if c1_low > c3_high:
            fvg = {'idx': i-1, 'top': c1_low, 'bottom': c3_high,
                    'fifty': (c1_low + c3_high) / 2, 'mitigated': False}
            for j in range(i, len(df)):
                if df['high'].iloc[j] >= fvg['fifty']:
                    fvg['mitigated'] = True
                    break
            if not fvg['mitigated']:
                fvg['distance'] = abs(fvg['fifty'] - current_price)
                bearish_fvgs.append(fvg)

    bullish_fvgs.sort(key=lambda x: x['distance'])
    bearish_fvgs.sort(key=lambda x: x['distance'])
    return bullish_fvgs, bearish_fvgs


def find_equal_levels(df: pd.DataFrame, pip_size: float, tolerance_pips: float):
    """Find ACTIVE equal highs/lows - nearest to price, not swept yet."""
    swing_highs, swing_lows = find_swing_points(df)
    current_price = df['close'].iloc[-1]
    equal_highs = []
    equal_lows = []
    tol = tolerance_pips * pip_size

    for i, sh1 in enumerate(swing_highs):
        for sh2 in swing_highs[i+1:]:
            if abs(sh1['price'] - sh2['price']) <= tol:
                avg_price = (sh1['price'] + sh2['price']) / 2
                swept = False
                for j in range(sh2['idx'] + 1, len(df)):
                    if df['high'].iloc[j] > avg_price + tol:
                        swept = True
                        break
                if not swept and avg_price > current_price:
                    equal_highs.append({'price': avg_price, 'idx1': sh1['idx'], 'idx2': sh2['idx']})
                break

    for i, sl1 in enumerate(swing_lows):
        for sl2 in swing_lows[i+1:]:
            if abs(sl1['price'] - sl2['price']) <= tol:
                avg_price = (sl1['price'] + sl2['price']) / 2
                swept = False
                for j in range(sl2['idx'] + 1, len(df)):
                    if df['low'].iloc[j] < avg_price - tol:
                        swept = True
                        break
                if not swept and avg_price < current_price:
                    equal_lows.append({'price': avg_price, 'idx1': sl1['idx'], 'idx2': sl2['idx']})
                break

    equal_highs.sort(key=lambda x: abs(x['price'] - current_price))
    equal_lows.sort(key=lambda x: abs(x['price'] - current_price))
    return equal_highs, equal_lows


def plot_single_chart(pair: str, tf: str):
    """Generate one full-size chart for a single timeframe — VEX style."""

    cfg = get_config(pair)
    fmt = f".{cfg['decimals']}f"
    pip_size = cfg['pip_size']
    target_band = cfg['target_band']

    print(f"\n  Fetching {pair} {tf}...")
    df = fetch_data(pair, tf, 80)
    if df.empty:
        print(f"  ❌ No data for {pair} {tf}")
        return None

    swing_highs, swing_lows = find_swing_points(df)
    bull_fvgs, bear_fvgs = find_fvgs(df)

    if tf != 'M5':
        equal_highs, equal_lows = find_equal_levels(df, pip_size, cfg['eq_tol_pips'])
    else:
        equal_highs, equal_lows = [], []

    # Determine bias
    bias = "NEUTRAL"
    bias_color = 'white'
    if len(swing_highs) >= 2 and len(swing_lows) >= 2:
        lh = swing_highs[-1]['price'] < swing_highs[-2]['price']
        ll = swing_lows[-1]['price'] < swing_lows[-2]['price']
        hh = swing_highs[-1]['price'] > swing_highs[-2]['price']
        hl = swing_lows[-1]['price'] > swing_lows[-2]['price']

        if lh and ll:
            bias = "BEARISH (LH + LL)"
            bias_color = '#ff4444'
        elif hh and hl:
            bias = "BULLISH (HH + HL)"
            bias_color = '#44ff44'
        else:
            bias = "MIXED"
            bias_color = '#ffff44'

    # Create large figure
    fig, ax = plt.subplots(figsize=(18, 10))
    fig.patch.set_facecolor('#0d0d0d')
    ax.set_facecolor('#0d0d0d')

    # Plot candlesticks
    for i in range(len(df)):
        color = '#26a69a' if df['close'].iloc[i] >= df['open'].iloc[i] else '#ef5350'
        ax.plot([i, i], [df['low'].iloc[i], df['high'].iloc[i]], color=color, linewidth=1)
        body_bottom = min(df['open'].iloc[i], df['close'].iloc[i])
        body_top = max(df['open'].iloc[i], df['close'].iloc[i])
        body_height = max(body_top - body_bottom, pip_size * 0.01)
        rect = mpatches.Rectangle((i - 0.35, body_bottom), 0.7, body_height,
                                   linewidth=0, facecolor=color)
        ax.add_patch(rect)

    # Determine order flow
    is_bearish = bias.startswith("BEARISH")
    is_bullish = bias.startswith("BULLISH")

    # Only 1 FVG - aligned with order flow, nearest to price
    if is_bearish and bear_fvgs:
        fvg = bear_fvgs[0]
        rect = mpatches.Rectangle((fvg['idx'], fvg['bottom']),
                                   len(df) - fvg['idx'], fvg['top'] - fvg['bottom'],
                                   linewidth=1, edgecolor='#ff0000', facecolor='#ff0000', alpha=0.15)
        ax.add_patch(rect)
        ax.axhline(y=fvg['fifty'], color='#ff0000', linestyle=':', linewidth=1.5, alpha=0.9)
        ax.annotate(f"FVG: {fvg['fifty']:{fmt}}",
                   (len(df) - 2, fvg['fifty']),
                   fontsize=7, color='#ff0000', ha='right', fontweight='bold',
                   bbox=dict(boxstyle='round,pad=0.2', facecolor='#0d0d0d', alpha=0.8))
    elif is_bullish and bull_fvgs:
        fvg = bull_fvgs[0]
        rect = mpatches.Rectangle((fvg['idx'], fvg['bottom']),
                                   len(df) - fvg['idx'], fvg['top'] - fvg['bottom'],
                                   linewidth=1, edgecolor='#00ff00', facecolor='#00ff00', alpha=0.15)
        ax.add_patch(rect)
        ax.axhline(y=fvg['fifty'], color='#00ff00', linestyle=':', linewidth=1.5, alpha=0.9)
        ax.annotate(f"FVG 50%: {fvg['fifty']:{fmt}}",
                   (len(df) - 2, fvg['fifty']),
                   fontsize=7, color='#00ff00', ha='right', fontweight='bold',
                   bbox=dict(boxstyle='round,pad=0.3', facecolor='#0d0d0d', alpha=0.8))
    elif bull_fvgs or bear_fvgs:
        nearest = None
        if bull_fvgs and bear_fvgs:
            nearest = bull_fvgs[0] if bull_fvgs[0]['distance'] < bear_fvgs[0]['distance'] else bear_fvgs[0]
            is_bull_nearest = bull_fvgs[0]['distance'] < bear_fvgs[0]['distance']
        elif bull_fvgs:
            nearest = bull_fvgs[0]
            is_bull_nearest = True
        else:
            nearest = bear_fvgs[0]
            is_bull_nearest = False
        if nearest:
            color = '#00ff00' if is_bull_nearest else '#ff0000'
            rect = mpatches.Rectangle((nearest['idx'], nearest['bottom']),
                                       len(df) - nearest['idx'], nearest['top'] - nearest['bottom'],
                                       linewidth=1, edgecolor=color, facecolor=color, alpha=0.15)
            ax.add_patch(rect)
            ax.axhline(y=nearest['fifty'], color=color, linestyle=':', linewidth=1.5, alpha=0.9)
            ax.annotate(f"FVG 50%: {nearest['fifty']:{fmt}}",
                       (len(df) - 2, nearest['fifty']),
                       fontsize=7, color=color, ha='right', fontweight='bold',
                       bbox=dict(boxstyle='round,pad=0.3', facecolor='#0d0d0d', alpha=0.8))

    # Equal Highs (BSL)
    if equal_highs:
        eh = equal_highs[0]
        ax.plot([eh['idx1'], eh['idx2']], [eh['price'], eh['price']],
               color='#ff00ff', linestyle='--', linewidth=2.5, alpha=0.9)
        ax.annotate(f"BSL: {eh['price']:{fmt}}",
                   (eh['idx2'] + 2, eh['price']),
                   fontsize=7, color='#ff00ff', ha='left', fontweight='bold')

    # Equal Lows (SSL)
    if equal_lows:
        el = equal_lows[0]
        ax.plot([el['idx1'], el['idx2']], [el['price'], el['price']],
               color='#00ffff', linestyle='--', linewidth=2.5, alpha=0.9)
        ax.annotate(f"SSL: {el['price']:{fmt}}",
                   (el['idx2'] + 2, el['price']),
                   fontsize=7, color='#00ffff', ha='left', fontweight='bold')

    # Mark swing highs with price labels
    for sh in swing_highs[-6:]:
        ax.scatter(sh['idx'], sh['price'], marker='v', color='#ffeb3b', s=120, zorder=5, edgecolors='black')
        ax.annotate(f"{sh['price']:{fmt}}",
                   (sh['idx'], sh['price']),
                   textcoords="offset points", xytext=(0, 12),
                   fontsize=7, color='#ffeb3b', ha='center', fontweight='bold')

    # Mark swing lows with price labels
    for sl in swing_lows[-6:]:
        ax.scatter(sl['idx'], sl['price'], marker='^', color='#ffeb3b', s=120, zorder=5, edgecolors='black')
        ax.annotate(f"{sl['price']:{fmt}}",
                   (sl['idx'], sl['price']),
                   textcoords="offset points", xytext=(0, -18),
                   fontsize=7, color='#ffeb3b', ha='center', fontweight='bold')

    # Current price line
    current = df['close'].iloc[-1]
    ax.axhline(y=current, color='white', linestyle='-', linewidth=1.5, alpha=1)
    ax.annotate(f"{current:{fmt}}",
               (len(df) - 1, current),
               fontsize=8, color='white', fontweight='bold', ha='right',
               bbox=dict(boxstyle='round,pad=0.2', facecolor='#333333', edgecolor='white'))

    # =========================================================================
    # VEX PREDICTION - Draw the expected price path
    # =========================================================================

    prediction_text = ""
    last_idx = len(df) - 1
    future_candles = 20

    ax.set_xlim(-2, last_idx + future_candles)
    ax.axvline(x=last_idx, color='#444444', linestyle='--', linewidth=1, alpha=0.5)
    ax.text(last_idx + 1, ax.get_ylim()[1], 'FUTURE', fontsize=7, color='#666666', va='top')

    if is_bearish:
        target_up = None
        target_down = None

        if bear_fvgs:
            target_up = bear_fvgs[0]['fifty']
        elif equal_highs:
            target_up = equal_highs[0]['price']

        if equal_lows:
            target_down = equal_lows[0]['price']
        elif swing_lows:
            target_down = min([sl['price'] for sl in swing_lows[-3:]])

        if target_up and target_up > current and target_down:
            path_x = [last_idx, last_idx + 6, last_idx + 18]
            path_y = [current, target_up, target_down]
            ax.plot(path_x, path_y, color='#ff6600', linewidth=3, linestyle='-',
                   marker='o', markersize=8, markerfacecolor='#ff6600', zorder=10)
            ax.annotate('', xy=(path_x[1], path_y[1]), xytext=(path_x[0], path_y[0]),
                       arrowprops=dict(arrowstyle='-|>', color='#ffaa00', lw=2))
            ax.annotate('', xy=(path_x[2], path_y[2]), xytext=(path_x[1], path_y[1]),
                       arrowprops=dict(arrowstyle='-|>', color='#ff0000', lw=3))
            ax.text(last_idx + 3, (current + target_up) / 2, '① UP', fontsize=7,
                   color='#ffaa00', fontweight='bold', ha='center')
            ax.text(last_idx + 12, (target_up + target_down) / 2, '② SELL', fontsize=8,
                   color='#ff0000', fontweight='bold', ha='center')
            ax.axhspan(target_down - target_band, target_down + target_band,
                      alpha=0.4, color='#ff0000', zorder=1)
            ax.text(last_idx + future_candles - 1, target_down, f'TARGET: {target_down:{fmt}}',
                   fontsize=7, color='#ff0000', ha='right', fontweight='bold')
            prediction_text = f"SHORT: Retrace={target_up:{fmt}} then DROP={target_down:{fmt}}"

        elif target_down:
            ax.plot([last_idx, last_idx + 15], [current, target_down],
                   color='#ff0000', linewidth=3, linestyle='-', marker='o', markersize=8, zorder=10)
            ax.annotate('', xy=(last_idx + 15, target_down), xytext=(last_idx, current),
                       arrowprops=dict(arrowstyle='-|>', color='#ff0000', lw=3))
            ax.axhspan(target_down - target_band, target_down + target_band, alpha=0.4, color='#ff0000')
            ax.text(last_idx + 8, (current + target_down) / 2, 'SELL', fontsize=8,
                   color='#ff0000', fontweight='bold')
            prediction_text = f"SHORT: Drop to {target_down:{fmt}}"

    elif is_bullish:
        target_down = None
        target_up = None

        if bull_fvgs:
            target_down = bull_fvgs[0]['fifty']
        elif equal_lows:
            target_down = equal_lows[0]['price']

        if equal_highs:
            target_up = equal_highs[0]['price']
        elif swing_highs:
            target_up = max([sh['price'] for sh in swing_highs[-3:]])

        if target_down and target_down < current and target_up:
            path_x = [last_idx, last_idx + 6, last_idx + 18]
            path_y = [current, target_down, target_up]
            ax.plot(path_x, path_y, color='#00ff00', linewidth=3, linestyle='-',
                   marker='o', markersize=8, markerfacecolor='#00ff00', zorder=10)
            ax.annotate('', xy=(path_x[1], path_y[1]), xytext=(path_x[0], path_y[0]),
                       arrowprops=dict(arrowstyle='-|>', color='#ffaa00', lw=2))
            ax.annotate('', xy=(path_x[2], path_y[2]), xytext=(path_x[1], path_y[1]),
                       arrowprops=dict(arrowstyle='-|>', color='#00ff00', lw=3))
            ax.text(last_idx + 3, (current + target_down) / 2, '① DOWN', fontsize=7,
                   color='#ffaa00', fontweight='bold', ha='center')
            ax.text(last_idx + 12, (target_down + target_up) / 2, '② BUY', fontsize=8,
                   color='#00ff00', fontweight='bold', ha='center')
            ax.axhspan(target_up - target_band, target_up + target_band, alpha=0.4, color='#00ff00')
            ax.text(last_idx + future_candles - 1, target_up, f'TARGET: {target_up:{fmt}}',
                   fontsize=7, color='#00ff00', ha='right', fontweight='bold')
            prediction_text = f"LONG: Retrace={target_down:{fmt}} then PUMP={target_up:{fmt}}"

        elif target_up:
            ax.plot([last_idx, last_idx + 15], [current, target_up],
                   color='#00ff00', linewidth=3, linestyle='-', marker='o', markersize=8, zorder=10)
            ax.annotate('', xy=(last_idx + 15, target_up), xytext=(last_idx, current),
                       arrowprops=dict(arrowstyle='-|>', color='#00ff00', lw=3))
            ax.axhspan(target_up - target_band, target_up + target_band, alpha=0.4, color='#00ff00')
            ax.text(last_idx + 8, (current + target_up) / 2, 'BUY', fontsize=8,
                   color='#00ff00', fontweight='bold')
            prediction_text = f"LONG: Pump to {target_up:{fmt}}"

    else:
        prediction_text = "NO CLEAR BIAS - WAIT"

    # Title
    ax.set_title(f"VEX: {pair} {tf}  |  {bias}",
                 fontsize=14, fontweight='bold', color=bias_color, pad=15)

    # Stats box
    stats = f"Bull FVGs: {len(bull_fvgs)} | Bear FVGs: {len(bear_fvgs)} | EQH: {len(equal_highs)} | EQL: {len(equal_lows)}"
    if prediction_text:
        stats += f"\n{prediction_text}"
    ax.text(0.02, 0.98, stats, transform=ax.transAxes, fontsize=8,
            verticalalignment='top', fontfamily='monospace',
            bbox=dict(boxstyle='round', facecolor='#1a1a2e', alpha=0.9))

    ax.grid(True, alpha=0.2, linestyle='-', linewidth=0.5)
    ax.set_ylabel('Price', fontsize=8)
    ax.set_xlabel('Candles', fontsize=8)

    tick_positions = range(0, len(df), max(1, len(df) // 8))
    tick_labels = [df['time'].iloc[i].strftime('%m/%d %H:%M') for i in tick_positions]
    ax.set_xticks(list(tick_positions))
    ax.set_xticklabels(tick_labels, fontsize=7, rotation=20)

    # Save
    timestamp = datetime.now().strftime('%H%M%S')
    output_path = f"/Users/villain/Documents/transfer/ICT_WORK/ict_trainer/screenshots/vex_{pair}_{tf}_{timestamp}.png"
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor='#0d0d0d')
    plt.close()

    print(f"  ✅ Saved: {output_path}")
    return output_path


def main():
    pair = sys.argv[1] if len(sys.argv) > 1 else "ALL"
    tf = sys.argv[2].upper() if len(sys.argv) > 2 else "H1"

    pairs_to_chart = []
    if pair.upper() == "ALL":
        pairs_to_chart = ['XAU_USD', 'XAG_USD']
    else:
        pairs_to_chart = [pair.upper()]

    for p in pairs_to_chart:
        cfg = get_config(p)
        print(f"\n{'='*50}")
        print(f"  VEX CHART: {cfg['name']} ({p})")
        print(f"{'='*50}")

        if tf == "ALL":
            timeframes = ['D', 'H4', 'H1', 'M15']
            paths = []
            for t in timeframes:
                path = plot_single_chart(p, t)
                if path:
                    paths.append(path)
            print(f"\n  Opening {len(paths)} charts...")
            for path in paths:
                subprocess.run(["open", path])
        else:
            path = plot_single_chart(p, tf)
            if path:
                subprocess.run(["open", path])


if __name__ == "__main__":
    main()
