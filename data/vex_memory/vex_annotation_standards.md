# VEX Chart Annotation Standards

## Core Principle: BE SPECIFIC

The goal is PRECISION, not coverage. Mark exactly what you mean.

## Annotation Style Guide

### DO:
- **Thin horizontal lines** for levels (equal highs/lows, liquidity pools)
- **Small rectangles** that fit the EXACT candle body for OBs
- **Tight vertical boxes** for FVGs showing the actual gap
- **Labels RIGHT NEXT to** what you're marking
- **Tell the STORY** - show the sequence (equal lows → sweep → OB/FVG)

### DON'T:
- Big chunky circles that are vague
- Huge boxes covering multiple candles unnecessarily
- Random markings without context
- Mark "sweeps" without showing WHAT level was swept

## Pattern Requirements

### Equal Highs/Lows
- Must be 2+ touches at SAME level
- Draw thin line across those touches
- Label it (e.g., "EQUAL LOWS")

### SSL/BSL Sweep
- Must have a DEFINED level that was swept
- Show the wick that took the level
- Mark the rejection/reversal after

### Order Block
- Small box around the LAST opposite candle before displacement
- Bearish OB = last UP candle before down move
- Bullish OB = last DOWN candle before up move

### Fair Value Gap
- Box the actual GAP (candle 1 high to candle 3 low, or vice versa)
- Label "FVG"
- Note: Forms BECAUSE of displacement

### AMD Pattern
- Show all 3 phases:
  - A = Accumulation (range/equal levels forming)
  - M = Manipulation (sweep/false break)
  - D = Distribution (displacement in true direction)

## The Story Matters

Don't just mark random patterns. Show HOW they connect:

1. HTF bias determines direction
2. Equal levels = liquidity target
3. Sweep takes liquidity (manipulation)
4. Displacement confirms direction
5. OB + FVG form from displacement
6. These become re-entry zones

## Color Coding Standard

- **Cyan/Light Blue**: Equal levels, liquidity pools
- **Pink/Salmon**: Order Blocks
- **Green**: Fair Value Gaps
- **Red arrows/lines**: Bearish elements
- **Text**: White on dark background for readability
