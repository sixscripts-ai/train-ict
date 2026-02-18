#!/usr/bin/env python3
"""
Place Trade Script
==================
Places a manual trade via OANDA Executor.

Config:
  Symbol: EUR_USD
  Action: BUY
  Type: MARKET
  Size: 1.0 Lots (100,000 units)
  Stop Loss: 1.18055
  Take Profit: 1.19278
"""

import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Add src to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from ict_agent.execution.oanda_executor import OANDAExecutor

def place_trade():
    print("🚀 Initializing Trade Execution...")
    
    # Load env vars
    load_dotenv()
    
    executor = OANDAExecutor(environment="practice")
    
    # Trade Params
    SYMBOL = "EUR_USD"
    UNITS = 100000  # 1.0 Lot
    STOP_LOSS = 1.18055
    TAKE_PROFIT = 1.19278
    
    print(f"  Symbol: {SYMBOL}")
    print(f"  Action: BUY MARKET")
    print(f"  Size:   {UNITS} units (1.0 Lot)")
    print(f"  SL:     {STOP_LOSS}")
    print(f"  TP:     {TAKE_PROFIT}")
    
    confirm = input("\n⚠️  Confirm execution? (y/n): ")
    if confirm.lower() != 'y':
        print("❌ Trade cancelled by user.")
        return

    print("\n⏳ Sending order...")
    
    result = executor.place_market_order(
        symbol=SYMBOL,
        units=UNITS,
        stop_loss=STOP_LOSS,
        take_profit=TAKE_PROFIT
    )
    
    if result.success:
        print(f"\n✅ TRADE EXECUTED SUCCESSFULLY")
        print(f"   Fill Price: {result.fill_price}")
        print(f"   Trade ID:   {result.trade_id}")
        print(f"   Order ID:   {result.order_id}")
    else:
        print(f"\n❌ TRADE FAILED")
        print(f"   Reason: {result.message}")
        if result.raw_response:
            print(f"   Details: {result.raw_response}")

if __name__ == "__main__":
    place_trade()
