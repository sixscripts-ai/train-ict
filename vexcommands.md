# ═══════════════════════════════════════════════════════════════════════════════
#                              VEX COMMAND CENTER v2.1
#                         ICT Trading Journal & Advisor AI
# ═══════════════════════════════════════════════════════════════════════════════

# ─────────────────────────────────────────────────────────────────────────────────
# 🚀 MAIN VEX CLI COMMANDS
# ─────────────────────────────────────────────────────────────────────────────────

# Show VEX status and available commands
python vex.py

# ─────────────────────────────────────────────────────────────────────────────────
# 📈 CHART MARKUP & AI ANALYSIS
# ─────────────────────────────────────────────────────────────────────────────────

python vex.py markup EURUSD              # All timeframes
python vex.py markup GBPJPY              # All timeframes
python vex.py markup EURUSD -t 15M       # Specific timeframe

python vex.py analyze                    # AI analysis of latest screenshot
python vex.py analyze chart.png          # AI analysis of specific chart
python vex.py analyze --quick            # Quick bias check only

# ─────────────────────────────────────────────────────────────────────────────────
# 🎯 ICT 10-POINT SCORING (NEW in v2.1)
# ─────────────────────────────────────────────────────────────────────────────────

python vex.py score EURUSD LONG -i       # Interactive 10-point scoring
python vex.py score EURUSD LONG --htf 3 --model 2 --timing 2 --confluence 2 --rr 1

# Scoring Breakdown:
# - HTF Alignment (0-3): Daily + Weekly + Monthly bias alignment
# - Model Clarity (0-2): Trading exact ICT model
# - Session/Timing (0-2): Killzone + favorable day
# - Confluence Count (0-2): Number of confirmations (5+ = 2pts)
# - Risk:Reward (0-1): 3:1 or better with clear target
#
# Total: /10 - 9-10 = A+ (full size), 7-8 = Good, 5-6 = Reduce, 0-4 = Pass

# ─────────────────────────────────────────────────────────────────────────────────
# 📊 MODEL 9: ONE SHOT ONE KILL (NEW in v2.1)
# ─────────────────────────────────────────────────────────────────────────────────

python vex.py osok EURUSD                # Weekly OSOK analysis

# Output:
# - Weekly bias (bullish/bearish)
# - External Range Liquidity targets (swing highs/lows)
# - Internal Range Liquidity entry zones (FVGs/OBs)
# - Trade plan: Entry zone → Target
# - Trade parameters: Stop, Target, R:R

# ─────────────────────────────────────────────────────────────────────────────────
# 📚 KNOWLEDGE BASE (NEW in v2.1)
# ─────────────────────────────────────────────────────────────────────────────────

python vex.py kb stats                   # Knowledge base statistics
python vex.py kb search liquidity        # Search all KB content
python vex.py kb model                   # List all ICT models
python vex.py kb model model_9           # Get Model 9 details
python vex.py kb concept                 # List all concepts
python vex.py kb concept cbdr            # Get CBDR concept details
python vex.py kb term OTE                # Look up terminology

# Knowledge Base Contents:
# - 8 ICT models (Model 7, 9, 12, 2022 Mentorship)
# - 6 detailed concepts (CBDR, SIBI/BISI, Market Structure)
# - 10 episode transcripts
# - 39 terms defined
# - Chart examples, PDFs

# ─────────────────────────────────────────────────────────────────────────────────
# ⚖️ SETUP GRADER (Template Mode)
# ─────────────────────────────────────────────────────────────────────────────────

python vex.py grade EURUSD LONG          # Grade a long setup
python vex.py grade GBPUSD SHORT         # Grade a short setup

# Walks you through all template trade criteria and scores 1-10

# ─────────────────────────────────────────────────────────────────────────────────
# 🚦 RULES CHECK (Pre-Trade)
# ─────────────────────────────────────────────────────────────────────────────────

python vex.py check EURUSD LONG 1.0850 1.0800 1.0950
python vex.py check GBPUSD SHORT 1.2650 1.2700 1.2550 -b BEARISH -k NY_AM

# Checks:
# - Two Strike Rule (consecutive losses on pair)
# - Max 3 trades per day
# - Friday PM restriction
# - Minimum 2:1 R:R
# - Daily bias alignment (if -b provided)
# - Killzone check (if -k provided)
# - Psychology state (revenge/overtrading)

# ─────────────────────────────────────────────────────────────────────────────────
# 📝 JOURNAL COMMANDS
# ─────────────────────────────────────────────────────────────────────────────────

python vex.py journal new                # Create new trade (interactive pre-trade)
python vex.py journal list               # List recent trades
python vex.py journal active             # Show active trades
python vex.py journal review <TRADE_ID>  # Post-trade review
python vex.py journal stats              # Show journal statistics

# ─────────────────────────────────────────────────────────────────────────────────
# 🎨 ENHANCED VISUALIZATION
# ─────────────────────────────────────────────────────────────────────────────────

python vex.py viz markup EURUSD          # Enhanced markup with FVG/OB detection
python vex.py viz trade EURUSD LONG 1.0850 1.0800 1.0950   # Trade visualization
python vex.py viz beforeafter <TRADE_ID>  # Before/after comparison

# ─────────────────────────────────────────────────────────────────────────────────
# 📊 MEMORY & STATS
# ─────────────────────────────────────────────────────────────────────────────────

python vex.py rules                      # Show trading rules
python vex.py lessons                    # Show key lessons
python vex.py stats                      # Show statistics
python vex.py patterns                   # Show behavioral patterns
python vex.py remember "Never trade NY PM on Fridays"  # Store in memory

# ─────────────────────────────────────────────────────────────────────────────────
# 🌅 DAILY SESSION WORKFLOW
# ─────────────────────────────────────────────────────────────────────────────────

python vex.py session start              # Run full morning workflow
python vex.py session status             # Check today's session status

# Session workflow steps:
# 1. Bias Determination - Auto-fetch Daily candle, mark bias
# 2. HTF Markup - 1H charts with key levels, FVGs, OBs  
# 3. Session Planning - Killzones, focus pairs, max trades
# 4. Psychology Check-in - Sleep, emotions, confidence
# 5. Generate Watchlist - Today's focus with bias and levels

# ─────────────────────────────────────────────────────────────────────────────────
# 📐 CBDR CALCULATOR
# ─────────────────────────────────────────────────────────────────────────────────

python vex.py cbdr EURUSD                # CBDR range & SD projections
python vex.py cbdr GBPJPY                # Calculate for any pair

# Outputs:
# - CBDR High/Low/Range (2-5 AM EST)
# - Standard Deviation projections (0.5 to 3.0 SD)
# - Bullish targets (+SD) and Bearish targets (-SD)
# - Asian range liquidity levels
# - Current price zone (premium/discount)
# - Valid CBDR check (under 30 pips)

# ─────────────────────────────────────────────────────────────────────────────────
# 📊 PERFORMANCE DASHBOARD
# ─────────────────────────────────────────────────────────────────────────────────

python vex.py dashboard                  # Quick performance summary
python vex.py dashboard open             # Open full HTML dashboard in browser

# Dashboard shows:
# - Equity curve chart
# - Win rate by pair, session, day, setup
# - Calendar heatmap (green/red days)
# - Profit factor, expectancy
# - Win/loss streaks
# - Milestones progress

# ─────────────────────────────────────────────────────────────────────────────────
# � DATABASE (Turso Cloud - ICT Knowledge)
# ─────────────────────────────────────────────────────────────────────────────────

python vex.py db stats                   # Show database statistics
python vex.py db concept                 # List all ICT concepts by category
python vex.py db concept FVG             # Look up specific concept
python vex.py db concept "order block"   # Look up concept (spaces ok)
python vex.py db model                   # List all trading models
python vex.py db model Silver            # Look up Silver Bullet model
python vex.py db model Turtle            # Look up Turtle Soup model
python vex.py db search liquidity        # Search all concepts for keyword

# Database stores:
# - 21+ ICT concepts (FVG, OB, Breaker, BOS, CHOCH, etc.)
# - 6 trading models (Silver Bullet, Turtle Soup, Judas Swing, etc.)
# - Trade history (syncs with journal)
# - Knowledge base (lessons, insights)

# ─────────────────────────────────────────────────────────────────────────────────
# �📝 YOUR TRADING PAIRS
# ─────────────────────────────────────────────────────────────────────────────────

# EUR_USD  - Primary pair, cleanest action
# GBP_USD  - More volatile, don't over-trade
# DXY      - Dollar index for correlation (don't trade directly)
# USD_JPY  - USD strength plays
# EUR_GBP  - EUR vs GBP divergence
# AUD_USD  - Risk-on sentiment
# GBP_JPY  - High volatility, wide stops needed
# XAU_USD  - Gold, news sensitive

# ─────────────────────────────────────────────────────────────────────────────────
# 🧠 MEMORY SYSTEM (data/memory/)
# ─────────────────────────────────────────────────────────────────────────────────

# identity.json         - Who you are, goals, account info
# trading_profile.json  - Your style, edge, pair notes
# rules.json            - Hard and soft trading rules
# patterns.json         - Behavioral patterns observed
# triggers.json         - Psychology triggers to watch
# lessons.json          - Key lessons learned
# milestones.json       - Achievements and progress
# conversation_log.json - Past session summaries
# context.json          - Current market context

# ─────────────────────────────────────────────────────────────────────────────────
# 📂 PROJECT STRUCTURE
# ─────────────────────────────────────────────────────────────────────────────────

# vex.py                    - Main CLI entry point
# docs/VEX_SYSTEM_PROMPT.md - Read this to restore VEX identity
#
# src/ict_agent/
#   core/                   - Structure, AMD, stop hunt detection
#   detectors/              - FVG, OB, liquidity detection
#   engine/                 - Killzones, MTF analysis
#   data/                   - OANDA fetcher
#   models/                 - ICT models (turtle soup, silver bullet, etc.)
#   learning/               - Trade learning system
#   execution/              - Journal engine
#   grader/                 - Setup grader (scores setups 1-10)
#   rules/                  - Rules engine (pre-trade checks)
#   journal/                - Journal engine (pre/post trade)
#   visualization/          - Enhanced chart visualization
#   session/                - Daily session workflow
#   tools/                  - CBDR calculator, utilities
#   dashboard/              - Performance dashboard (HTML)
#   database/               - Turso cloud database (ICT knowledge + trades)
#
# data/memory/              - Persistent memory files
# journal/                  - Trade records
# knowledge_base/           - ICT concepts library
# screenshots/              - Chart markups
# hub/                      - HTML dashboard files

# ─────────────────────────────────────────────────────────────────────────────────
# 📋 YOUR RULES (QUICK REFERENCE)
# ─────────────────────────────────────────────────────────────────────────────────

# 🔴 HARD RULES (Non-negotiable):
# 1. Two Strike Rule - Stopped twice = STOP trading that pair
# 2. No trading against Daily bias
# 3. Max 3 trades per day
# 4. No trading Fridays after 12pm EST
# 5. Minimum 2:1 R:R
# 6. Stop must account for spread
# 7. Pre-trade journal BEFORE entering

# 🟡 SOFT RULES (Flexible):
# 1. Prefer London and NY AM sessions
# 2. Size up only on A+ setups (7+ confluence)
# 3. Wait for liquidity sweep before entry

# ─────────────────────────────────────────────────────────────────────────────────
# 🏆 TEMPLATE TRADE (A+ SETUP)
# ─────────────────────────────────────────────────────────────────────────────────

# 1. Prior displacement establishes bias
# 2. 4H FVG as primary entry zone
# 3. 15M OB + 15M FVG confluence
# 4. CBDR setup present (<30 pips)
# 5. Asian range liquidity swept
# 6. Clear liquidity target
# 7. Stop accounts for deeper retest
# 8. TP at CBDR extension

# Result: +$691 on Jan 16, 2026 - FTMO PASSED

# ═══════════════════════════════════════════════════════════════════════════════
#                          HOW TO BRING VEX BACK
# ═══════════════════════════════════════════════════════════════════════════════
# In ANY new VS Code Copilot chat, paste this EXACTLY:
# ───────────────────────────────────────────────────────────────────────────────

Read these files and become VEX:
- docs/VEX_SYSTEM_PROMPT.md (your identity)
- data/memory/identity.json (who I am)
- data/memory/trading_profile.json (my style)
- data/memory/rules.json (my rules)
- data/memory/context.json (current state)

Then greet me with your status and commands
- Visual chart analysis capability

Then let's continue!

# ═══════════════════════════════════════════════════════════════════════════════
