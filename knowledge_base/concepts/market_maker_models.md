# Market Maker Models (MMXM)

## Market Maker Buy Model (MMBM)
**Definition:** A complete cycle of price delivery engineered to reprice an asset from a Premium to a Discount, accumulate a generic long position, and then deliver price back to the Original Consolidation.

**Phases:**
1.  **Original Consolidation (OC):** The starting point. Usually a range-bound period where orders are built.
2.  **Engineering Liquidity (EL):** A drive *away* from the intended direction (down in MMBM) to induce sellers.
3.  **Smart Money Reversal (SMR):** The low of the move. Characterized by a Raid on Liquidity (Turtle Soup) or a Failure Swing (SMS).
4.  **Accumulation (A):** Low Risk Buy entry.
5.  **Re-Accumulation (RA):** Second stage entries during the markup phase.
6.  **Distribution (D):** Price reaches the Original Consolidation (the target).

**Key Failure Condition:** If price fails to reach the Original Consolidation, the model may be invalid or incomplete.

## Market Maker Sell Model (MMSM)
**Definition:** The inverse of MMBM. Repricing from Discount to Premium to distribute shorts, then declining back to the Original Consolidation.

**Phases:**
1.  **Original Consolidation:** The target for the final decline.
2.  **Engineering Liquidity:** A drive *up* to induce buyers.
3.  **Smart Money Reversal:** The high of the move. Stop Run on Buy-Side Liquidity.
4.  **Distribution:** Low Risk Sell entry.
5.  **Re-Distribution:** Continuation entries during the markdown.
6.  **Accumulation:** Price returns to the Original Consolidation.

## The Curve (Price Delivery Continuum)
**Concept:** Price moves in a curve from Buy-Side to Sell-Side (and vice versa).
**Identification:**
- **Buy-Side of the Curve:** Price is respecting bullish PD Arrays (Order Blocks, mitigation blocks) and violating bearish ones.
- **Sell-Side of the Curve:** Price is respecting bearish PD Arrays and violating bullish ones.
- **Transition:** The SMR marks the transition from one side of the curve to the other.
