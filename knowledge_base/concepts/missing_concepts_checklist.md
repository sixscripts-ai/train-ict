# Missing Concepts Checklist

Use this checklist to identify concepts that need to be defined and added to the `terminology.yaml` or `concepts/` directory.

## Advanced Price Action
- [ ] **Inversion Fair Value Gap (IFVG)**: A FVG that price respects as support after being resistance (or vice versa).
- [ ] **Balanced Price Range (BPR)**: Overlapping Fair Value Gaps from opposite dictions (e.g., a pumping candle with a FVG immediately followed by a dumping candle with a FVG).
- [ ] **Volume Imbalance (VI)**: A gap between the *bodies* of two candles, but wicks overlap.
- [ ] **Opening Gap**: The gap between the opening price of the current session/day and the closing price of the previous one.
- [ ] **Reclaimed Order Block**: An order block that was violated but is now being used again.
- [ ] **Vacuum Block**: A gap created by a liquidity event (like news) that acts as a void.
- [ ] **Rejection Block**: A swing high/low with a long wick; the "block" is the region from the highest open/close to the high/low.

## Time & Macro
- [ ] **The "Algorithm" Macros**: Specific 20-minute windows (e.g., 9:50-10:10 AM EST).
- [ ] **Quarterly Shifts**: How the algorithm changes characteristics every 3-4 months (IPDA Data Ranges).
- [ ] **90-Minute Cycles**: The market's internal rhythm.

## Analysis Techniques
- [ ] **IPDA (Interbank Price Delivery Algorithm)**: The theoretical AI that drives price.
- [ ] **Data Ranges**: Looking back 20, 40, 60 days for liquidity pools.
- [ ] **Dealing Range**: Defining the current fractal trading range to find Premium/Discount.
