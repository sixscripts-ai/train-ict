# Market Maker Buy/Sell Model (MMBM / MMSM)

The **Market Maker Model** is the complete cycle framework that contains all ICT entry setups. Understanding which phase you're in determines which setups to look for and which direction to trade.

---

## Model Types

| Model | Direction | Smart Money Action | Entry Type |
|-------|-----------|-------------------|------------|
| **MMSM** (Sell Model) | SHORT | Accumulated longs → distributing shorts | Redistribution |
| **MMBM** (Buy Model) | LONG | Accumulated shorts → distributing longs | Reaccumulation |

---

## MMSM - Market Maker Sell Model

**Goal:** Take price from highs to lows

### Phases:

```
1. ACCUMULATION (Buy Side)
   └── Smart money buying on left side of curve
   └── Building long positions to sell later

2. LIQUIDITY RUN (High)
   └── Takes buy-side liquidity (equal highs, prior highs)
   └── Retail longs get trapped
   └── Smart money sells into this liquidity

3. SMART MONEY REVERSAL (SMR)
   └── Location: ABOVE equilibrium (50% of dealing range)
   └── Signature: Sharp displacement DOWN
   └── Market structure shift bearish
   └── Creates FVG/OB for entry

4. REDISTRIBUTION
   └── Price retraces into premium
   └── SHORT entry zones (OB, FVG, mitigation blocks)
   └── Multiple redistribution opportunities
   └── "Sells what they bought on the left"

5. FINAL TARGET (Sell-Side)
   └── Equal lows, prior lows, sell-side liquidity
   └── Take profits here
   └── Cycle complete
```

### MMSM Visual:
```
        [2. Liquidity Run High]
              /\
             /  \
  [1. Accum]/    \[3. SMR]
           /      \
                   \  [4. Redistribution zones]
                    \    /\
                     \  /  \
                      \/    \
                            [5. Sell-Side Target]
```

---

## MMBM - Market Maker Buy Model

**Goal:** Take price from lows to highs

### Phases:

```
1. ACCUMULATION (Sell Side)
   └── Smart money selling on left side of curve
   └── Building short positions to cover later

2. LIQUIDITY RUN (Low)
   └── Takes sell-side liquidity (equal lows, prior lows)
   └── Retail shorts get trapped
   └── Smart money buys into this liquidity

3. SMART MONEY REVERSAL (SMR)
   └── Location: BELOW equilibrium (50% of dealing range)
   └── Signature: Sharp displacement UP
   └── Market structure shift bullish
   └── Creates FVG/OB for entry

4. REACCUMULATION
   └── Price retraces into discount
   └── LONG entry zones (OB, FVG, mitigation blocks)
   └── Multiple reaccumulation opportunities
   └── "Buys what they sold on the left"

5. FINAL TARGET (Buy-Side)
   └── Equal highs, prior highs, buy-side liquidity
   └── Take profits here
   └── Cycle complete
```

### MMBM Visual:
```
                            [5. Buy-Side Target]
                      /\    /
                     /  \  /
                    /    \/
                   /  [4. Reaccumulation zones]
  [1. Accum]\    /[3. SMR]
             \  /
              \/
        [2. Liquidity Run Low]
```

---

## How Entry Setups Fit Into MM Models

| Setup Type | MMSM Phase | MMBM Phase |
|------------|------------|------------|
| OB_FVG_retrace | Redistribution (short) | Reaccumulation (long) |
| Judas_into_OB | SMR / Early redistribution | SMR / Early reaccumulation |
| Liquidity_Sweep_Reversal | SMR | SMR |
| CBDR_ASIA_SD | Any phase (session-based) | Any phase (session-based) |
| LTF_refinement | Redistribution | Reaccumulation |

---

## Schema Integration

When logging trades, include:

```json
"mm_model": {
  "type": "MMSM",
  "phase": "redistribution",
  "dealing_range": {
    "high": 1.1650,
    "low": 1.1580,
    "equilibrium": 1.1615
  },
  "entry_relative_to_eq": "above",
  "target_liquidity": "equal_lows_1.1560"
}
```

### Valid Phases:

**MMSM:**
- `accumulation_buyside`
- `liquidity_run_high`
- `smart_money_reversal`
- `redistribution`
- `sellside_target`

**MMBM:**
- `accumulation_sellside`
- `liquidity_run_low`
- `smart_money_reversal`
- `reaccumulation`
- `buyside_target`

---

## Full Schema (Reference)

```
MarketMakerModelSetup
├── 1. HigherTimeframeContext
│   ├── Instrument
│   ├── HTF_Charts: [Daily, 4H, 1H]
│   ├── Key_HTF_Levels:
│   │   ├── PriorHighs/Lows
│   │   ├── EqualHighs/Lows
│   │   ├── FVGs
│   │   └── OrderBlocks
│   ├── DrawOnLiquidity:
│   │   ├── PrimaryTarget (buy-side / sell-side)
│   │   └── SecondaryTargets
│   └── DirectionalBias
│
├── 2. DealingRangeDefinition
│   ├── ITF_Charts: [15m, 5m, 1m]
│   ├── ImpulseDirection (Up for MMSM / Down for MMBM)
│   ├── RangeHigh, RangeLow, Equilibrium(50%)
│   └── LeftSideAccumulationZones
│
├── 3. ModelType
│   ├── Type: MMSM / MMBM
│   ├── CurveSide:
│   │   ├── BuySideOfCurve (left accumulations)
│   │   └── SellSideOfCurve (right distributions)
│   └── ExpectedSequence:
│       ├── LiquidityRun
│       ├── DisplacementLeg
│       ├── SmartMoneyReversal (SMR)
│       ├── Redistribution/Reaccumulation Zones
│       └── FinalLiquidityTarget
│
├── 4. SmartMoneyReversal
│   ├── LocationRelativeToRange:
│   │   ├── AboveEquilibrium (MMSM)
│   │   └── BelowEquilibrium (MMBM)
│   ├── HTFConfluence (FVG, OB, External Liquidity)
│   ├── ReversalSignature (Displacement, MSS)
│   └── LowRiskEntryZone_1
│
├── 5. Redistribution / Reaccumulation
│   ├── CarriedOverRanges
│   ├── RightSideBehavior (chop, time elongation)
│   ├── Redistribution/Reaccumulation Zones
│   └── ValidShort/LongAreas
│
├── 6. TradeExecutionPlan
│   ├── EntrySetups (trigger, direction, price)
│   ├── StopPlacement
│   ├── Targets (TP1, TP2, TP3)
│   └── ManagementRules
│
└── 7. PostTradeReview
    ├── WasDirectionalBiasCorrect?
    ├── WasModelSequenceRespected?
    ├── TimingAssessment
    ├── ExecutionErrors
    └── LessonsForNextModel
```

---

## Key Insights

1. **Know which model is active BEFORE looking for entries**
2. **SMR is the turning point** - miss this, miss the move
3. **Redistribution/Reaccumulation = multiple entry opportunities**
4. **Entry setups are WITHIN phases, not separate from them**
5. **Your A+ trades happen when you catch SMR → first redistribution/reaccumulation**
