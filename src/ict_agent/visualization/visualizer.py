"""
VEX Enhanced Visualization - Advanced charting and trade replay.

Features:
- Multi-timeframe markup with ICT elements
- Before/after trade comparison charts
- Trade replay functionality
- Session-based chart saving
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import sys

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import Rectangle, FancyBboxPatch
import numpy as np
import pandas as pd

# Import project modules
try:
    from ict_agent.data.oanda_fetcher import OANDAFetcher
    from ict_agent.detectors.fvg import FVGDetector, FVGDirection
    from ict_agent.detectors.order_block import OrderBlockDetector, OBDirection
    from ict_agent.detectors.market_structure import MarketStructureAnalyzer as StructureAnalyzer
    from ict_agent.data.fetcher import DataConfig
except ImportError as e:
    print(f"Import warning: {e}")

# Paths
SCREENSHOTS_DIR = PROJECT_ROOT / "screenshots"
JOURNAL_DIR = PROJECT_ROOT / "journal" / "ashton"
MEMORY_DIR = PROJECT_ROOT / "data" / "memory"

# Style configuration
STYLE_CONFIG = {
    "background": "#1e1e1e",  # Dark charcoal/grey (neutral)
    "candle_up": "#d4d4d4",   # Light grey/white
    "candle_down": "#5a5a5a", # Dark grey
    "fvg_bullish": "#ffffff22", # Whiter/light grey for bullish imbalance
    "fvg_bearish": "#00000044", # Darker for bearish imbalance
    "ob_bullish": "#d4d4d433",  # Light grey zone
    "ob_bearish": "#5a5a5a33",  # Dark grey zone
    "premium_zone": "#5a5a5a11",
    "discount_zone": "#d4d4d411",
    "equilibrium": "#ffffff44",
    "text_color": "#e0e0e0",
    "grid_color": "#2d2d2d",
    "liquidity_high": "#ffffff88",
    "liquidity_low": "#ffffff88"
}


class EnhancedVisualizer:
    """
    Advanced charting with ICT elements and trade visualization.
    """
    
    def __init__(self):
        self.fetcher = OANDAFetcher()
        self.fvg_detector = FVGDetector()
        self.ob_detector = OrderBlockDetector()
        self.structure_analyzer = StructureAnalyzer()
        SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
        
    def fetch_candles(self, pair: str, timeframe: str, bars: int) -> List[Dict]:
        """Fetch candles and convert to list of dicts."""
        try:
            config = DataConfig(symbol=pair, timeframe=timeframe, limit=bars)
            df = self.fetcher.fetch(config)
            
            candles = []
            for idx, row in df.iterrows():
                c = row.to_dict()
                c['time'] = idx # Add timestamp
                candles.append(c)
                
            return candles
        except Exception as e:
            print(f"Error fetching candles: {e}")
            return []
    
    def create_markup(
        self,
        pair: str,
        timeframes: List[str] = None,
        show_fvg: bool = True,
        show_ob: bool = True,
        show_liquidity: bool = True,
        show_pd_zones: bool = True,
        bars: int = 100,
        save: bool = True
    ) -> Tuple[plt.Figure, str]:
        """
        Create comprehensive ICT markup chart.
        
        Args:
            pair: Trading pair
            timeframes: List of timeframes to chart
            show_fvg: Show Fair Value Gaps
            show_ob: Show Order Blocks
            show_liquidity: Show liquidity levels
            show_pd_zones: Show premium/discount zones
            bars: Number of bars to fetch
            save: Whether to save the chart
        
        Returns:
            (figure, filepath) tuple
        """
        if timeframes is None:
            timeframes = ["D", "H4", "H1", "M15"]
        
        # Normalize pair format
        if "_" not in pair:
            pair = f"{pair[:3]}_{pair[3:]}"
        pair = pair.upper()
        
        # Set up figure
        n_charts = len(timeframes)
        fig, axes = plt.subplots(n_charts, 1, figsize=(16, 4 * n_charts))
        fig.patch.set_facecolor(STYLE_CONFIG["background"])
        
        # Handle single timeframe case
        if n_charts == 1:
            axes = [axes]
        
        analysis_data = {}
        
        for idx, tf in enumerate(timeframes):
            ax = axes[idx]
            ax.set_facecolor(STYLE_CONFIG["background"])
            
            # Fetch data
            candles = self.fetch_candles(pair, tf, bars)
            if not candles:
                ax.text(0.5, 0.5, f"No data for {tf}", transform=ax.transAxes,
                       ha='center', va='center', color=STYLE_CONFIG["text_color"])
                continue
            
            # Plot candlesticks
            self._plot_candlesticks(ax, candles)
            
            # Detect ICT elements
            closes = [c["close"] for c in candles]
            highs = [c["high"] for c in candles]
            lows = [c["low"] for c in candles]
            
            # Premium/Discount zones
            if show_pd_zones:
                self._plot_pd_zones(ax, highs, lows, len(candles))
            
            # FVGs
            if show_fvg:
                fvgs = self._detect_fvgs(candles)
                self._plot_fvgs(ax, fvgs, len(candles))
                analysis_data[f"{tf}_fvgs"] = len(fvgs)
            
            # Order Blocks
            if show_ob:
                obs = self._detect_order_blocks(candles)
                self._plot_order_blocks(ax, obs, len(candles))
                analysis_data[f"{tf}_obs"] = len(obs)
            
            # Liquidity levels
            if show_liquidity:
                self._plot_liquidity_levels(ax, highs, lows, len(candles))
            
            # Styling
            ax.set_title(f"{pair} - {tf}", color=STYLE_CONFIG["text_color"], 
                        fontsize=12, fontweight='bold', pad=10)
            ax.tick_params(colors=STYLE_CONFIG["text_color"])
            ax.grid(True, alpha=0.1, color=STYLE_CONFIG["grid_color"])
            
            for spine in ax.spines.values():
                spine.set_color(STYLE_CONFIG["grid_color"])
            
            # Store analysis
            current_price = closes[-1] if closes else 0
            swing_high = max(highs[-20:]) if len(highs) >= 20 else max(highs)
            swing_low = min(lows[-20:]) if len(lows) >= 20 else min(lows)
            mid = (swing_high + swing_low) / 2
            
            if current_price > mid:
                analysis_data[f"{tf}_zone"] = "PREMIUM"
            else:
                analysis_data[f"{tf}_zone"] = "DISCOUNT"
            
            analysis_data[f"{tf}_price"] = current_price
        
        # Add legend
        self._add_legend(fig)
        
        plt.tight_layout()
        
        # Save
        filepath = ""
        if save:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{pair}_markup_{timestamp}.png"
            filepath = str(SCREENSHOTS_DIR / filename)
            fig.savefig(filepath, dpi=150, facecolor=fig.get_facecolor(),
                       edgecolor='none', bbox_inches='tight')
            print(f"✅ Chart saved: {filepath}")
        
        return fig, filepath, analysis_data
    
    def create_trade_chart(
        self,
        pair: str,
        entry: float,
        stop: float,
        target: float,
        direction: str,
        timeframe: str = "M15",
        bars: int = 100
    ) -> Tuple[plt.Figure, str]:
        """
        Create chart with trade levels marked.
        """
        if "_" not in pair:
            pair = f"{pair[:3]}_{pair[3:]}"
        pair = pair.upper()
        
        fig, ax = plt.subplots(figsize=(16, 8))
        fig.patch.set_facecolor(STYLE_CONFIG["background"])
        ax.set_facecolor(STYLE_CONFIG["background"])
        
        # Fetch data
        candles = self.fetch_candles(pair, timeframe, bars)
        if not candles:
            ax.text(0.5, 0.5, "No data", transform=ax.transAxes,
                   ha='center', va='center', color=STYLE_CONFIG["text_color"])
            return fig, ""
        
        # Plot candlesticks
        self._plot_candlesticks(ax, candles)
        
        # Plot trade levels
        n = len(candles)
        
        # Entry line
        ax.axhline(y=entry, color='#00aaff', linestyle='-', linewidth=2, 
                  label=f'Entry: {entry}')
        
        # Stop line
        ax.axhline(y=stop, color='#ff3366', linestyle='--', linewidth=2,
                  label=f'Stop: {stop}')
        
        # Target line  
        ax.axhline(y=target, color='#00ff88', linestyle='--', linewidth=2,
                  label=f'Target: {target}')
        
        # Fill risk/reward zones
        if direction == "LONG":
            ax.axhspan(stop, entry, alpha=0.1, color='#ff3366')  # Risk zone
            ax.axhspan(entry, target, alpha=0.1, color='#00ff88')  # Reward zone
        else:
            ax.axhspan(entry, stop, alpha=0.1, color='#ff3366')  # Risk zone
            ax.axhspan(target, entry, alpha=0.1, color='#00ff88')  # Reward zone
        
        # Calculate R:R
        risk = abs(entry - stop)
        reward = abs(target - entry)
        rr = reward / risk if risk > 0 else 0
        
        # Title with trade info
        ax.set_title(
            f"{pair} {direction} | Entry: {entry} | Stop: {stop} | Target: {target} | R:R: {rr:.1f}:1",
            color=STYLE_CONFIG["text_color"], fontsize=12, fontweight='bold'
        )
        
        ax.legend(loc='upper left', facecolor=STYLE_CONFIG["background"],
                 labelcolor=STYLE_CONFIG["text_color"])
        ax.tick_params(colors=STYLE_CONFIG["text_color"])
        ax.grid(True, alpha=0.1, color=STYLE_CONFIG["grid_color"])
        
        for spine in ax.spines.values():
            spine.set_color(STYLE_CONFIG["grid_color"])
        
        # Save
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{pair}_{direction}_trade_{timestamp}.png"
        filepath = str(SCREENSHOTS_DIR / filename)
        fig.savefig(filepath, dpi=150, facecolor=fig.get_facecolor(),
                   edgecolor='none', bbox_inches='tight')
        
        print(f"✅ Trade chart saved: {filepath}")
        return fig, filepath
    
    def create_before_after(
        self,
        trade_id: str,
        before_bars: int = 50,
        after_bars: int = 50
    ) -> Tuple[plt.Figure, str]:
        """
        Create before/after comparison chart for a completed trade.
        """
        # Load trade from database
        db_path = JOURNAL_DIR / "trades_database.json"
        if not db_path.exists():
            print("No trades database found")
            return None, ""
        
        with open(db_path) as f:
            db = json.load(f)
        
        trade = None
        for t in db.get("trades", []):
            if t.get("id") == trade_id:
                trade = t
                break
        
        if not trade:
            print(f"Trade not found: {trade_id}")
            return None, ""
        
        pre = trade.get("pre_trade", {})
        pair = pre.get("pair", "")
        if not pair:
            print("No pair in trade data")
            return None, ""
        
        if "_" not in pair:
            pair = f"{pair[:3]}_{pair[3:]}"
        
        entry = pre.get("entry_price", 0)
        stop = pre.get("stop_price", 0)
        target = pre.get("target_price", 0)
        direction = pre.get("direction", "LONG")
        exit_price = trade.get("exit_price", target)
        result = trade.get("result", "PENDING")
        pnl = trade.get("pnl_dollars", 0)
        
        # Create figure with 2 subplots
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(20, 8))
        fig.patch.set_facecolor(STYLE_CONFIG["background"])
        
        for ax in [ax1, ax2]:
            ax.set_facecolor(STYLE_CONFIG["background"])
        
        # Fetch data (we'll simulate before/after with the same data for now)
        candles = self.fetch_candles(pair, "M15", before_bars + after_bars)
        if not candles:
            return None, ""
        
        # BEFORE chart (first half)
        before_candles = candles[:before_bars]
        self._plot_candlesticks(ax1, before_candles)
        ax1.axhline(y=entry, color='#00aaff', linestyle='-', linewidth=2)
        ax1.axhline(y=stop, color='#ff3366', linestyle='--', linewidth=2)
        ax1.axhline(y=target, color='#00ff88', linestyle='--', linewidth=2)
        ax1.set_title("BEFORE - Setup", color=STYLE_CONFIG["text_color"],
                     fontsize=14, fontweight='bold')
        
        # AFTER chart (full data)
        self._plot_candlesticks(ax2, candles)
        ax2.axhline(y=entry, color='#00aaff', linestyle='-', linewidth=2, label='Entry')
        ax2.axhline(y=stop, color='#ff3366', linestyle='--', linewidth=2, label='Stop')
        ax2.axhline(y=target, color='#00ff88', linestyle='--', linewidth=2, label='Target')
        ax2.axhline(y=exit_price, color='#ffaa00', linestyle='-', linewidth=3, label='Exit')
        
        result_color = '#00ff88' if result == 'WIN' else '#ff3366'
        ax2.set_title(f"AFTER - {result} (${pnl:.2f})", color=result_color,
                     fontsize=14, fontweight='bold')
        ax2.legend(loc='upper left', facecolor=STYLE_CONFIG["background"],
                  labelcolor=STYLE_CONFIG["text_color"])
        
        for ax in [ax1, ax2]:
            ax.tick_params(colors=STYLE_CONFIG["text_color"])
            ax.grid(True, alpha=0.1, color=STYLE_CONFIG["grid_color"])
            for spine in ax.spines.values():
                spine.set_color(STYLE_CONFIG["grid_color"])
        
        plt.tight_layout()
        
        # Save
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{pair}_beforeafter_{trade_id}_{timestamp}.png"
        filepath = str(SCREENSHOTS_DIR / filename)
        fig.savefig(filepath, dpi=150, facecolor=fig.get_facecolor(),
                   edgecolor='none', bbox_inches='tight')
        
        print(f"✅ Before/After chart saved: {filepath}")
        return fig, filepath
    
    def _plot_candlesticks(self, ax, candles: List[Dict]):
        """Plot candlestick chart."""
        for i, candle in enumerate(candles):
            o, h, l, c = candle["open"], candle["high"], candle["low"], candle["close"]
            
            color = STYLE_CONFIG["candle_up"] if c >= o else STYLE_CONFIG["candle_down"]
            
            # Wick
            ax.plot([i, i], [l, h], color=color, linewidth=1)
            
            # Body
            body_bottom = min(o, c)
            body_height = abs(c - o)
            if body_height < 0.00001:  # Doji
                body_height = 0.00001
            
            rect = Rectangle((i - 0.4, body_bottom), 0.8, body_height,
                            facecolor=color, edgecolor=color)
            ax.add_patch(rect)
        
        ax.set_xlim(-1, len(candles))
    
    def _plot_pd_zones(self, ax, highs: List[float], lows: List[float], n: int):
        """Plot premium/discount zones."""
        swing_high = max(highs[-20:]) if len(highs) >= 20 else max(highs)
        swing_low = min(lows[-20:]) if len(lows) >= 20 else min(lows)
        mid = (swing_high + swing_low) / 2
        
        # Premium zone (above equilibrium)
        ax.axhspan(mid, swing_high, color=STYLE_CONFIG["premium_zone"])
        
        # Discount zone (below equilibrium)
        ax.axhspan(swing_low, mid, color=STYLE_CONFIG["discount_zone"])
        
        # Equilibrium line
        ax.axhline(y=mid, color=STYLE_CONFIG["equilibrium"], linestyle='--', 
                  linewidth=1, alpha=0.5)
    
    def _detect_fvgs(self, candles: List[Dict]) -> List[Dict]:
        """Detect Fair Value Gaps using FVGDetector."""
        if not candles:
            return []
            
        df = pd.DataFrame(candles)
        if 'time' in df.columns:
            df['time'] = pd.to_datetime(df['time'])
            df.set_index('time', inplace=True)
            
        result = self.fvg_detector.detect(df)
        fvgs = []
        
        # Iterate through detected FVGs and format for plotting
        # FVGDetector stores detected FVGs in self.fvg_detector._fvgs
        # But for visualization of a specific batch, we should rely on the returned DataFrame or rebuild logic
        # The DataFrame contains fvg_top, fvg_bottom, fvg_direction columns
        
        for idx_val, row in result.iterrows():
            if not pd.isna(row['fvg_top']):
                # Find integer index in the current candles list
                # This assumes candles list aligns with df index
                try:
                    # Get integer location
                    idx = df.index.get_loc(idx_val)
                    
                    direction = "bullish" if row['fvg_direction'] == FVGDirection.BULLISH.value else "bearish"
                    
                    fvgs.append({
                        "type": direction,
                        "top": row['fvg_top'],
                        "bottom": row['fvg_bottom'],
                        "index": idx
                    })
                except KeyError:
                    continue
                    
        return fvgs

    def _plot_fvgs(self, ax, fvgs: List[Dict], n: int):
        """Plot FVGs on chart."""
        for fvg in fvgs:
            color = STYLE_CONFIG["fvg_bullish"] if fvg["type"] == "bullish" else STYLE_CONFIG["fvg_bearish"]
            # Extend FVG to the right
            ax.axhspan(fvg["bottom"], fvg["top"], 
                      xmin=fvg["index"]/n, xmax=1,
                      alpha=0.3, color=color)

    def _detect_order_blocks(self, candles: List[Dict]) -> List[Dict]:
        """Detect Order Blocks using OrderBlockDetector."""
        if not candles:
            return []
            
        df = pd.DataFrame(candles)
        if 'time' in df.columns:
            df['time'] = pd.to_datetime(df['time'])
            df.set_index('time', inplace=True)
            
        result = self.ob_detector.detect(df)
        obs = []
        
        for idx_val, row in result.iterrows():
            if not pd.isna(row['ob_top']):
                try:
                    idx = df.index.get_loc(idx_val)
                    
                    direction = "bullish" if row['ob_direction'] == OBDirection.BULLISH.value else "bearish"
                    
                    # Use body for OB definition if available (more precise ICT method)
                    top = row['ob_body_top'] if 'ob_body_top' in row and not pd.isna(row['ob_body_top']) else row['ob_top']
                    bottom = row['ob_body_bottom'] if 'ob_body_bottom' in row and not pd.isna(row['ob_body_bottom']) else row['ob_bottom']
                    
                    obs.append({
                        "type": direction,
                        "top": top,
                        "bottom": bottom,
                        "index": idx
                    })
                except KeyError:
                    continue
        
        return obs
    
    def _plot_order_blocks(self, ax, obs: List[Dict], n: int):
        """Plot Order Blocks on chart."""
        for ob in obs:
            color = STYLE_CONFIG["ob_bullish"] if ob["type"] == "bullish" else STYLE_CONFIG["ob_bearish"]
            rect = Rectangle(
                (ob["index"], ob["bottom"]),
                n - ob["index"],
                ob["top"] - ob["bottom"],
                facecolor=color,
                edgecolor=color.replace("44", "88"),
                linewidth=1
            )
            ax.add_patch(rect)
    
    def _plot_liquidity_levels(self, ax, highs: List[float], lows: List[float], n: int):
        """Plot liquidity levels (swing highs/lows)."""
        # Find swing highs
        for i in range(2, len(highs) - 2):
            if highs[i] > highs[i-1] and highs[i] > highs[i-2] and \
               highs[i] > highs[i+1] and highs[i] > highs[i+2]:
                ax.axhline(y=highs[i], color=STYLE_CONFIG["liquidity_high"], linestyle=':', 
                          linewidth=1, alpha=0.5)
                ax.annotate('BSL', (n-5, highs[i]), color=STYLE_CONFIG["liquidity_high"], 
                           fontsize=8, alpha=0.7)
        
        # Find swing lows
        for i in range(2, len(lows) - 2):
            if lows[i] < lows[i-1] and lows[i] < lows[i-2] and \
               lows[i] < lows[i+1] and lows[i] < lows[i+2]:
                ax.axhline(y=lows[i], color=STYLE_CONFIG["liquidity_low"], linestyle=':', 
                          linewidth=1, alpha=0.5)
                ax.annotate('SSL', (n-5, lows[i]), color=STYLE_CONFIG["liquidity_low"], 
                           fontsize=8, alpha=0.7)
    
    def _add_legend(self, fig):
        """Add legend explaining chart elements."""
        legend_elements = [
            mpatches.Patch(facecolor=STYLE_CONFIG["fvg_bullish"], label='Bullish FVG'),
            mpatches.Patch(facecolor=STYLE_CONFIG["fvg_bearish"], label='Bearish FVG'),
            mpatches.Patch(facecolor=STYLE_CONFIG["ob_bullish"], label='Bullish OB'),
            mpatches.Patch(facecolor=STYLE_CONFIG["ob_bearish"], label='Bearish OB'),
            mpatches.Patch(facecolor=STYLE_CONFIG["premium_zone"], label='Premium Zone'),
            mpatches.Patch(facecolor=STYLE_CONFIG["discount_zone"], label='Discount Zone'),
        ]
        
        fig.legend(handles=legend_elements, loc='upper right', 
                  facecolor=STYLE_CONFIG["background"],
                  labelcolor=STYLE_CONFIG["text_color"],
                  framealpha=0.8)


def main():
    """CLI entry point for visualization."""
    import sys
    
    viz = EnhancedVisualizer()
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python visualizer.py markup PAIR [TF1,TF2,...]")
        print("  python visualizer.py trade PAIR DIRECTION ENTRY STOP TARGET")
        print("  python visualizer.py beforeafter TRADE_ID")
        return
    
    cmd = sys.argv[1].lower()
    
    if cmd == "markup" and len(sys.argv) >= 3:
        pair = sys.argv[2].upper()
        timeframes = sys.argv[3].upper().split(",") if len(sys.argv) > 3 else None
        fig, path, data = viz.create_markup(pair, timeframes)
        print("\nAnalysis:")
        for k, v in data.items():
            print(f"  {k}: {v}")
        plt.show()
    
    elif cmd == "trade" and len(sys.argv) >= 7:
        pair = sys.argv[2].upper()
        direction = sys.argv[3].upper()
        entry = float(sys.argv[4])
        stop = float(sys.argv[5])
        target = float(sys.argv[6])
        fig, path = viz.create_trade_chart(pair, entry, stop, target, direction)
        plt.show()
    
    elif cmd == "beforeafter" and len(sys.argv) >= 3:
        trade_id = sys.argv[2]
        fig, path = viz.create_before_after(trade_id)
        if fig:
            plt.show()
    
    else:
        print(f"Unknown command: {cmd}")


if __name__ == "__main__":
    main()
