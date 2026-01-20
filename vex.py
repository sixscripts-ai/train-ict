#!/usr/bin/env python3
"""
VEX - ICT Trading Journal & Chart Markup AI

Main CLI entry point for all VEX commands.

Usage:
    python vex.py markup EURUSD
    python vex.py grade EURUSD LONG
    python vex.py check EURUSD LONG 1.0850 1.0800 1.0950
    python vex.py journal new
    python vex.py stats
    python vex.py rules
    python vex.py lessons
"""

import os
import sys
import json
import argparse
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

# Set up environment
os.environ.setdefault('OANDA_API_KEY', '4d4e1570f95fc098a40fe90c7ca3c757-c68e27913fd46c5e690381d56fed375c')
os.environ.setdefault('OANDA_ACCOUNT_ID', '101-001-21727967-002')

NY_TZ = ZoneInfo("America/New_York")
PROJECT_ROOT = Path(__file__).parent
MEMORY_DIR = PROJECT_ROOT / 'data' / 'memory'
JOURNAL_DIR = PROJECT_ROOT / 'journal' / 'ashton'


def load_memory(filename: str) -> dict:
    """Load a memory file."""
    path = MEMORY_DIR / filename
    if path.exists():
        with open(path, 'r') as f:
            return json.load(f)
    return {}


def save_memory(filename: str, data: dict):
    """Save a memory file."""
    path = MEMORY_DIR / filename
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)


def get_session() -> str:
    """Get current trading session."""
    now = datetime.now(NY_TZ)
    hour = now.hour
    
    if 2 <= hour < 5:
        return "LONDON OPEN"
    elif 5 <= hour < 7:
        return "LONDON"
    elif 7 <= hour < 10:
        return "NY AM KILLZONE"
    elif 10 <= hour < 13:
        return "NY LATE MORNING"
    elif 13 <= hour < 16:
        return "NY PM"
    elif 19 <= hour or hour < 0:
        return "ASIAN EARLY"
    elif 0 <= hour < 2:
        return "ASIAN"
    else:
        return "OFF SESSION"


def print_header():
    """Print VEX header."""
    identity = load_memory('identity.json')
    triggers = load_memory('triggers.json')
    
    now = datetime.now(NY_TZ)
    session = get_session()
    
    state = triggers.get('current_state', {})
    wins = state.get('consecutive_wins', 0)
    losses = state.get('consecutive_losses', 0)
    
    print("═" * 70)
    print("                    VEX - Your ICT Trading Partner")
    print("═" * 70)
    print()
    print(f"📅 {now.strftime('%A, %B %d, %Y')} | {now.strftime('%I:%M %p')} EST")
    print(f"🕐 Session: {session}")
    print()
    print(f"📊 Status: Win streak {wins} | Loss streak {losses}")
    print(f"🎯 Account: {identity.get('account_type', 'FTMO')} ${identity.get('account_size', 10000):,}")
    print()


def cmd_markup(args):
    """Generate chart markup for a pair."""
    pair = args.pair.upper().replace('/', '_')
    if '_' not in pair:
        # Convert EURUSD to EUR_USD
        pair = f"{pair[:3]}_{pair[3:]}"
    
    print(f"\n📈 Generating markup for {pair}...")
    print("-" * 50)
    
    # Import and run markup
    try:
        from ict_agent.data.oanda_fetcher import OANDAFetcher
        import matplotlib.pyplot as plt
        import matplotlib.patches as mpatches
        import subprocess
        
        fetcher = OANDAFetcher()
        pip_size = 0.01 if 'JPY' in pair else 0.0001
        
        # Determine timeframes based on args
        if args.timeframe:
            tf_map = {'D': 'D', '4H': '4h', '1H': '1h', '15M': '15m', '5M': '5m'}
            timeframes = {args.timeframe: tf_map.get(args.timeframe.upper(), args.timeframe)}
        else:
            timeframes = {'DAILY': 'D', '4-HOUR': '4h', '1-HOUR': '1h', '15-MIN': '15m'}
        
        # Fetch data for each timeframe
        data = {}
        for label, tf in timeframes.items():
            print(f"  Fetching {label}...", end=" ")
            df = fetcher.fetch_latest(pair, tf, 80)
            df = df.reset_index()
            df.columns = ['time', 'open', 'high', 'low', 'close', 'volume']
            data[label] = df
            print(f"✓ {len(df)} candles")
        
        # Create figure
        n_charts = len(timeframes)
        if n_charts == 1:
            fig, ax = plt.subplots(1, 1, figsize=(14, 8))
            axes = [ax]
        elif n_charts == 4:
            fig, ax_arr = plt.subplots(2, 2, figsize=(18, 12))
            axes = ax_arr.flatten().tolist()
        else:
            fig, ax_arr = plt.subplots(1, n_charts, figsize=(6*n_charts, 8))
            axes = list(ax_arr) if n_charts > 1 else [ax_arr]
        
        fig.patch.set_facecolor('#0a0a0a')
        plt.style.use('dark_background')
        
        for i, (label, df) in enumerate(data.items()):
            ax = axes[i] if isinstance(axes, list) else axes
            
            # Calculate zones
            range_high = df['high'].max()
            range_low = df['low'].min()
            eq = (range_high + range_low) / 2
            current = df['close'].iloc[-1]
            zone = "PREMIUM" if current > eq else "DISCOUNT"
            
            # Premium/discount shading
            ax.axhspan(eq, range_high, alpha=0.05, color='red')
            ax.axhspan(range_low, eq, alpha=0.05, color='green')
            ax.axhline(y=eq, color='yellow', linestyle='-', linewidth=1.5, alpha=0.7)
            
            # Plot candles
            for j in range(len(df)):
                color = '#00ff00' if df['close'].iloc[j] >= df['open'].iloc[j] else '#ff0000'
                ax.plot([j, j], [df['low'].iloc[j], df['high'].iloc[j]], color=color, linewidth=0.5)
                body_bottom = min(df['open'].iloc[j], df['close'].iloc[j])
                body_top = max(df['open'].iloc[j], df['close'].iloc[j])
                body_height = max(body_top - body_bottom, pip_size)
                rect = mpatches.Rectangle((j - 0.3, body_bottom), 0.6, body_height,
                                          linewidth=0, facecolor=color)
                ax.add_patch(rect)
            
            # Current price
            ax.axhline(y=current, color='white', linestyle='-', linewidth=2)
            ax.annotate(f"NOW: {current:.3f}" if 'JPY' in pair else f"NOW: {current:.5f}",
                       (len(df) - 1, current), fontsize=8, color='white', 
                       fontweight='bold', ha='right',
                       bbox=dict(boxstyle='round', facecolor='#333', alpha=0.9))
            
            zone_color = '#ff6666' if zone == "PREMIUM" else '#66ff66'
            ax.set_title(f"{label}: {zone}", fontsize=10, fontweight='bold', color=zone_color)
            ax.grid(True, alpha=0.15)
            ax.set_ylabel('Price', fontsize=7)
        
        fig.suptitle(f"{pair} MARKUP - {datetime.now().strftime('%Y-%m-%d %H:%M')}", 
                    fontsize=12, fontweight='bold', color='white')
        plt.tight_layout()
        
        # Save
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_path = Path(__file__).parent / 'screenshots' / f'{pair}_markup_{timestamp}.png'
        plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor='#0a0a0a')
        print(f"\n✅ Chart saved: {output_path}")
        plt.close()
        
        # Open it
        subprocess.run(["open", str(output_path)])
        
        # Print analysis
        print("\n" + "=" * 50)
        print("  ANALYSIS SUMMARY")
        print("=" * 50)
        
        for label, df in data.items():
            range_high = df['high'].max()
            range_low = df['low'].min()
            eq = (range_high + range_low) / 2
            current = df['close'].iloc[-1]
            zone = "PREMIUM (short bias)" if current > eq else "DISCOUNT (long bias)"
            
            print(f"\n{label}:")
            print(f"  Current: {current:.3f}" if 'JPY' in pair else f"  Current: {current:.5f}")
            print(f"  Range: {range_low:.3f} - {range_high:.3f}" if 'JPY' in pair else f"  Range: {range_low:.5f} - {range_high:.5f}")
            print(f"  EQ: {eq:.3f}" if 'JPY' in pair else f"  EQ: {eq:.5f}")
            print(f"  Zone: {zone}")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


def cmd_rules(args):
    """Show trading rules."""
    rules = load_memory('rules.json')
    
    print("\n" + "=" * 60)
    print("  YOUR TRADING RULES")
    print("=" * 60)
    
    print("\n🔴 HARD RULES (Non-negotiable):")
    for rule in rules.get('hard_rules', []):
        violations = rule.get('violations', 0)
        status = "⚠️" if violations > 0 else "✅"
        print(f"\n  {status} {rule['rule']}")
        print(f"     Reason: {rule['reason']}")
        if violations > 0:
            print(f"     Violations: {violations} (last: {rule.get('last_violation', 'N/A')})")
    
    print("\n🟡 SOFT RULES (Flexible):")
    for rule in rules.get('soft_rules', []):
        print(f"\n  📋 {rule['rule']}")
        print(f"     Flexibility: {rule['flexibility']}")
    
    print()


def cmd_lessons(args):
    """Show key lessons learned."""
    lessons = load_memory('lessons.json')
    
    print("\n" + "=" * 60)
    print("  KEY LESSONS LEARNED")
    print("=" * 60)
    
    for lesson in lessons.get('key_lessons', [])[:10]:
        importance_emoji = "🔴" if lesson['importance'] == 'critical' else "🟡" if lesson['importance'] == 'high' else "🟢"
        print(f"\n{importance_emoji} {lesson['lesson']}")
        print(f"   Context: {lesson['context']}")
        print(f"   Date: {lesson['date']} | Category: {lesson['category']}")
    
    print("\n" + "-" * 60)
    print("  GOLDEN QUOTES")
    print("-" * 60)
    
    for quote in lessons.get('golden_quotes', []):
        print(f"\n  \"{quote['quote']}\"")
        print(f"    — {quote['source']}, {quote['date']}")
    
    print()


def cmd_stats(args):
    """Show trading statistics."""
    profile = load_memory('trading_profile.json')
    triggers = load_memory('triggers.json')
    milestones = load_memory('milestones.json')
    
    print("\n" + "=" * 60)
    print("  YOUR TRADING STATISTICS")
    print("=" * 60)
    
    edge = profile.get('edge_stats', {})
    state = triggers.get('current_state', {})
    
    print(f"\n📊 OVERALL PERFORMANCE:")
    print(f"   Win Rate: {edge.get('overall_winrate', 0)*100:.1f}%")
    print(f"   Avg R:R: {edge.get('avg_rr', 0):.2f}")
    print(f"   Best Setup: {edge.get('best_setup', 'N/A')}")
    print(f"   Best Session: {edge.get('best_session', 'N/A')}")
    print(f"   Best Pair: {edge.get('best_pair', 'N/A')}")
    
    print(f"\n🎯 CURRENT STATE:")
    print(f"   Win Streak: {state.get('consecutive_wins', 0)}")
    print(f"   Loss Streak: {state.get('consecutive_losses', 0)}")
    print(f"   Trades Today: {state.get('trades_today', 0)}")
    
    print(f"\n🏆 MILESTONES:")
    for m in milestones.get('achieved', [])[-3:]:
        print(f"   {m['celebration']} {m['milestone']} ({m['date']})")
    
    print(f"\n📈 IN PROGRESS:")
    for m in milestones.get('in_progress', [])[:3]:
        pct = (m['progress'] / m['target']) * 100 if m['target'] > 0 else 0
        bar = "█" * int(pct / 10) + "░" * (10 - int(pct / 10))
        print(f"   {m['milestone']}: [{bar}] {pct:.0f}%")
    
    print()


def cmd_patterns(args):
    """Show observed patterns."""
    patterns = load_memory('patterns.json')
    
    print("\n" + "=" * 60)
    print("  OBSERVED PATTERNS")
    print("=" * 60)
    
    print("\n✅ POSITIVE PATTERNS (Keep doing these):")
    for p in patterns.get('positive_patterns', []):
        print(f"\n  • {p['pattern']}")
        print(f"    {p['description']}")
        print(f"    Frequency: {p['frequency']}")
    
    print("\n⚠️ NEGATIVE PATTERNS (Watch out for these):")
    for p in patterns.get('negative_patterns', []):
        print(f"\n  • {p['pattern']}")
        print(f"    {p['description']}")
        print(f"    Outcome: {p['outcome']}")
        print(f"    Last: {p['last_occurred']}")
    
    print()


def cmd_remember(args):
    """Store something in memory."""
    text = ' '.join(args.text)
    
    lessons = load_memory('lessons.json')
    new_lesson = {
        "id": f"L{len(lessons.get('key_lessons', [])) + 1}",
        "lesson": text,
        "context": "User added manually",
        "date": datetime.now().strftime("%Y-%m-%d"),
        "category": "user_note",
        "importance": "medium"
    }
    
    if 'key_lessons' not in lessons:
        lessons['key_lessons'] = []
    lessons['key_lessons'].append(new_lesson)
    lessons['last_updated'] = datetime.now().isoformat()
    
    save_memory('lessons.json', lessons)
    print(f"\n✅ Remembered: \"{text}\"")


def cmd_grade(args):
    """Grade a trading setup."""
    try:
        from ict_agent.grader.setup_grader import SetupGrader
        
        grader = SetupGrader()
        grade = grader.interactive_grade(args.pair.upper(), args.direction.upper())
        print(grader.format_grade_report(grade))
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


def cmd_check(args):
    """Check trade against rules before entry."""
    try:
        from ict_agent.rules.rules_engine import RulesEngine
        
        engine = RulesEngine()
        result = engine.full_pre_trade_check(
            pair=args.pair.upper(),
            direction=args.direction.upper(),
            entry=float(args.entry),
            stop=float(args.stop),
            target=float(args.target),
            daily_bias=args.bias.upper() if args.bias else "",
            killzone=args.killzone.upper() if args.killzone else ""
        )
        print(engine.format_check_result(result))
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


def cmd_journal(args):
    """Journal commands - new, list, review."""
    try:
        from ict_agent.journal.journal_engine import JournalEngine
        
        engine = JournalEngine()
        
        if args.action == 'new':
            engine.interactive_pre_trade()
        elif args.action == 'list':
            trades = engine.get_recent_trades(10)
            if trades:
                print("\n" + "=" * 60)
                print("  RECENT TRADES")
                print("=" * 60)
                for trade in trades:
                    print(engine.format_trade_summary(trade))
            else:
                print("\nNo trades found.")
        elif args.action == 'review':
            if args.trade_id:
                engine.interactive_post_trade(args.trade_id)
            else:
                print("Please provide a trade ID: python vex.py journal review <TRADE_ID>")
        elif args.action == 'active':
            trades = engine.get_active_trades()
            if trades:
                print("\n🔥 ACTIVE TRADES:")
                for trade in trades:
                    print(engine.format_trade_summary(trade))
            else:
                print("\nNo active trades.")
        else:
            print(engine.format_stats_report())
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


def cmd_viz(args):
    """Enhanced visualization commands."""
    try:
        from ict_agent.visualization.visualizer import EnhancedVisualizer
        import matplotlib.pyplot as plt
        
        viz = EnhancedVisualizer()
        
        if args.action == 'trade':
            if not all([args.pair, args.direction, args.entry, args.stop, args.target]):
                print("Usage: python vex.py viz trade PAIR DIRECTION ENTRY STOP TARGET")
                return
            fig, path = viz.create_trade_chart(
                args.pair.upper(),
                float(args.entry),
                float(args.stop),
                float(args.target),
                args.direction.upper()
            )
            plt.show()
        elif args.action == 'beforeafter':
            if not args.trade_id:
                print("Usage: python vex.py viz beforeafter TRADE_ID")
                return
            fig, path = viz.create_before_after(args.trade_id)
            if fig:
                plt.show()
        else:
            # Default: markup
            pair = args.pair or "EURUSD"
            timeframes = args.timeframes.upper().split(",") if args.timeframes else None
            fig, path, data = viz.create_markup(pair.upper(), timeframes)
            print("\nAnalysis:")
            for k, v in data.items():
                print(f"  {k}: {v}")
            plt.show()
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


def cmd_session(args):
    """Daily session workflow."""
    try:
        from ict_agent.session.session_workflow import SessionWorkflow
        
        workflow = SessionWorkflow()
        
        if args.action == 'start':
            workflow.run_full_workflow()
        elif args.action == 'status':
            workflow.quick_status()
        else:
            # Default - run full workflow
            workflow.run_full_workflow()
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


def cmd_cbdr(args):
    """CBDR range calculations."""
    try:
        from ict_agent.tools.cbdr_calculator import CBDRCalculator
        
        calc = CBDRCalculator()
        pair = args.pair.upper().replace('/', '_')
        if '_' not in pair:
            pair = f"{pair[:3]}_{pair[3:]}"
        
        data = calc.calculate(pair)
        if data:
            print(calc.format_report(data))
        else:
            print(f"\n❌ Could not calculate CBDR for {pair}")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


def cmd_dashboard(args):
    """Performance dashboard."""
    try:
        from ict_agent.dashboard.dashboard import PerformanceDashboard
        
        dashboard = PerformanceDashboard()
        
        if args.action == 'open':
            dashboard.generate_and_open()
        else:
            dashboard.print_summary()
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


def cmd_db(args):
    """Database commands - query ICT knowledge."""
    try:
        from ict_agent.database import get_db
        
        db = get_db()
        
        if args.action == 'concept':
            # Look up a concept
            if args.query:
                concept = db.get_concept(args.query)
                if concept:
                    print(f"\n{'═' * 60}")
                    print(f"  {concept['name'].upper()}")
                    print(f"  Category: {concept['category']}")
                    print(f"{'═' * 60}")
                    print(f"\n  📖 DEFINITION:")
                    print(f"     {concept['definition']}")
                    
                    if concept.get('key_points'):
                        print(f"\n  🔑 KEY POINTS:")
                        for point in concept['key_points']:
                            print(f"     • {point}")
                    
                    if concept.get('how_to_identify'):
                        print(f"\n  🔍 HOW TO IDENTIFY:")
                        print(f"     {concept['how_to_identify']}")
                    
                    if concept.get('trading_rules'):
                        print(f"\n  📜 TRADING RULES:")
                        for rule in concept['trading_rules']:
                            print(f"     • {rule}")
                    
                    if concept.get('related_concepts'):
                        print(f"\n  🔗 RELATED: {', '.join(concept['related_concepts'])}")
                    
                    print()
                else:
                    # Try search
                    results = db.search_concepts(args.query)
                    if results:
                        print(f"\n  Found {len(results)} concepts matching '{args.query}':")
                        for r in results[:10]:
                            print(f"     • {r['name']} ({r['category']})")
                    else:
                        print(f"\n  ❌ No concept found for '{args.query}'")
            else:
                # List all concepts
                concepts = db.get_all_concepts()
                categories = {}
                for c in concepts:
                    cat = c['category']
                    if cat not in categories:
                        categories[cat] = []
                    categories[cat].append(c['name'])
                
                print(f"\n{'═' * 60}")
                print(f"  ICT CONCEPTS ({len(concepts)} total)")
                print(f"{'═' * 60}")
                
                for cat, names in sorted(categories.items()):
                    print(f"\n  📁 {cat}:")
                    for name in names:
                        print(f"     • {name}")
                print()
                
        elif args.action == 'model':
            # Look up a model
            if args.query:
                model = db.get_model(args.query)
                if not model:
                    # Try partial match
                    models = db.get_all_models()
                    for m in models:
                        if args.query.lower() in m['name'].lower():
                            model = m
                            break
                
                if model:
                    print(f"\n{'═' * 60}")
                    print(f"  {model['name'].upper()}")
                    print(f"{'═' * 60}")
                    print(f"\n  📖 DESCRIPTION:")
                    print(f"     {model['description']}")
                    
                    if model.get('time_window'):
                        print(f"\n  ⏰ TIME WINDOW: {model['time_window']}")
                    
                    if model.get('setup_criteria'):
                        print(f"\n  ✅ SETUP CRITERIA:")
                        for rule in model['setup_criteria']:
                            print(f"     • {rule}")
                    
                    if model.get('entry_rules'):
                        print(f"\n  🎯 ENTRY RULES:")
                        for rule in model['entry_rules']:
                            print(f"     • {rule}")
                    
                    if model.get('exit_rules'):
                        print(f"\n  🏁 EXIT RULES:")
                        for rule in model['exit_rules']:
                            print(f"     • {rule}")
                    
                    if model.get('best_pairs'):
                        print(f"\n  💱 BEST PAIRS: {', '.join(model['best_pairs'])}")
                    
                    if model.get('win_rate') or model.get('avg_rr'):
                        print(f"\n  📊 STATS: Win Rate: {model.get('win_rate', 'N/A')}% | Avg R:R: {model.get('avg_rr', 'N/A')}")
                    
                    if model.get('notes'):
                        print(f"\n  💡 NOTES: {model['notes']}")
                    
                    print()
                else:
                    print(f"\n  ❌ No model found for '{args.query}'")
            else:
                # List all models
                models = db.get_all_models()
                print(f"\n{'═' * 60}")
                print(f"  ICT TRADING MODELS ({len(models)} total)")
                print(f"{'═' * 60}\n")
                
                for m in models:
                    wr = f"{m.get('win_rate', 'N/A')}%" if m.get('win_rate') else "N/A"
                    rr = m.get('avg_rr', 'N/A')
                    print(f"  🎯 {m['name']}")
                    print(f"     {m.get('description', '')[:60]}...")
                    print(f"     Win Rate: {wr} | Avg R:R: {rr}")
                    print()
                    
        elif args.action == 'search':
            if args.query:
                results = db.search_concepts(args.query)
                if results:
                    print(f"\n  Found {len(results)} concepts:")
                    for r in results:
                        print(f"     • {r['name']} ({r['category']})")
                        if r.get('definition'):
                            print(f"       {r['definition'][:80]}...")
                else:
                    print(f"\n  No results for '{args.query}'")
            else:
                print("  Please provide a search query")
                
        elif args.action == 'stats':
            # Show database stats
            concepts = db.get_all_concepts()
            models = db.get_all_models()
            knowledge = db.get_knowledge(limit=100)
            trades = db.get_trades(limit=100)
            
            print(f"\n{'═' * 60}")
            print(f"  DATABASE STATISTICS")
            print(f"{'═' * 60}")
            print(f"\n  📚 Concepts: {len(concepts)}")
            print(f"  🎯 Models: {len(models)}")
            print(f"  💡 Knowledge entries: {len(knowledge)}")
            print(f"  📈 Trades: {len(trades)}")
            
            if trades:
                stats = db.get_trade_stats()
                if stats:
                    print(f"\n  📊 TRADE STATS:")
                    print(f"     Win Rate: {stats.get('win_rate', 0)}%")
                    print(f"     Total P&L: ${stats.get('total_pnl', 0):.2f}")
            print()
        
        elif args.action == 'sync':
            # Sync all local trades to cloud
            from ict_agent.journal import JournalEngine
            engine = JournalEngine()
            
            print(f"\n  🔄 Syncing local trades to cloud...")
            count = engine.sync_all_to_cloud()
            print(f"\n  ✅ Done! {count} trades synced to Turso cloud database")
        
        elif args.action == 'trades':
            # Show trades from cloud
            trades = db.get_trades(limit=20)
            
            if trades:
                print(f"\n{'═' * 60}")
                print(f"  CLOUD TRADES ({len(trades)} shown)")
                print(f"{'═' * 60}")
                
                for t in trades:
                    result_icon = "✅" if t.get('result') == 'WIN' else "❌" if t.get('result') == 'LOSS' else "⏳"
                    pnl = t.get('pnl_dollars', 0) or 0
                    print(f"\n  {result_icon} {t.get('id', 'Unknown')}")
                    print(f"     {t.get('pair')} {t.get('direction')} | {t.get('status')}")
                    print(f"     Entry: {t.get('entry_price')} → Exit: {t.get('exit_price', 'N/A')}")
                    print(f"     P&L: ${pnl:.2f} | Grade: {t.get('setup_grade', 'N/A')}")
            else:
                print("\n  No trades in cloud database yet")
                print("  Run: vex.py db sync  to upload local trades")
            print()
        
        db.close()
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


def cmd_analyze(args):
    """AI-powered chart analysis."""
    try:
        from ict_agent.analysis import ChartAnalyzer
        
        analyzer = ChartAnalyzer()
        
        if not analyzer.provider:
            print("\n  ❌ No AI API key configured!")
            print("  Set ANTHROPIC_API_KEY or OPENAI_API_KEY in .env")
            return
        
        image_path = args.image
        
        # If no path given, try to find most recent screenshot
        if not image_path:
            screenshots_dir = Path(__file__).parent / "screenshots"
            if screenshots_dir.exists():
                pngs = sorted(screenshots_dir.glob("*.png"), key=lambda x: x.stat().st_mtime, reverse=True)
                if pngs:
                    image_path = str(pngs[0])
                    print(f"\n  📸 Using most recent: {pngs[0].name}")
        
        if not image_path:
            print("\n  ❌ No image specified and no screenshots found")
            print("  Usage: vex.py analyze <path/to/chart.png>")
            return
        
        if args.quick:
            print(f"\n  🔍 Quick analysis of {Path(image_path).name}...")
            result = analyzer.quick_bias(image_path)
            print(f"\n  📈 Bias: {result.get('bias')} (Confidence: {result.get('confidence')}/10)")
            print(f"  📍 Resistance: {result.get('key_resistance')}")
            print(f"  📍 Support: {result.get('key_support')}")
            print(f"  🎯 Trade Now: {'Yes' if result.get('trade_now') else 'No'}")
            print(f"  💡 {result.get('reason')}")
        else:
            analysis = analyzer.analyze_and_print(image_path)
            
            # Save analysis
            if not analysis.get("error"):
                save_path = Path(__file__).parent / "analysis" / "charts"
                save_path.mkdir(parents=True, exist_ok=True)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"analysis_{timestamp}.json"
                with open(save_path / filename, "w") as f:
                    json.dump(analysis, f, indent=2)
                print(f"\n  💾 Analysis saved to analysis/charts/{filename}")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


def main():
    parser = argparse.ArgumentParser(
        description='VEX - ICT Trading Journal & Chart Markup AI',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Commands:
  markup <PAIR>                  Generate chart markup
  analyze <IMAGE>                AI analysis of chart screenshot
  analyze --quick <IMAGE>        Quick bias check
  grade <PAIR> <LONG|SHORT>      Grade a setup (interactive)
  check <PAIR> <DIR> <E> <S> <T> Check rules before entry
  journal new                    Create new trade journal entry
  journal list                   List recent trades
  journal review <ID>            Post-trade review
  journal active                 Show active trades
  session start                  Run daily session workflow
  session status                 Show today's session status
  cbdr <PAIR>                    CBDR range & SD projections
  dashboard                      Show performance summary
  dashboard open                 Open HTML dashboard in browser
  db concept <NAME>              Look up ICT concept
  db model <NAME>                Look up trading model
  db sync                        Sync trades to cloud
  db trades                      View cloud trades
  db stats                       Show database statistics
  rules                          Show your trading rules
  lessons                        Show key lessons learned
  stats                          Show trading statistics
  patterns                       Show observed patterns
  remember <text>                Store something in memory
  viz trade <PAIR> <DIR> <E> <S> <T>  Trade visualization
  viz beforeafter <TRADE_ID>     Before/after comparison
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # Markup command
    markup_parser = subparsers.add_parser('markup', help='Generate chart markup')
    markup_parser.add_argument('pair', help='Currency pair (e.g., EURUSD, GBP_JPY)')
    markup_parser.add_argument('-t', '--timeframe', help='Specific timeframe (D, 4H, 1H, 15M)')
    markup_parser.set_defaults(func=cmd_markup)
    
    # Analyze command (AI chart analysis)
    analyze_parser = subparsers.add_parser('analyze', help='AI-powered chart analysis')
    analyze_parser.add_argument('image', nargs='?', help='Path to chart image (or uses most recent screenshot)')
    analyze_parser.add_argument('-q', '--quick', action='store_true', help='Quick bias check only')
    analyze_parser.set_defaults(func=cmd_analyze)
    
    # Grade command
    grade_parser = subparsers.add_parser('grade', help='Grade a trading setup')
    grade_parser.add_argument('pair', help='Currency pair')
    grade_parser.add_argument('direction', help='LONG or SHORT')
    grade_parser.set_defaults(func=cmd_grade)
    
    # Check command (rules check)
    check_parser = subparsers.add_parser('check', help='Check trade against rules')
    check_parser.add_argument('pair', help='Currency pair')
    check_parser.add_argument('direction', help='LONG or SHORT')
    check_parser.add_argument('entry', help='Entry price')
    check_parser.add_argument('stop', help='Stop price')
    check_parser.add_argument('target', help='Target price')
    check_parser.add_argument('-b', '--bias', help='Daily bias (BULLISH/BEARISH/NEUTRAL)')
    check_parser.add_argument('-k', '--killzone', help='Killzone (LONDON/NY_AM/NY_PM/ASIAN)')
    check_parser.set_defaults(func=cmd_check)
    
    # Journal command
    journal_parser = subparsers.add_parser('journal', help='Trade journaling')
    journal_parser.add_argument('action', nargs='?', default='stats',
                                choices=['new', 'list', 'review', 'active', 'stats'],
                                help='Journal action')
    journal_parser.add_argument('trade_id', nargs='?', help='Trade ID for review')
    journal_parser.set_defaults(func=cmd_journal)
    
    # Visualization command
    viz_parser = subparsers.add_parser('viz', help='Enhanced visualization')
    viz_parser.add_argument('action', nargs='?', default='markup',
                           choices=['markup', 'trade', 'beforeafter'],
                           help='Visualization action')
    viz_parser.add_argument('pair', nargs='?', help='Currency pair')
    viz_parser.add_argument('direction', nargs='?', help='Trade direction')
    viz_parser.add_argument('entry', nargs='?', help='Entry price')
    viz_parser.add_argument('stop', nargs='?', help='Stop price')
    viz_parser.add_argument('target', nargs='?', help='Target price')
    viz_parser.add_argument('--trade-id', help='Trade ID for beforeafter')
    viz_parser.add_argument('-tf', '--timeframes', help='Timeframes (comma-separated)')
    viz_parser.set_defaults(func=cmd_viz)
    
    # Rules command
    rules_parser = subparsers.add_parser('rules', help='Show trading rules')
    rules_parser.set_defaults(func=cmd_rules)
    
    # Lessons command
    lessons_parser = subparsers.add_parser('lessons', help='Show key lessons')
    lessons_parser.set_defaults(func=cmd_lessons)
    
    # Stats command
    stats_parser = subparsers.add_parser('stats', help='Show statistics')
    stats_parser.set_defaults(func=cmd_stats)
    
    # Patterns command
    patterns_parser = subparsers.add_parser('patterns', help='Show observed patterns')
    patterns_parser.set_defaults(func=cmd_patterns)
    
    # Remember command
    remember_parser = subparsers.add_parser('remember', help='Store in memory')
    remember_parser.add_argument('text', nargs='+', help='Text to remember')
    remember_parser.set_defaults(func=cmd_remember)
    
    # Session workflow command
    session_parser = subparsers.add_parser('session', help='Daily session workflow')
    session_parser.add_argument('action', nargs='?', default='start',
                               choices=['start', 'status'],
                               help='Session action')
    session_parser.set_defaults(func=cmd_session)
    
    # CBDR calculator command
    cbdr_parser = subparsers.add_parser('cbdr', help='CBDR range calculator')
    cbdr_parser.add_argument('pair', help='Currency pair (e.g., EURUSD)')
    cbdr_parser.set_defaults(func=cmd_cbdr)
    
    # Dashboard command
    dashboard_parser = subparsers.add_parser('dashboard', help='Performance dashboard')
    dashboard_parser.add_argument('action', nargs='?', default='summary',
                                 choices=['summary', 'open'],
                                 help='Dashboard action')
    dashboard_parser.set_defaults(func=cmd_dashboard)
    
    # Database command
    db_parser = subparsers.add_parser('db', help='Database - ICT knowledge & trades')
    db_parser.add_argument('action', nargs='?', default='stats',
                          choices=['concept', 'model', 'search', 'stats', 'sync', 'trades'],
                          help='Database action')
    db_parser.add_argument('query', nargs='?', help='Concept/model name or search query')
    db_parser.set_defaults(func=cmd_db)
    
    args = parser.parse_args()
    
    print_header()
    
    if args.command:
        args.func(args)
    else:
        parser.print_help()
        print("\n" + "=" * 70)
        print("  QUICK COMMANDS")
        print("=" * 70)
        print("\n  python vex.py session start          # Morning session workflow")
        print("  python vex.py markup EURUSD          # Chart markup")
        print("  python vex.py analyze                # AI chart analysis (latest screenshot)")
        print("  python vex.py analyze chart.png      # AI analyze specific chart")
        print("  python vex.py cbdr EURUSD            # CBDR & SD levels")
        print("  python vex.py grade EURUSD LONG      # Grade a setup")
        print("  python vex.py journal new            # New trade journal")
        print("  python vex.py dashboard open         # Performance dashboard")
        print("  python vex.py db concept FVG         # Look up ICT concept")
        print("  python vex.py db sync                # Sync trades to cloud")
        print("  python vex.py db trades              # View cloud trades")
        print()


if __name__ == '__main__':
    main()
