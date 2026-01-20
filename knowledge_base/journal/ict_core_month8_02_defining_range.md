---
title: ICT Mentorship Core Content - Month 08 - Defining The Daily Range
type: video_notes
source: https://www.youtube.com/watch?v=_2nUKLAD9ig&list=PLVgHx4Z63paZrCT5EaUhJ6sCVNaegCf_c&index=2
date_ingested: 2026-01-17
---

# Video Summary
Month 8 Lesson 2 defines the precise time windows that constitute the "Daily Range" and the "IPDA True Day". It moves beyond simple clock time to focus on specific institutional delivery windows.

## Key Concepts

### 1. The IPDA True Day
*   **Time Window**: 00:00 (Midnight) to 15:00 (3 PM) New York Time.
*   **Significance**: This is the period where the majority of the intraday trend and daily range is established. After 3 PM, the market is usually in a "dead zone" or minor consolidation.

### 2. ICT Killzones (Precise Times)
*   **Asian Range**: 20:00 - 00:00 (8 PM - Midnight). Accumulation.
*   **London Killzone**: 01:00 - 05:00. Traditional manipulation window.
*   **New York Killzone**: 07:00 - 10:00. The "Easy" session.
*   **London Close Killzone**: 10:00 - 12:00 (Noon). Reversal or trend termination.

### 3. The 08:20 AM CME Open
*   **Significance**: The opening of the Chicago Mercantile Exchange (CME) at 08:20 AM ET.
*   **Usage**: Often acts as a "second open" or a point of volatility injection shortly before the 08:30 AM news or the 09:30 AM equity open.

### 4. Day Hierarchy
*   **Midnight Open**: The anchor for daily bias.
*   **9:30 AM Open**: The equity anchor.
*   **8:20 AM Open**: The futures anchor.

## Implementation Checklist
*   [x] **Session Times**: Most already exist, but some need slight adjustment to match these precise minutes.
*   [ ] **8:20 AM CME Open**: Add to `OpeningPrices` in `TimeBasedLevelsDetector`.
*   [ ] **15:00 (3 PM) True Day End**: Ensure detectors respect this as the end of the "trading day" for high/low calculation.
