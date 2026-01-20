# Ashton's Trading Philosophy - Core Principles

## FVG vs Order Block Priority

**FOCUS ON FVG, NOT OB**

> "I don't really care too much for order blocks. I trade the fair value gaps because that's where the movement is coming from."

### Why FVG > OB
- Algorithm is trying to bring price back to **THE VOID**
- All it needs is **50% of the imbalance** to continue
- FVG = where the movement originates
- OB is secondary

### FVG Entry - Just Touch, No Confirmation Needed

> "It just needs to touch it. 'Cause it's an algorithm. This is numbers. This is math moving. Price has to balance and when there's that imbalance, price will return there to continue forward."

- **No candle close needed** - pure algorithmic balancing
- **No waiting for confirmation** - the touch IS the event
- **That's why displacement + FVG are THE KEY to all this**

---

## Equal Levels Philosophy

**It's FUNCTIONAL, not TECHNICAL**

- Not about perfect pip-count alignment
- 2-3 candles sitting at same area = **"I'm licking my chops"**
- That's money sitting there waiting to get swept
- **"This is the part of our trading that's different. They don't teach this shit."**

---

## Sweep Philosophy

**Fluid, Not Violent**

- Don't think of sweep as some violent action
- Think of it as **fluid process that is DESTINED**
- Price is headed there anyway
- 20-25-30 pips knocks everybody out
- Doesn't matter if wick or whole candle - **they lost, they got swept**


---

## CRITICAL: Mitigated vs Unmitigated FVGs (2026-01-15)

### The Rule
> "You're thinking that the imbalance still matters after it's been mitigated, and it doesn't as much... You're looking for ones that have been UNTOUCHED. Not the ones that have been returned to price."

### What This Means
- **UNMITIGATED** = Price has NOT returned to the FVG yet → HIGH PRIORITY
- **MITIGATED** = Price already touched it → Less important (support/resistance, but not a fresh target)
- Only show FVGs that are UNTOUCHED when scanning for entries

### Higher Timeframe Controls
- 4H FVG > 15M FVG > 1M FVG
- "The higher time frame is going to control"
- Use lower TF for precise entry, but respect higher TF direction

### VEX Implementation
- Scanner must track if FVG has been touched since formation
- Filter OUT mitigated FVGs from entry signals

### FVG Measurement
- Measured from **WICKS** (high/low), NOT candle bodies
- Candle 1 HIGH or LOW (depending on direction)
- Candle 3 HIGH or LOW (depending on direction)
- The middle candle is where the FVG is "located" (for timestamps)

### FVG Mitigation Check (CRITICAL - 2026-01-15)
- GBP_USD 1.33942 FVG was INVALID - price already went there
- Check if ANY candle after formation touched the 50% level
- If touched = MITIGATED = do not show

---

## PD Array Display Rules (2026-01-15)

### One of Each Per Chart
- **1 FVG** - most current, unmitigated, aligned with flow
- **1 OB** - most current, unmitigated  
- **1 SSL** - nearest BELOW price, unswept
- **1 BSL** - nearest ABOVE price, unswept
- **1 EQL** - nearest equal lows
- **1 EQH** - nearest equal highs

### Must Be:
- CURRENT - not old/historical
- OPTIMAL - aligned with order flow direction
- ACTIVE - not already swept/mitigated
- RELEVANT - the NEXT level to get hit

### Timeframe Rules
- M5 = minimal clutter (just FVGs, maybe 2 max)
- M15 FVGs more pivotal than M5
- HTF controls direction, LTF for entry

---

## Liquidity Targeting (2026-01-15)

### BSL (Buy-Side Liquidity)
- Must be ABOVE current price
- Nearest unswept level = next target up
- If price swept it, it's GONE

### SSL (Sell-Side Liquidity)  
- Must be BELOW current price
- Nearest unswept level = next target down
- If price swept it, it's GONE



### Multiple Candle Wicks
- We **don't like wicks** on multiple candles
- That usually means **institutional sponsorship** (NFP, news events)
- Stay away from that

---

## Displacement Philosophy

**Structure Shift WITH SPEED**

- No ATR formula needed
- Happens during:
  - Optimal trade entry times
  - Sessions (London, NY)
  - Judas swings
- When you see **force AND structure shift with speed** = displacement

### Single vs Multiple Candles
- Can be sequential (like EUR 07:00-09:00)
- Single big candle could be Judas swing
- Timeframe changes perception (15M sequence = 4H single candle)

---

## The Core Question

**"Where is price trying to go? Where's the liquidity - internal or external?"**

This is the foundation of every decision.

---

## Today's Examples (Jan 15, 2026)

1. **EUR/USD** - Equal lows swept, displacement down
2. **DXY** - Bought equal highs, blew right through them (inverse concept)

Same model, different direction.
