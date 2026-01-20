# ICT Trading Concepts and Models - Processed Knowledge Base

## Core Concepts

### 1. Liquidity Framework

#### External Range Liquidity
- **Definition**: Liquidity resting outside current short-term dealing range
- **Locations**: Above double tops (buy-side) and below double bottoms (sell-side)
- **Purpose**: Often targeted for stop runs or breakouts
- **Trading Application**: Primary targets for internal range liquidity entries

#### Internal Range Liquidity
- **Components**: Fair Value Gaps (FVGs), liquidity voids, order blocks
- **Function**: Entry points within current dealing range
- **Relationship**: Entries from internal liquidity typically target external liquidity
- **Reverse Application**: Turtle soup entries (fading stop runs) target internal liquidity for exits

#### Low Resistance Liquidity Runs
- **Concept**: Price movements characterized by smooth runs toward identified liquidity pools
- **Application**: Key for identifying high-probability trade directions

### 2. Order Blocks

#### Definition and Identification
- **Core Concept**: Last opposing candle before significant price move
- **Enhanced Reliability Factors**:
  - Break of Market Structure (Breaker)
  - Associated Fair Value Gaps
  - Traded during ICT Kill Zones
  - Formed after run on stops (liquidity grab)

#### Order Block Types
- **Bullish Order Block**: Down-close candle before upward move
- **Bearish Order Block**: Up-close candle before downward move
- **Reclaimed Order Block**: Old order blocks revisited after breaker

#### Validation Criteria
- Must be traded into during kill zones for validity
- Higher probability when associated with FVGs
- Enhanced reliability after breaker formation
- Increased trust after stop runs

### 3. Fair Value Gaps (FVGs) and Inefficiencies

#### Core Characteristics
- **Definition**: Price ranges with lack of efficient trading
- **Visual**: Gap between wicks of consecutive candles
- **Function**: Act as price magnets and entry points

#### Trading Applications
- **Entry Strategy**: Bottom of gap entry with stop beyond opposite side
- **Limit Orders**: Midpoint entries for live market conditions
- **Consequent Encouragement (CE)**: Midpoint as significant support/resistance

#### Model 12 Integration
- **Setup**: FVGs forming after order block expansion swing
- **Target**: 20-pip scalping opportunities
- **Timing**: Must occur during kill zones

### 4. Time-Based Analysis

#### Kill Zones (New York Time)
- **Asian Range**: 8:00 PM - Midnight EST
- **London Kill Zone**: 1:00 AM - 5:00 AM EST
- **New York Kill Zone**: 7:00 AM - 10:00 AM EST
- **London Close Kill Zone**: 10:00 AM - 12:00 PM EST
- **CME Open**: 8:20 AM NY Time (significant turning point)

#### Central Bank Dealers Range (CBDR)
- **Time Frame**: 2:00 PM - 8:00 PM New York time
- **Ideal Range**: Less than 40 pips (preferably 20-30 pips)
- **Application**: Basis for daily high/low projections using standard deviations

#### Time-Based Projections
- **Sell Days**: High of day typically 1-3 standard deviations above CBDR
- **Buy Days**: Low of day typically 2+ standard deviations below CBDR
- **2:00 PM Rule**: Usually caps higher low of trending days

## Trading Models

### Model 11: 30 Pips Intraday Trade Model
- **Classification**: "Bread and butter" model with frequent setups
- **Chart Analysis**: 60-minute for expansion potential, 15/5-minute for entry
- **Entry Method**: Optimal Trade Entry (OTE) at 62% Fibonacci (+/- 5 pips)
- **Target**: Fixed 30-pip profit
- **Stop Loss**: Initial 20 pips, adjustable as trade progresses
- **Timing**: London and New York open kill zones
- **Requirements**: Weekly bias alignment and volatility injections

### Model 12: 20 Pips Scalping Model
- **Focus**: Quick scalping opportunities
- **Setup Sequence**: Order block → Expansion swing → Fair value gap entry
- **Entry Method**: Institutional order flow entry drill (+/- 5 pips) on 5-minute chart
- **Target**: Fixed 20-pip profit
- **Stop Loss**: Standard 20 pips
- **Timing**: Must occur during ICT kill zones
- **Requirements**: Daily range expansion context

### Model 7: Universal Trade Plan
- **Application**: All trading styles with sell-side focus
- **Components**:
  - **Stage**: Liquidity draw to higher timeframe level
  - **Setup**: Sell-side market maker profile
  - **Pattern**: Fair value gap as primary entry trigger
- **Entry Points**: Premium FVGs or short buy stops during redistribution
- **Target**: Sell-side liquidity below old lows

## Market Maker Models

### Sell-Side Market Maker Profile
1. **Consolidation**: Initial range formation
2. **Manipulation**: Run-up to induce buying
3. **Distribution**: Retracement back to consolidation
4. **Sell-off**: Target sell-side liquidity below old lows

### Liquidity Distribution (IPDA)
- **Concept**: Interbank Price Delivery Algorithm distribution
- **Monitoring**: Price fluctuations within predetermined ranges
- **Application**: Identify true order flow on buy/sell sides

### Market Structure Shifts
- **Qualification**: Highest reaccumulation level taken out
- **Significance**: Confirms directional bias change
- **Application**: Entry timing for continuation moves

## High Probability Day Trades

### Bullish Conditions
- **Order Flow**: Bullish institutional sentiment
- **Entry**: Discount PD array reaction (bullish order block)
- **Path**: Clear route to opposing premium array
- **Ideal Days**: Monday, Tuesday, Wednesday
- **CBDR Requirements**: <40 pips, Asian range ≤20 pips
- **Entry Locations**:
  - 1-2 standard deviations of CBDR/Asian range
  - Below Asian range into FVGs/bullish order blocks

### Bearish Conditions
- **Order Flow**: Bearish institutional sentiment
- **Entry**: Premium PD array reaction (bearish order block)
- **Path**: Clear route to opposing discount array
- **Ideal Days**: Tuesday, Wednesday, Thursday
- **CBDR Requirements**: <40 pips, Asian range ≤20 pips
- **Entry Locations**:
  - 1-2 standard deviations of CBDR/Asian range
  - Above Asian range into FVGs/bearish order blocks

## Daily Range Projections

### CBDR-Based Projections
- **Method**: Use CBDR pip range for standard deviation calculations
- **Premium Days**: Project from highs after premium PD array during London
- **Discount Days**: Project from lows after discount PD array during London
- **Multiplier Effect**: London range becomes multiplier for daily range projection

### 0 GMT Opening Price Strategy
- **Reference Point**: Midnight New York time opening price
- **Power Three Application**: Accumulation, manipulation, distribution around opening
- **Judas Swing**: Temporary opposite direction move in London session
- **Entry Strategy**: Limit orders above/below 0 GMT opening
- **Stop Loss**: Based on 5-day average daily range

## Natural Market Structure Breaks

### Characteristics
- **High Energy Moves**: Significant range candles
- **Level Violation**: Breaking previous highs/lows with conviction
- **Closing Requirement**: Must close beyond the level
- **Inversion Principle**: Broken support becomes resistance (vice versa)

### Retest vs Retrade
- **Retest**: Multiple small touches of broken level
- **Retrade**: Significant move back to broken level
- **Timing**: Often occurs during kill zones
- **Continuation**: Typically followed by move in break direction

### Stop Run vs True Break
- **Stop Run**: Brief violation returning quickly
- **True Break**: High energy move with meaningful distribution
- **Context**: Equal lows break with high energy suggests true break

## Implementation Guidelines

### Bias and Higher Timeframe Analysis
- **Requirement**: Directional bias from higher timeframe PD arrays
- **Institutional Order Flow**: Must align with intraday setups
- **Success Factor**: Higher timeframe alignment crucial for model success

### Practice and Personalization
- **Backtesting**: Essential for model validation
- **Personality Fit**: Find resonating "bread and butter" setups
- **Flexibility**: Adapt core concepts to individual trading style
- **Simplification**: Make as simple or complex as needed

### Risk Management
- **Stop Loss Placement**: Specific to entry scenario and model
- **Profit Taking**: Scale out at key levels and time intervals
- **Position Sizing**: Align with account risk parameters
- **Time Management**: Respect kill zone timing for optimal results

## Key Success Factors

1. **Liquidity Awareness**: Understand internal vs external liquidity dynamics
2. **Time Sensitivity**: Respect kill zones and CBDR timing
3. **Structure Recognition**: Identify natural breaks vs stop runs
4. **Bias Alignment**: Ensure higher timeframe and intraday alignment
5. **Model Consistency**: Stick to chosen model parameters
6. **Risk Control**: Maintain disciplined stop loss and profit taking
7. **Market Context**: Consider CBDR range and daily projections
8. **Pattern Recognition**: Develop skill in identifying PD arrays

This processed knowledge base provides a comprehensive framework for implementing ICT trading concepts with specific focus on actionable strategies and clear implementation guidelines.