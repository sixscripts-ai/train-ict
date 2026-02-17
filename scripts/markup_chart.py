#!/usr/bin/env python3
"""
VEX Chart Markup — ICT-Annotated Multi-Timeframe Chart
======================================================
Fetches live OANDA candles and marks up:
  - Candlesticks (dark theme)
  - Fair Value Gaps (FVG)
  - Order Blocks (OB)
  - Liquidity levels (swing high/low)
  - Premium/Discount zones
  - Current price + spread
  - Session context (killzone status)

Usage:
    PYTHONPATH=src python3 scripts/markup_chart.py NZD_USD
    PYTHONPATH=src python3 scripts/markup_chart.py EUR_USD --timeframes H4 H1 M15
    PYTHONPATH=src python3 scripts/markup_chart.py GBP_USD --bars 200
"""

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import matplotlib
matplotlib.use("Agg")  # Non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import Rectangle
import numpy as np
import pandas as pd

# Project imports
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from ict_agent.data.oanda_fetcher import OANDAFetcher, OANDAConfig

NY_TZ = ZoneInfo("America/New_York")
SCREENSHOTS_DIR = PROJECT_ROOT / "screenshots"
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

# ─── Style ────────────────────────────────────────────────────────────────
COLORS = {
    "bg": "#0d1117",
    "panel": "#161b22",
    "candle_up": "#00dc82",
    "candle_down": "#ff4757",
    "wick_up": "#00dc82",
    "wick_down": "#ff4757",
    "fvg_bull": "#00dc8233",
    "fvg_bear": "#ff475733",
    "fvg_border_bull": "#00dc8288",
    "fvg_border_bear": "#ff475788",
    "ob_bull": "#1e90ff44",
    "ob_bear": "#ff8c0044",
    "ob_border_bull": "#1e90ff88",
    "ob_border_bear": "#ff8c0088",
    "premium": "#ff475715",
    "discount": "#00dc8215",
    "equilibrium": "#ffffff33",
    "liquidity": "#ffd700",
    "text": "#c9d1d9",
    "grid": "#21262d",
    "price_line": "#58a6ff",
}


# ─── Data Fetching ────────────────────────────────────────────────────────

def load_env():
    env_paths = [
        PROJECT_ROOT / ".env",
        Path.home() / "Documents" / "trae_projects" / "vexbrain" / "Antigravity" / ".env",
    ]
    for p in env_paths:
        if p.exists():
            for line in open(p):
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ[k.strip()] = v.strip()
            return


def fetch_candles(fetcher: OANDAFetcher, symbol: str, timeframe: str, count: int) -> pd.DataFrame:
    """Fetch candles from OANDA and return DataFrame."""
    instrument = symbol.upper().replace("/", "_")
    granularity = {
        "M1": "M1", "M5": "M5", "M15": "M15", "M30": "M30",
        "H1": "H1", "H4": "H4", "D": "D", "W": "W",
    }.get(timeframe, timeframe)

    url = f"{fetcher.config.base_url}/v3/instruments/{instrument}/candles"
    params = {"granularity": granularity, "count": count, "price": "MBA"}
    resp = fetcher.session.get(url, params=params)
    resp.raise_for_status()
    candles = resp.json().get("candles", [])

    rows = []
    for c in candles:
        if not c.get("complete", True) and granularity not in ("M1", "M5"):
            continue
        mid = c.get("mid", {})
        rows.append({
            "time": pd.to_datetime(c["time"]),
            "open": float(mid["o"]),
            "high": float(mid["h"]),
            "low": float(mid["l"]),
            "close": float(mid["c"]),
            "volume": int(c.get("volume", 0)),
        })

    df = pd.DataFrame(rows)
    if not df.empty:
        df.set_index("time", inplace=True)
        df.sort_index(inplace=True)
    return df


# ─── ICT Detection ───────────────────────────────────────────────────────

def detect_fvgs(df: pd.DataFrame) -> list:
    """Detect Fair Value Gaps."""
    fvgs = []
    for i in range(2, len(df)):
        # Bullish FVG: candle[i] low > candle[i-2] high (gap up)
        if df.iloc[i]["low"] > df.iloc[i - 2]["high"]:
            fvgs.append({
                "type": "bullish",
                "top": df.iloc[i]["low"],
                "bottom": df.iloc[i - 2]["high"],
                "start_idx": i - 2,
                "end_idx": i,
            })
        # Bearish FVG: candle[i] high < candle[i-2] low (gap down)
        elif df.iloc[i]["high"] < df.iloc[i - 2]["low"]:
            fvgs.append({
                "type": "bearish",
                "top": df.iloc[i - 2]["low"],
                "bottom": df.iloc[i]["high"],
                "start_idx": i - 2,
                "end_idx": i,
            })
    return fvgs


def detect_order_blocks(df: pd.DataFrame) -> list:
    """Detect Order Blocks (last opposing candle before impulsive move)."""
    obs = []
    for i in range(2, len(df)):
        body_curr = abs(df.iloc[i]["close"] - df.iloc[i]["open"])
        range_curr = df.iloc[i]["high"] - df.iloc[i]["low"]
        if range_curr == 0:
            continue

        # Impulsive candle check (body > 60% of range)
        if body_curr / range_curr < 0.6:
            continue

        prev = df.iloc[i - 1]

        # Bullish OB: impulsive bullish candle, previous was bearish
        if df.iloc[i]["close"] > df.iloc[i]["open"] and prev["close"] < prev["open"]:
            obs.append({
                "type": "bullish",
                "high": prev["high"],
                "low": prev["low"],
                "idx": i - 1,
            })
        # Bearish OB: impulsive bearish candle, previous was bullish
        elif df.iloc[i]["close"] < df.iloc[i]["open"] and prev["close"] > prev["open"]:
            obs.append({
                "type": "bearish",
                "high": prev["high"],
                "low": prev["low"],
                "idx": i - 1,
            })
    return obs


def detect_liquidity_levels(df: pd.DataFrame, lookback: int = 20) -> dict:
    """Detect swing highs/lows as liquidity targets."""
    highs = df["high"].values
    lows = df["low"].values
    n = len(df)

    swing_highs = []
    swing_lows = []

    window = 5  # candles on each side
    for i in range(window, n - window):
        if highs[i] == max(highs[i - window:i + window + 1]):
            swing_highs.append({"price": highs[i], "idx": i})
        if lows[i] == min(lows[i - window:i + window + 1]):
            swing_lows.append({"price": lows[i], "idx": i})

    # Equal highs/lows (liquidity pools)
    equal_highs = []
    equal_lows = []
    tolerance = (df["high"].max() - df["low"].min()) * 0.001  # 0.1% of range

    for i in range(len(swing_highs)):
        for j in range(i + 1, len(swing_highs)):
            if abs(swing_highs[i]["price"] - swing_highs[j]["price"]) < tolerance:
                equal_highs.append(swing_highs[i]["price"])

    for i in range(len(swing_lows)):
        for j in range(i + 1, len(swing_lows)):
            if abs(swing_lows[i]["price"] - swing_lows[j]["price"]) < tolerance:
                equal_lows.append(swing_lows[i]["price"])

    return {
        "swing_highs": swing_highs[-8:],  # Most recent
        "swing_lows": swing_lows[-8:],
        "equal_highs": list(set(equal_highs))[-3:],
        "equal_lows": list(set(equal_lows))[-3:],
    }


# ─── Plotting ─────────────────────────────────────────────────────────────

def plot_candlesticks(ax, df):
    """Plot candlesticks on axis."""
    n = len(df)
    for i in range(n):
        row = df.iloc[i]
        o, h, l, c = row["open"], row["high"], row["low"], row["close"]
        is_up = c >= o

        color = COLORS["candle_up"] if is_up else COLORS["candle_down"]
        wick_color = COLORS["wick_up"] if is_up else COLORS["wick_down"]

        # Wick
        ax.plot([i, i], [l, h], color=wick_color, linewidth=0.8)

        # Body
        body_bottom = min(o, c)
        body_height = abs(c - o)
        if body_height < (h - l) * 0.01:
            body_height = (h - l) * 0.01  # Minimum body height for doji

        rect = Rectangle(
            (i - 0.35, body_bottom), 0.7, body_height,
            facecolor=color, edgecolor=wick_color, linewidth=0.5,
        )
        ax.add_patch(rect)


def plot_fvgs(ax, fvgs, n_candles):
    """Plot Fair Value Gaps."""
    for fvg in fvgs:
        color = COLORS["fvg_bull"] if fvg["type"] == "bullish" else COLORS["fvg_bear"]
        border = COLORS["fvg_border_bull"] if fvg["type"] == "bullish" else COLORS["fvg_border_bear"]
        width = n_candles - fvg["start_idx"]
        rect = Rectangle(
            (fvg["start_idx"], fvg["bottom"]),
            width, fvg["top"] - fvg["bottom"],
            facecolor=color, edgecolor=border, linewidth=0.5, linestyle="--",
        )
        ax.add_patch(rect)


def plot_order_blocks(ax, obs, n_candles):
    """Plot Order Blocks."""
    for ob in obs:
        color = COLORS["ob_bull"] if ob["type"] == "bullish" else COLORS["ob_bear"]
        border = COLORS["ob_border_bull"] if ob["type"] == "bullish" else COLORS["ob_border_bear"]
        width = n_candles - ob["idx"]
        rect = Rectangle(
            (ob["idx"], ob["low"]),
            width, ob["high"] - ob["low"],
            facecolor=color, edgecolor=border, linewidth=0.8,
        )
        ax.add_patch(rect)


def plot_liquidity(ax, liquidity, n_candles):
    """Plot liquidity levels."""
    for sh in liquidity["swing_highs"]:
        ax.axhline(y=sh["price"], color=COLORS["liquidity"], linewidth=0.5,
                   linestyle=":", alpha=0.4)
        ax.plot(sh["idx"], sh["price"], "v", color=COLORS["liquidity"],
                markersize=4, alpha=0.6)

    for sl in liquidity["swing_lows"]:
        ax.axhline(y=sl["price"], color=COLORS["liquidity"], linewidth=0.5,
                   linestyle=":", alpha=0.4)
        ax.plot(sl["idx"], sl["price"], "^", color=COLORS["liquidity"],
                markersize=4, alpha=0.6)

    # Equal highs/lows ($$$ liquidity pools)
    for eh in liquidity.get("equal_highs", []):
        ax.axhline(y=eh, color="#ffd700", linewidth=1.2, linestyle="-", alpha=0.7)
        ax.text(n_candles + 0.5, eh, "$$$", color="#ffd700", fontsize=7,
                va="center", fontweight="bold")

    for el in liquidity.get("equal_lows", []):
        ax.axhline(y=el, color="#ffd700", linewidth=1.2, linestyle="-", alpha=0.7)
        ax.text(n_candles + 0.5, el, "$$$", color="#ffd700", fontsize=7,
                va="center", fontweight="bold")


def plot_pd_zones(ax, df, n_candles):
    """Plot Premium/Discount/Equilibrium zones."""
    look = min(50, len(df))
    recent_high = df["high"].iloc[-look:].max()
    recent_low = df["low"].iloc[-look:].min()
    mid = (recent_high + recent_low) / 2

    # Premium zone (above EQ)
    ax.axhspan(mid, recent_high, facecolor=COLORS["premium"], zorder=0)
    # Discount zone (below EQ)
    ax.axhspan(recent_low, mid, facecolor=COLORS["discount"], zorder=0)
    # Equilibrium line
    ax.axhline(y=mid, color=COLORS["equilibrium"], linewidth=1, linestyle="-",
               label="Equilibrium")

    # Labels
    ax.text(0.5, recent_high - (recent_high - mid) * 0.15, "PREMIUM",
            color="#ff475766", fontsize=9, fontweight="bold", ha="center")
    ax.text(0.5, recent_low + (mid - recent_low) * 0.15, "DISCOUNT",
            color="#00dc8266", fontsize=9, fontweight="bold", ha="center")


def plot_current_price(ax, df, n_candles):
    """Plot current price line."""
    price = df["close"].iloc[-1]
    ax.axhline(y=price, color=COLORS["price_line"], linewidth=1, linestyle="-",
               alpha=0.8)
    ax.text(n_candles + 0.5, price, f" {price:.5f}", color=COLORS["price_line"],
            fontsize=8, va="center", fontweight="bold",
            bbox=dict(boxstyle="round,pad=0.2", facecolor="#0d1117", edgecolor=COLORS["price_line"]))


# ─── Main Chart Builder ──────────────────────────────────────────────────

def build_chart(symbol: str, timeframes: list, bars: int = 100) -> str:
    """Build full ICT markup chart for a symbol."""
    load_env()
    fetcher = OANDAFetcher()

    instrument = symbol.upper().replace("/", "_")
    n_tf = len(timeframes)

    fig, axes = plt.subplots(n_tf, 1, figsize=(18, 5 * n_tf))
    fig.patch.set_facecolor(COLORS["bg"])

    if n_tf == 1:
        axes = [axes]

    now = datetime.now(NY_TZ)
    analysis_summary = {}

    for idx, tf in enumerate(timeframes):
        ax = axes[idx]
        ax.set_facecolor(COLORS["panel"])

        # Fetch
        print(f"  Fetching {instrument} {tf} ({bars} bars)...")
        df = fetch_candles(fetcher, instrument, tf, bars)
        if df.empty:
            ax.text(0.5, 0.5, f"No data for {tf}", transform=ax.transAxes,
                    ha="center", va="center", color=COLORS["text"], fontsize=14)
            continue

        n = len(df)

        # Plot layers (bottom to top)
        plot_pd_zones(ax, df, n)
        plot_candlesticks(ax, df)

        # Detect ICT elements
        fvgs = detect_fvgs(df)
        obs = detect_order_blocks(df)
        liquidity = detect_liquidity_levels(df)

        plot_fvgs(ax, fvgs, n)
        plot_order_blocks(ax, obs, n)
        plot_liquidity(ax, liquidity, n)
        plot_current_price(ax, df, n)

        # Style
        ax.set_xlim(-1, n + 5)
        price_range = df["high"].max() - df["low"].min()
        ax.set_ylim(df["low"].min() - price_range * 0.02,
                    df["high"].max() + price_range * 0.02)
        ax.set_title(f"{instrument}  •  {tf}", color=COLORS["text"],
                     fontsize=13, fontweight="bold", pad=10, loc="left")
        ax.tick_params(colors=COLORS["text"], labelsize=8)
        ax.grid(True, alpha=0.15, color=COLORS["grid"])
        for spine in ax.spines.values():
            spine.set_color(COLORS["grid"])

        # Per-timeframe summary
        current = df["close"].iloc[-1]
        look = min(50, len(df))
        rng_high = df["high"].iloc[-look:].max()
        rng_low = df["low"].iloc[-look:].min()
        mid = (rng_high + rng_low) / 2
        zone = "PREMIUM" if current > mid else "DISCOUNT"

        # Count unfilled FVGs near price
        nearby_fvgs = [f for f in fvgs if abs(f["top"] - current) < price_range * 0.1
                       or abs(f["bottom"] - current) < price_range * 0.1]

        info_text = (f"Price: {current:.5f} | Zone: {zone} | "
                     f"FVGs: {len(fvgs)} ({len(nearby_fvgs)} nearby) | "
                     f"OBs: {len(obs)} | "
                     f"Swing H/L: {len(liquidity['swing_highs'])}/{len(liquidity['swing_lows'])}")
        ax.text(0.99, 0.02, info_text, transform=ax.transAxes,
                color=COLORS["text"], fontsize=7, ha="right", va="bottom",
                alpha=0.7, fontfamily="monospace")

        analysis_summary[tf] = {
            "price": current,
            "zone": zone,
            "fvgs": len(fvgs),
            "order_blocks": len(obs),
            "swing_highs": len(liquidity["swing_highs"]),
            "swing_lows": len(liquidity["swing_lows"]),
            "equal_highs": len(liquidity.get("equal_highs", [])),
            "equal_lows": len(liquidity.get("equal_lows", [])),
        }

        print(f"    ✅ {tf}: {current:.5f} | {zone} | {len(fvgs)} FVGs, {len(obs)} OBs")

    # Legend
    legend_items = [
        mpatches.Patch(facecolor=COLORS["fvg_bull"], edgecolor=COLORS["fvg_border_bull"],
                       label="Bullish FVG", linestyle="--"),
        mpatches.Patch(facecolor=COLORS["fvg_bear"], edgecolor=COLORS["fvg_border_bear"],
                       label="Bearish FVG", linestyle="--"),
        mpatches.Patch(facecolor=COLORS["ob_bull"], edgecolor=COLORS["ob_border_bull"],
                       label="Bullish OB"),
        mpatches.Patch(facecolor=COLORS["ob_bear"], edgecolor=COLORS["ob_border_bear"],
                       label="Bearish OB"),
        plt.Line2D([0], [0], color=COLORS["liquidity"], linewidth=1,
                   linestyle=":", label="Liquidity Level"),
        plt.Line2D([0], [0], color=COLORS["price_line"], linewidth=1,
                   label="Current Price"),
        plt.Line2D([0], [0], color=COLORS["equilibrium"], linewidth=1,
                   label="Equilibrium"),
    ]
    fig.legend(handles=legend_items, loc="upper center", ncol=7,
               fontsize=8, framealpha=0.3,
               facecolor=COLORS["bg"], edgecolor=COLORS["grid"],
               labelcolor=COLORS["text"])

    # Title
    fig.suptitle(f"VEX ICT Markup  •  {instrument}  •  {now.strftime('%Y-%m-%d %H:%M ET')}",
                 color=COLORS["text"], fontsize=15, fontweight="bold", y=0.995)

    plt.tight_layout(rect=[0, 0, 1, 0.97])

    # Save
    timestamp = now.strftime("%Y%m%d_%H%M%S")
    filename = f"{instrument}_markup_{timestamp}.png"
    filepath = SCREENSHOTS_DIR / filename
    fig.savefig(str(filepath), dpi=150, facecolor=fig.get_facecolor(),
                edgecolor="none", bbox_inches="tight")
    plt.close(fig)

    print(f"\n  ✅ Chart saved: {filepath}")

    # Print analysis summary
    print(f"\n  {'═' * 50}")
    print(f"  📊 {instrument} MARKUP SUMMARY")
    print(f"  {'═' * 50}")
    for tf, data in analysis_summary.items():
        print(f"    {tf:4s} | {data['price']:.5f} | {data['zone']:8s} | "
              f"{data['fvgs']} FVG | {data['order_blocks']} OB | "
              f"EQH: {data['equal_highs']} EQL: {data['equal_lows']}")
    print(f"  {'═' * 50}")

    return str(filepath)


# ─── CLI ──────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="VEX ICT Chart Markup")
    parser.add_argument("symbol", help="Trading pair (e.g., NZD_USD, EURUSD)")
    parser.add_argument("--timeframes", nargs="+", default=["D", "H4", "H1", "M15"],
                        help="Timeframes to chart (default: D H4 H1 M15)")
    parser.add_argument("--bars", type=int, default=100,
                        help="Number of bars per timeframe (default: 100)")
    args = parser.parse_args()

    symbol = args.symbol.upper().replace("/", "_")
    if "_" not in symbol and len(symbol) == 6:
        symbol = f"{symbol[:3]}_{symbol[3:]}"

    print(f"\n🎨 VEX Chart Markup: {symbol}")
    print(f"   Timeframes: {args.timeframes}")
    print(f"   Bars: {args.bars}\n")

    filepath = build_chart(symbol, args.timeframes, args.bars)
    print(f"\n  Open: open {filepath}")


if __name__ == "__main__":
    main()
