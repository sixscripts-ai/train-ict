---
description: Standard Operating Procedure for creating professional ICT chart markups
---

# ICT Chart Markup Workflow

This workflow defines the standard process for analyzing user-uploaded charts and generating high-quality ICT markups. It ensures consistency, professional aesthetics, and adherence to ICT methodology.

## 1. Analysis Phase (The "Mental" Markup)

Before generating any image, perform a deep technical analysis of the provided chart using the following checklist:

1.  **Identify the Phase:**
    *   Is price in Consolidation, Expansion, Retracement, or Reversal?
    *   Identify the current Killzone (Asia, London, NY AM/PM).

2.  **Locate Liquidity Pools (The "Draw"):**
    *   **BSL (Buy-Side Liquidity):** Look for clean Equal Highs (EQH), previous day/week highs, or swing highs.
    *   **SSL (Sell-Side Liquidity):** Look for clean Equal Lows (EQL), previous day/week lows, or swing lows.
    *   *Decision:* Which pool is price being drawn to *next*?

3.  **Identify the "Judas Swing" / Stop Hunt:**
    *   Look for a sweep of a recent high/low that immediately reverses.
    *   This is often the "Manipulation" phase.

4.  **Confirm Displacement & MSS:**
    *   **Displacement:** Look for large, energetic candles (wide range bodies) moving away from the sweep.
    *   **MSS (Market Structure Shift):** Did the displacement break a key swing high/low? This confirms the reversal.

5.  **Locate Entry Arrays (PD Arrays):**
    *   **FVG (Fair Value Gap):** The most important array. Look for a 3-candle sequence where the wicks don't overlap.
    *   **OB (Order Block):** The last up-candle before a down-move (or vice versa).
    *   **Breaker:** A failed order block that price smashed through.

## 2. Image Generation Prompt Structure

When using the `generate_image` tool, strictly follow this prompt template to maintain the "Professional Trader" aesthetic:

```text
Annotate this [PAIR] [TIMEFRAME] chart with detailed ICT concepts based on the following analysis:

1. **[Concept 1 - e.g., Liquidity Sweep]:** Mark the [High/Low] at [Price] with a label '[Label]' and an arrow pointing to the wick.
2. **Displacement:** Highlight the aggressive move [Up/Down] away from the sweep.
3. **Market Structure Shift (MSS):** Mark the break of structure at [Price] with a line and label 'MSS'.
4. **[PD Array - e.g., Bullish FVG]:** Identify the gap between [Price A] and [Price B]. Draw a shaded box extending forward and label it '[Bullish/Bearish] FVG (Entry)'.
5. **Draw on Liquidity (Target):** Draw an arrow pointing [Up/Down] towards the target at [Price]. Label it 'Draw on Liquidity ([BSL/SSL])'.

Style: Use professional trading chart aesthetics. Bright green (#00FF00) for bullish elements/targets, Red (#FF0000) for bearish/stops. Ensure text is clear and legible against the background. Use dashed lines for key price levels.
```

## 3. The Output Routine

After generating the image:

1.  **Present the Image:** Embed the generated chart markup.
2.  **Provide the Narrative:** breakdown the markup in bullet points:
    *   **The Setup:** deeply explain *why* the sweep happened (Stop Hunt).
    *   **The Confirmation:** Explain the Displacement and MSS.
    *   **The Entry:** Clearly state where the user should look to enter (the FVG/OB).
    *   **The Target:** Clearly state the Draw on Liquidity.
3.  **Actionable Conclusion:** Give a clear " Bias" (Long/Short) and "Plan" (e.g., "Wait for pullback to 1.1880, target 1.1920").

## 4. Key Rules

*   **Accuracy First:** Never hallucinate a setup. If the chart is unclear/choppy, state "No clear setup" rather than forcing one.
*   **Terminology:** Always use proper ICT terms (BSL, SSL, FVG, MSS, Displacement, breaker, mitigation block).
*   **Colors:** Consistently use **Green** for Bullish and **Red** for Bearish.
