# Implementation Plan: ICT 2026 Smart Money Concepts (Jan 06)
**Source**: [ICT 2026 Smart Money Concepts In Action](https://youtu.be/Jxl5UJk_ylc?si=vYGdj_kT1kHQE5iQ)
**Date**: 2026-01-17

## 1. Missing Definitions
The following concepts were identified in the source material but are absent from the codebase:

### A. Suspension Block
*   **Context**: "This green shaded area here that is the daily charts suspension block which is a buy side imbalance sell side efficiency within volume... We want to see that offer no real resistance to the upside. We want to see it cut right through that like a hot knife through butter."
*   **Definition**: A specific type of FVG (BISI) on a higher timeframe (Daily) that price is expected to accelerate through, rather than bounce off.
*   **Action Item**: Create `SuspensionBlockDetector` or extend `FVGDetector` to classify FVGs as "Suspension Blocks" if they meet criteria (likely size/speed of formation).

### B. RTH Settlement (Regular Trading Hours)
*   **Context**: "Regular trading hours settlement is down here... if it's going to go back down here then I think it's going to be bearish."
*   **Definition**: The closing price of the previous day's Regular Trading Hours (09:30 - 16:00 ET for Equities, or 17:00 ET for Futures). Serves as a magnet or support/resistance.
*   **Action Item**: Add `calculate_rth_settlement` to `TimeBasedLevelsDetector`.

### C. Pre-Market Highs/Lows
*   **Context**: "I'm wanting the buy side that's resting above the pre-market session highs."
*   **Definition**: The High/Low formed between Midnight (00:00) and NY Open (09:30) or 08:30.
*   **Action Item**: Update `SessionRangeDetector` to explicitly track "Pre-Market" (00:00-09:30 ET) as a distinct session range.

## 2. Refinements (Logic Updates)

### A. Stop Management
*   **Rule**: "If we had been trading for like 15 minutes or 20 minutes in the opening range, then I would have rolled the stop up... But as it is right now (1 min away from open), I want to see it just rip."
*   **Implication**: Stop loss rules should be time-dependent relative to the Opening Bell (09:30 ET).
*   **Action Item**: Update `RiskGuardian` or `TradeManager` to include time-based stop trailing logic (e.g., "Don't trail aggressively immediately before the bell").

### B. Overlap Logic
*   **Rule**: "I don't want to see it completely overlap on that [long up close candle]."
*   **Implication**: When retesting an Order Block or FVG, a full 100% overlap/retracement invalidates the strength.
*   **Action Item**: Add `max_retracement_percent` parameter to `OrderBlockDetector` validation.
