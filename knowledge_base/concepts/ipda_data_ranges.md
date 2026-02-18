# IPDA Data Ranges (Lookback Periods)

## Overview
The Interbank Price Delivery Algorithm (IPDA) references historical data in specific "lookback" periods to determine liquidity targets and rebalancing objectives. Understanding these ranges helps traders anticipate where price is likely to reach.

## The Lookback Periods

### 20-Day Range (Short-Term)
- **Timeframe:** Approximately 1 trading month.
- **Significance:** Represents the immediate short-term institutional flow.
- **Application:**
    - Look for old highs/lows within the last 20 trading days as primary liquidity targets for intraday/short-term trades.
    - Identify the "Dealing Range" of the current month.

### 40-Day Range (Intermediate-Term)
- **Timeframe:** Approximately 2 trading months.
- **Significance:** Standard institutional review period. Often aligns with the "central" portion of a quarterly move.
- **Application:**
    - Swings that formed 20-40 days ago are often revisited if the short-term trend fails.
    - Used to frame intermediate-term bias.

### 60-Day Range (Long-Term / Quarterly)
- **Timeframe:** Approximately 3 trading months (1 quarter).
- **Significance:** The primary institutional cycle. Banks and large institutions operate on quarterly cycles.
- **Application:**
    - The "Quarterly Shift" often occurs every 3-4 months.
    - Liquidity pools resting beyond the 60-day high/low are major draw-on-liquidity targets for macro reversals.

## Dealing Range
**Definition:** The current price range (High to Low) established by a major swing high and swing low, within which price is currently fluctuating.
- **Premium vs. Discount:** The Dealing Range is divided into Premium (upper 50%) and Discount (lower 50%).
- **IPDA Function:** The algorithm seeks to:
    1.  Take liquidity from one side (e.g., Sell-Side).
    2.  Retrace to a PD Array in the opposite zone (e.g., Premium).
    3.  Expand to the opposing liquidity (e.g., Buy-Side).
- **Identification:** Identify the most recent *break of structure* or *significant swing*. The range created by that swing is the current Dealing Range.
