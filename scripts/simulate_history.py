"""
VEX Historical Simulation (Time Machine) 🕒
Tests the VEX Brain (CoreEngine + KnowledgeManager) on past market data.
Simulates a live trading session candle-by-candle.
"""

import sys
import pandas as pd
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from ict_agent.core.vex_core import VexCoreEngine
from ict_agent.learning.knowledge_manager import KnowledgeManager
from ict_agent.data.oanda_fetcher import get_oanda_data

NY_TZ = ZoneInfo("America/New_York")

def run_simulation(symbol: str, days: int = 5):
    print(f"\n🚀 STARTING SIMULATION: {symbol} (Last {days} Days)")
    print("=" * 60)
    
    # Initialize Brains
    engine = VexCoreEngine()
    km = KnowledgeManager()
    
    # Fetch ample history
    print(f"📥 Fetching data for {symbol}...")
    # Get enough candles to cover the period + lookback
    df_15m = get_oanda_data(symbol, timeframe="M15", count=days * 96 + 200)
    df_1h = get_oanda_data(symbol, timeframe="H1", count=days * 24 + 100)
    
    if df_15m is None or df_15m.empty:
        print("❌ Failed to fetch data.")
        return

    # Filter for the simulation window (e.g., start 5 days ago)
    sim_start_time = datetime.now(NY_TZ) - timedelta(days=days)
    
    # We need to slice the dataframe to simulate "live" feed
    # In a real backtest, we'd step candle by candle.
    # For this "Brain Check", we will iterate efficiently through the 15m candles
    # and only "Analyze" during Killzones.
    
    # Identify Killzone candles (7am-11am NY, 2am-5am London)
    df_15m['dt'] = pd.to_datetime(df_15m.index).tz_convert(NY_TZ)
    
    print(f"📊 Analyzing {len(df_15m)} candles...")
    
    trades_found = 0
    rejections = 0
    lunch_rejections = 0
    anti_patterns = 0
    
    for i in range(200, len(df_15m)):
        current_candle = df_15m.iloc[i]
        curr_time = current_candle['dt']
        hour = curr_time.hour
        minute = curr_time.minute
        
        # Optimization: Only analyze during potential killzones
        # London: 2-5, NY: 7-11, Lunch: 12-13 (to test rejection)
        is_active_time = (2 <= hour < 5) or (7 <= hour < 12) or (12 <= hour < 14)
        
        if not is_active_time:
            continue
            
        # Create a "Live" slice (up to this candle)
        # We pass the full history up to 'i' as if it's the current state
        # VexCoreEngine usually takes the full DF and looks at the last row.
        # So we slice:
        current_slice_15m = df_15m.iloc[:i+1]
        current_slice_1h = df_1h[df_1h.index <= current_candle.name] # Approx match
        
        if len(current_slice_1h) < 50:
            continue
            
        # === THE BRAIN CHECK ===
        try:
            result = engine.analyze(symbol, current_slice_15m, current_slice_1h)
            
            if result.trade and result.setup:
                setup = result.setup
                formatted_time = curr_time.strftime("%Y-%m-%d %H:%M")
                
                # Knowledge Graph Validation
                validation = km.validate_setup(
                    confluences=setup.confluences,
                    model=setup.model.value,
                    session=setup.killzone
                )
                
                print(f"\nTime: {formatted_time} | Model: {setup.model.value} | Bias: {setup.bias.value}")
                print(f"   Setup: {setup.entry_reason}")
                
                if validation["valid"]:
                    print(f"   ✅ [ACCEPTED] Score: {validation['score']}/10")
                    trades_found += 1
                else:
                    print(f"   ❌ [REJECTED] {', '.join(validation['missing'] + validation['anti_patterns'])}")
                    print(f"      Warnings: {validation['warnings']}")
                    rejections += 1
                    
                    if "Lunch" in str(validation['warnings']):
                        lunch_rejections += 1
                    if validation['anti_patterns']:
                        anti_patterns += 1
        
        except Exception as e:
            # print(f"Error at {curr_time}: {e}")
            pass

    print("\n" + "=" * 60)
    print(f"🏁 SIMULATION COMPLETE: {symbol}")
    print(f"   Valid Trades Found: {trades_found}")
    print(f"   Rejected Setups: {rejections}")
    print(f"     - Lunch/Time Rules: {lunch_rejections}")
    print(f"     - Anti-Patterns: {anti_patterns}")
    print("=" * 60)

if __name__ == "__main__":
    # Test on EUR_USD for last 3 days
    run_simulation("EUR_USD", days=3)
