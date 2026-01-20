---
title: ICT Mentorship Core Content - Month 08 - Central Bank Dealers Range (CBDR)
type: video_notes
source: https://www.youtube.com/watch?v=nI1AMOC1pro&list=PLVgHx4Z63paZrCT5EaUhJ6sCVNaegCf_c&index=3&pp=iAQB
date_ingested: 2026-01-17
---

# Video Summary
Month 8 Lesson 3 focuses on the **Central Bank Dealers Range (CBDR)**. This range is a critical time-of-day concept used to project the High or Low of the day, specifically for the London Session.

## Key Concepts

### 1. Central Bank Dealers Range (CBDR)
*   **Time Window**: 2:00 PM to 8:00 PM New York Time (14:00 - 20:00).
*   **Definition**: The High and Low formed during this 6-hour window.
*   **Purpose**: It is the "benchmark" range used by algorithms to set the parameters for the next day's trading.

### 2. The Ideal CBDR
*   **Pip Range**: Ideally **20-30 pips**.
*   **Upper Limit**: If > 40 pips, the next day might be choppy or trending less predictably.
*   **Small Range**: Indicates coiled energy and high probability of expansion (Large Range Day).

### 3. Application: Standard Deviations
*   We use the CBDR height (High - Low) as a unit of measurement.
*   **Projections**: Project this range up and down to find logical support/resistance levels.
    *   1 Standard Deviation (SD)
    *   2 Standard Deviations (SD)
    *   3 Standard Deviations (SD)
*   **London High/Low**: The high or low of the day (especially in London) often forms at exactly 1, 2, 3, or sometimes 4 SDs from the CBDR.
*   **Confluence**: Align SD levels with other PD Arrays (Order Blocks, FVGs) for high-precision entries.

### Implementation Checklist
*   [x] **CBDR Detection** (Already exists in SessionRangeDetector).
*   [ ] **CBDR Quality Check**: Add logic to flag if CBDR is "Ideal" (<30 pips) or "Wide" (>40 pips).
*   [ ] **Standard Deviation Projections**: Add method to calculate 1-4 SDs from CBDR.
