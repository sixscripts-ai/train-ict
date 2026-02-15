---
title: ICT Mentorship Core Content - Month 08 - Essentials To ICT Daytrading
type: video_notes
source: https://www.youtube.com/watch?v=-cXnnHjy9s0
date_ingested: 2026-01-17
---

# Video Summary
Month 8 Lesson 1 focuses on the **Day Trading Model**. It outlines the core philosophy of capitalizing on the daily range (targeting 65-70%) and provides strict rules for day-of-week and time-of-day operations.

## Key Concepts

### 1. The Daily Range Objective
*   **Goal**: Capture 65-70% of the movement in a single 24h period.
*   **Frequency**: ~2 setups per day on average.
*   **Target**: Last 5 days Average Daily Range (ADR).

### 2. Time of Day (Killzones) - New York Time
*   **London Open**: 02:00 - 05:00 (manipulation/high-low formation).
*   **London Lunch**: 05:00 - 07:00 (Retracement/Consolidation/Reversal). *New concept*.
*   **New York Open**: 07:00 - 10:00 (Easiest to trade).
*   **London Close**: 14:00 - 15:00 (Profit taking/Reversal).
*   **Asian Session**: 19:00 - 00:00 (Accumulation).

### 3. Weekly Profiles & Directional Bias
*   **Sunday Opening Price Filter**:
    *   **Bearish Bias**: Look for shorts ONLY when price is **BELOW** the Sunday/Monday opening price.
    *   **Bullish Bias**: Look for longs ONLY when price is **ABOVE** the Sunday/Monday opening price.
    *   *Usage*: Draw the opening price line out until Thursday.
*   **Tuesday Importance**:
    *   **Bullish Week**: 70% chance Tuesday London forms the **Low of the Week**.
    *   **Bearish Week**: 70% chance Tuesday London forms the **High of the Week**.
*   **Wednesday**: Ideal day trading day (midweek data available).
*   **Thursday**: Can often mark the reversal or the cap of the weekly range.

### 4. Special Rules
*   **London Extension Rule**: If London session expands >80% of the ADR, **AVOID New York**. It will likely chop or reverse.
*   **FOMC/NFP**: NO TRADING. Sidelines.

## Implementation Checklist
*   [x] Weekly Open Level Detection (Already in TimeBasedLevels).
*   [ ] **London Lunch detection** (Adding to SessionRangeDetector).
*   [ ] **Sunday Open Filter** in VexBrain (Strict directional filter).
*   [ ] **Tuesday High/Low Weighting** (Increase confidence if trading on Tuesday in line with bias).
