# VEX Trading System Rules

## Chart Screenshots Rule
**Always remember when running the Complete VEX ICT Trading System to get the chart screenshots captured!**

### Implementation:
- Use Playwright with Firefox browser
- Screenshots saved to: `screenshots/` folder
- Naming format: `YYYYMMDD_HHMMSS_SYMBOL_TFm.png`
- TradingView URL: `https://www.tradingview.com/chart/?symbol=OANDA:{SYMBOL}&interval={TF}`

### Script: `scripts/vex_full_system.py`
This script runs the complete 3-step process:
1. **STEP 1: Data Collection** - OANDA price data + TradingView chart screenshot
2. **STEP 2: ICT Analysis** - Killzone, Structure, Liquidity, PD Arrays
3. **STEP 3: Decision Making** - Trade setup, confluences, position sizing

### Example Output:
```
✅ Chart saved: screenshots/20260115_182959_GBPUSD_15m.png
```

---
*Rule added: January 15, 2026*
