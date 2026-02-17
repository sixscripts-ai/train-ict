#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════╗
║                    VEX — RUN AGENT                          ║
║                                                              ║
║  Unified entry point for the autonomous ICT trading agent.   ║
║  Boots: Controller → Skills → Events → OANDA → Learn → Go   ║
║                                                              ║
║  Usage:                                                      ║
║    python run_vex.py                    # Live trading        ║
║    python run_vex.py --dry-run          # Simulate only       ║
║    python run_vex.py --dry-run --cycles 3   # 3 cycles test  ║
║    python run_vex.py --duration 60      # Run for 60 min      ║
║                                                              ║
║  Authors: VS Code Copilot + Antigravity                      ║
║  Created: 2026-02-15                                         ║
╚══════════════════════════════════════════════════════════════╝
"""

import sys
import os
import argparse
from pathlib import Path

# Ensure the project root is on the path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))


def main():
    parser = argparse.ArgumentParser(
        description="VEX — Autonomous ICT Trading Agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_vex.py                         Live trading (continuous)
  python run_vex.py --dry-run               Dry run (no real trades)
  python run_vex.py --dry-run --cycles 3    Run 3 analysis cycles
  python run_vex.py --dry-run --dashboard   Dry run with live TUI
  python run_vex.py --duration 120          Trade for 2 hours
  python run_vex.py --status                Show agent status and exit
  python run_vex.py --symbols EUR_USD GBP_USD   Trade specific pairs
        """,
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate trades without placing real orders",
    )
    parser.add_argument(
        "--duration", type=int, default=None, help="Run for N minutes then stop"
    )
    parser.add_argument(
        "--cycles", type=int, default=None, help="Run N scan cycles then stop"
    )
    parser.add_argument(
        "--symbols",
        nargs="+",
        default=None,
        help="Symbols to trade (e.g. EUR_USD GBP_USD)",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=300,
        help="Seconds between scan cycles (default 300)",
    )
    parser.add_argument(
        "--status", action="store_true", help="Boot agent, print status, and exit"
    )
    parser.add_argument("--no-news", action="store_true", help="Disable news filter")
    parser.add_argument(
        "--no-learn", action="store_true", help="Disable learning system"
    )
    parser.add_argument("--quiet", action="store_true", help="Minimal output")
    parser.add_argument(
        "--max-trades", type=int, default=8, help="Max trades per day (default 8)"
    )
    parser.add_argument(
        "--dashboard",
        action="store_true",
        help="Enable live terminal dashboard (rich TUI)",
    )

    args = parser.parse_args()

    # Build config
    from ict_agent.controller.agent_controller import VexController, VexConfig

    config = VexConfig.from_env()
    config.dry_run = args.dry_run
    config.scan_interval_seconds = args.interval
    config.check_news = not args.no_news
    config.learn_from_trades = not args.no_learn
    config.verbose = not args.quiet
    config.max_trades_per_day = args.max_trades

    if args.symbols:
        config.symbols = args.symbols

    # Create controller
    controller = VexController(config=config)

    # Attach dashboard if requested
    if args.dashboard:
        controller.enable_dashboard()

    # Boot
    if not controller.boot():
        print("\n❌ Boot failed. Check credentials and try again.")
        sys.exit(1)

    # Status mode
    if args.status:
        import json

        status = controller.get_status()
        print("\n📊 Agent Status:")
        print(json.dumps(status, indent=2, default=str))
        sys.exit(0)

    # Run
    controller.run(
        duration_minutes=args.duration,
        max_cycles=args.cycles,
    )


if __name__ == "__main__":
    main()
