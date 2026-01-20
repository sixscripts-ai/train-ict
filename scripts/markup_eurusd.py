#!/usr/bin/env python3
"""EUR/USD ICT Markup Script"""

import sys
sys.path.insert(0, '/Users/villain/Documents/transfer/ICT_WORK/ict_trainer')

from src.ict_agent.data.oanda_fetcher import OANDAFetcher
from src.ict_agent.detectors.fvg import FVGDetector, FVGDirection
from src.ict_agent.detectors.liquidity import LiquidityDetector, LiquidityType
from src.ict_agent.detectors.order_block import OrderBlockDetector, OBDirection
import pandas as pd
import numpy as np

fetcher = OANDAFetcher()
fvg_detector = FVGDetector()
liquidity_detector = LiquidityDetector()
ob_detector = OrderBlockDetector()

pair = 'EUR_USD'
print('='*60)
print(f'      EUR/USD ICT MARKUP - {pd.Timestamp.now().strftime("%Y-%m-%d %H:%M")}')
print('='*60)

# Fetch multiple timeframes
timeframes = [('D', 'DAILY', 50), ('H4', '4H', 100), ('H1', '1H', 100), ('M15', '15M', 100)]

for tf, label, count in timeframes:
    print(f'\n📊 {label} TIMEFRAME')
    print('-'*40)
    
    df = fetcher.fetch_latest(pair, tf, count)
    current = df['close'].iloc[-1]
    
    print(f'Current Price: {current:.5f}')
    
    # Run detectors - they populate internal state
    liq_df = liquidity_detector.detect(df)
    fvg_df = fvg_detector.detect(df)
    ob_df = ob_detector.detect(df)
    
    # Get liquidity pools from detector state
    pools = liquidity_detector._pools
    bsl = [p for p in pools if p.liquidity_type == LiquidityType.BUY_SIDE and not p.swept][-3:]
    ssl = [p for p in pools if p.liquidity_type == LiquidityType.SELL_SIDE and not p.swept][-3:]
    
    print(f'\nBuy Side Liquidity (above price):')
    for p in bsl:
        eq = " [EQUAL]" if p.is_equal_level else ""
        print(f'  • {p.level:.5f} (str: {p.strength}){eq}')
    if not bsl:
        print('  • None detected')
    
    print(f'\nSell Side Liquidity (below price):')
    for p in ssl:
        eq = " [EQUAL]" if p.is_equal_level else ""
        print(f'  • {p.level:.5f} (str: {p.strength}){eq}')
    if not ssl:
        print('  • None detected')
    
    # Get FVGs from detector state
    fvgs = fvg_detector.get_active_fvgs()
    bullish_fvgs = [f for f in fvgs if f.direction == FVGDirection.BULLISH][-2:]
    bearish_fvgs = [f for f in fvgs if f.direction == FVGDirection.BEARISH][-2:]
    
    print(f'\nBullish FVGs (BISI - support):')
    for f in bullish_fvgs:
        print(f'  • {f.bottom:.5f} - {f.top:.5f} (mid: {f.midpoint:.5f})')
    if not bullish_fvgs:
        print('  • None nearby')
        
    print(f'\nBearish FVGs (SIBI - resistance):')
    for f in bearish_fvgs:
        print(f'  • {f.bottom:.5f} - {f.top:.5f} (mid: {f.midpoint:.5f})')
    if not bearish_fvgs:
        print('  • None nearby')
    
    # Get Order Blocks from detector state
    obs = ob_detector.get_active_order_blocks()
    bullish_obs = [o for o in obs if o.direction == OBDirection.BULLISH][-2:]
    bearish_obs = [o for o in obs if o.direction == OBDirection.BEARISH][-2:]
    
    print(f'\nBullish OBs (demand):')
    for o in bullish_obs:
        print(f'  • {o.low:.5f} - {o.high:.5f}')
    if not bullish_obs:
        print('  • None nearby')
        
    print(f'\nBearish OBs (supply):')
    for o in bearish_obs:
        print(f'  • {o.low:.5f} - {o.high:.5f}')
    if not bearish_obs:
        print('  • None nearby')

print('\n' + '='*60)
print('                     BIAS SUMMARY')
print('='*60)

# Get daily data for bias
daily_df = fetcher.fetch_latest(pair, 'D', 20)
weekly_close = daily_df['close'].iloc[-5:].mean()
current_price = daily_df['close'].iloc[-1]

if current_price > weekly_close:
    bias = "BULLISH"
    bias_emoji = "🟢"
else:
    bias = "BEARISH"
    bias_emoji = "🔴"

print(f'\nHTF Bias: {bias_emoji} {bias}')
print(f'Current: {current_price:.5f}')
print(f'Weekly Avg: {weekly_close:.5f}')
print('\n' + '='*60)
