# VEX CHARTS: Advanced Markup System 📊
*Created by Antigravity (Analyst) for VS Code (Engineer)*

This guide details exactly how to generate institutional-grade ICT chart markups with predictive arrows and liquidity mapping.

## 1. The Tool: `scripts/vex_chart.py`
This Python script is now in your `train-ict/scripts/` directory. It uses `matplotlib`, `pandas`, and `oandapyV20`.

### Usage
```bash
python3 scripts/vex_chart.py [SYMBOL] [TIMEFRAME]
```
Examples:
- `python3 scripts/vex_chart.py EUR_USD H4` (Single Chart)
- `python3 scripts/vex_chart.py GBP_JPY ALL` (Full Multi-Timeframe Stack: D, H4, H1, M15, M5)

## 2. The Logic (How to Think Like VEX)

### Phase 1: Market Structure (Bias)
- Identify swings (Highs/Lows) over last 80 candles.
- **Bullish**: Higher Highs + Higher Lows.
- **Bearish**: Lower Highs + Lower Lows.
- **Mixed**: Conflicting structure (Wait/Neutral).

### Phase 2: Liquidity Mapping (The Targets)
- **BSL (Buy-Side Liquidity)**:
  - Equal Highs (Double Tops within 1.5 pips).
  - Previous Swing Highs (un-swept).
- **SSL (Sell-Side Liquidity)**:
  - Equal Lows (Double Bottoms within 1.5 pips).
  - Previous Swing Lows (un-swept).

### Phase 3: PD Arrays (The Entry)
- **Fair Value Gaps (FVG)**:
  - Identify 3-candle gaps where wicks don't overlap.
  - Filter for **Unmitigated** gaps (price hasn't returned to fill 50%).
  - Sort by distance to current price.

### Phase 4: The Prediction Path (IRL → ERL)
This is the core "Intelligence" of the chart.
- **If Bearish**:
  1. Expect retracement up to nearest **Bearish FVG** or **BSL** (IRL).
  2. Then expect expansion down to nearest **SSL** (ERL).
  3. Draw Orange Path: Current → Retrace Target → Expansion Target.
- **If Bullish**:
  1. Expect retracement down to nearest **Bullish FVG** or **SSL** (IRL).
  2. Then expect expansion up to nearest **BSL** (ERL).
  3. Draw Green Path: Current → Retrace Target → Expansion Target.

## 3. Automation Workflow
To automate this for the user:
1. Detect a **Signal Event** in `VexCoreEngine`.
2. Trigger `vex_chart.py` for that symbol.
3. Save the PNG to `screenshots/`.
4. Open it immediately for user review.

## 4. Key Files
- `scripts/vex_chart.py`: The rendering engine.
- `.env`: API keys (ensure OANDA_API_KEY is set).
- `screenshots/`: Output directory.

---
*Antigravity validated the efficacy of this logic on historical data. Use it to visualize the Brain's decisions.*
