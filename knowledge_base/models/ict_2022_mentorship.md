# ICT 2022 Mentorship Model (The "Index Model")

## Overview
The ICT 2022 Mentorship is a streamlined, algorithmic trading model designed specifically for **Index Futures** (ES, NQ) but applicable to Forex and Crypto. It focuses on removing "analysis paralysis" by providing a single, repeatable setup that occurs frequently.

**Core Philosophy**: "If you can identify where liquidity is (Stops), and you wait for the 'Smart Money' to displace price away from that level, you have an edge."

## The "2022 Model" Setup
This is the specific algorithmic pattern taught in the mentorship. It is a reversal pattern that forms after liquidity runs.

### 1. The Narrative (Pre-Conditions)
*   **Time**: Trading must occur during specific "Killzones":
    *   **New York AM**: 8:30 AM - 11:00 AM EST (Primary focus of 2022 model).
    *   **New York PM**: 1:30 PM - 4:00 PM EST.
*   **Daily Bias**: You should (ideally) only take trades in the direction of the Higher Timeframe (Daily/4H) expansion.
*   **Draw on Liquidity (DOL)**: Identify where price is *going* next (e.g., an old daily high/low or an imbalance).

### 2. The Setup Logic (Step-by-Step)
1.  **Run on Liquidity**: Price moves above an old High (Buy-side Liquidity) or below an old Low (Sell-side Liquidity).
    *   *Why?* To pair institutional orders with retail stops.
2.  **Market Structure Shift (MSS)**: Price rapidly reverses and breaks a short-term swing point in the opposite direction.
    *   *Key*: This move must be **energetic** (Displacement). It shouldn't lethargically drift past the swing point.
3.  **Displacement**: The candle(s) that break structure must be large, creating a **Fair Value Gap (FVG)**.
    *   *Note*: If there is no FVG, there is no trade.
4.  **Return to Fair Value**: Price retraces back into the FVG (and optionally an Order Block or OTE level within it).
5.  **Entry**: Place a Limit Order at the open or 50% (CE) of the FVG.

### 3. Execution Rules
*   **Stop Loss**:
    *   **Aggressive**: Above/Below the candle that created the FVG.
    *   **Conservative**: Above/Below the Swing High/Low that swept liquidity.
*   **Take Profit**:
    *   **Target 1 (Low Hanging Fruit)**: The nearest opposing swing point (liquidity pool).
    *   **Target 2**: 1:2 or 1:3 Risk/Reward.
    *   **Target 3**: The opposing Higher Timeframe DOL.

## Visual Representation

**Bearish Setup (Short)**
```
      (Liquidity Sweep)
          ^
         / \
   (High)/   \
   -----/-----\--------- Old High (BSL)
       /       \
      /         \  <-- Displacement (Big Down Candle)
     /           \
                  \
                   \
    (MSS) ---------\--------- Previous Swing Low
                     \
                      \   (FVG Forms Here)
                       \
                        \
                         \____ (Price Retraces UP into FVG -> ENTER SHORT)
```

## Mentorship Content Breakdown (The 41 Episodes)

### Phase 1: Foundation (Episodes 1-12)
*   **Internal vs External Range Liquidity**: The market oscillates between taking external stops (Highs/Lows) and rebalancing internal imbalances (FVGs).
*   **Market Structure**: Defining Swing Highs and Swing Lows rigorously.
*   **The Algorithm**: Introduction to the concept that price is driven by an algorithm (IPDA), not random buying/selling.

### Phase 2: The Setup details (Episodes 13-20)
*   **Displacement**: How to identify true institutional intent vs "fake" moves.
*   **Fair Value Gaps**: The primary entry mechanism.
*   **Daily Bias**: Using the Daily/Weekly chart to frame the trade.

### Phase 3: Refinement & Nuance (Episodes 21-30)
*   **Tape Reading**: Watching the 1-minute chart for signs of accumulation/distribution without indicators.
*   **Time of Day**: Why 8:30 AM (News releases) is the "opening bell" for the algorithm.
*   **SMT Divergence**: Using correlated assets (ES vs NQ) to confirm the liquidity sweep (e.g., ES makes a higher high, NQ fails to make a higher high = Bearish SMT).

### Phase 4: Risk & Psychology (Episodes 31-41)
*   **Model Building**: How to write a trade plan.
*   **Risk Management**: Never risking more than 1-2% per trade.
*   **The "One Setup" Life**: You only need this ONE model to be profitable.

## Cheat Sheet Checklist
- [ ] **Bias**: Is the Daily/4H chart Bullish or Bearish?
- [ ] **Time**: Is it between 8:30 AM and 11:00 AM EST?
- [ ] **News**: Are there high-impact news drivers (CPI, NFP) to avoid or wait for?
- [ ] **Liquidity**: Did we just sweep a clear High/Low?
- [ ] **Shift**: Did we break structure with FORCE (Displacement)?
- [ ] **Imbalance**: Did that move leave a FVG?
- [ ] **Entry**: Limit order set at the FVG.
- [ ] **Risk**: Stop loss set defined? Risk < 2%?
