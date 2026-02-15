#!/usr/bin/env python3
"""
VEX Brain Initializer
=====================
Creates all missing data/learning files with proper schemas.
Seeds initial weights from existing pattern_stats and vex_memory.

Run: python scripts/init_brain.py
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

NY_TZ = ZoneInfo("America/New_York")

# Project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "learning"
DATA_DIR.mkdir(parents=True, exist_ok=True)


def init_trade_lessons():
    """Initialize trade_lessons.json — every trade VEX remembers"""
    path = DATA_DIR / "trade_lessons.json"
    if path.exists():
        print(f"  ⏭️  trade_lessons.json already exists ({path})")
        return

    data = []  # Empty list — lessons get appended by TradeLearner.learn_from_trade()
    
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)
    print(f"  ✅ Created trade_lessons.json (empty — ready to record)")


def init_insights():
    """Initialize insights.json — aggregated learnings"""
    path = DATA_DIR / "insights.json"
    if path.exists():
        print(f"  ⏭️  insights.json already exists ({path})")
        return

    data = {
        "best_setups": [
            {
                "description": "Displacement Follow-Through in NY Overlap",
                "win_rate": 1.0,
                "avg_rr": 1.875,
                "sample_size": 6,
                "source": "pattern_stats migration"
            },
            {
                "description": "Silver Bullet in NY AM killzone",
                "win_rate": 1.0,
                "avg_rr": 2.15,
                "sample_size": 6,
                "source": "pattern_stats migration"
            },
            {
                "description": "Model 11 in London killzone",
                "win_rate": 1.0,
                "avg_rr": 2.5,
                "sample_size": 2,
                "source": "pattern_stats migration"
            }
        ],
        "worst_setups": [
            {
                "description": "Unknown model in Asian session",
                "win_rate": 0.0,
                "avg_rr": -1.0,
                "sample_size": 3,
                "lesson": "No trading in Asian session without clear model ID",
                "source": "pattern_stats migration"
            }
        ],
        "rules_learned": [
            "Quality over quantity: 1 good EU trade > 6 forced GU trades",
            "First loss is best loss — re-entries multiply losses",
            "When stressed about 5M, zoom out. LTF is noise.",
            "All ICT trades are IRL→ERL or ERL→IRL",
            "Commissions ($2.50/lot) destroy profits from 'nimble' entries",
            "FVG > OB — algorithm returns to the void (imbalance), 50% is key",
            "Equal lows are NOT support — they are LIQUIDITY"
        ],
        "patterns_to_avoid": [
            "Trading Asian session without model confluence",
            "Multiple re-entries on same thesis (GBP/USD cost $234)",
            "Stops too tight (4 pips — spread kills you)",
            "Getting 'entranced' during trades — use checkpoints"
        ],
        "optimal_conditions": {
            "best_killzone": "ny_am",
            "best_models": ["silver_bullet", "Displacement_Follow_Through"],
            "best_pair": "EUR_USD",
            "min_confluences": 5,
            "min_rr": 2.0
        },
        "last_updated": datetime.now(NY_TZ).isoformat()
    }

    with open(path, 'w') as f:
        json.dump(data, f, indent=2)
    print(f"  ✅ Created insights.json (seeded from pattern_stats + vex_memory)")


def init_confluence_stats():
    """Initialize confluence_stats.json — learned confluence effectiveness"""
    path = DATA_DIR / "confluence_stats.json"
    if path.exists():
        print(f"  ⏭️  confluence_stats.json already exists ({path})")
        return

    data = {
        "combinations": {},
        "individual_scores": {
            "htf_fvg": {"weight": 20, "appearances": 0, "win_rate": 0.0},
            "ltf_fvg": {"weight": 15, "appearances": 0, "win_rate": 0.0},
            "order_block": {"weight": 15, "appearances": 0, "win_rate": 0.0},
            "displacement": {"weight": 10, "appearances": 0, "win_rate": 0.0},
            "structure_break": {"weight": 15, "appearances": 0, "win_rate": 0.0},
            "liquidity_sweep": {"weight": 20, "appearances": 0, "win_rate": 0.0},
            "killzone_active": {"weight": 10, "appearances": 0, "win_rate": 0.0},
            "premium_discount": {"weight": 10, "appearances": 0, "win_rate": 0.0},
            "smt_divergence": {"weight": 15, "appearances": 0, "win_rate": 0.0},
            "model_detection": {"weight": 25, "appearances": 0, "win_rate": 0.0},
            "fvg_50_touch": {"weight": 18, "appearances": 0, "win_rate": 0.0},
            "equal_level_sweep": {"weight": 20, "appearances": 0, "win_rate": 0.0},
            "amd_phase_confirmed": {"weight": 12, "appearances": 0, "win_rate": 0.0}
        },
        "total_trades_analyzed": 0,
        "last_updated": datetime.now(NY_TZ).isoformat(),
        "notes": "Initial weights from VEX_IDENTITY.md scoring system. Will auto-adjust as trades are recorded."
    }

    with open(path, 'w') as f:
        json.dump(data, f, indent=2)
    print(f"  ✅ Created confluence_stats.json (13 confluences initialized with default weights)")


def init_user_teachings():
    """Initialize user_teachings.json — things Ashton taught VEX"""
    path = DATA_DIR / "user_teachings.json"
    if path.exists():
        print(f"  ⏭️  user_teachings.json already exists ({path})")
        return

    # Seed from existing vex_memory.json golden rules
    data = [
        {
            "timestamp": "2026-01-15T22:45:00-05:00",
            "topic": "Sell Model - Liquidity Sweep Sequence",
            "content": "Equal lows are NOT support, they are LIQUIDITY. 2-3 candles at same area = liquidity pool. Sweep is fluid/destined, not violent. FVG more important than OB - algorithm returning to the void. 50% of FVG imbalance is key level.",
            "category": "insight",
            "applied_to": ["fvg", "liquidity", "sell_model", "order_block"]
        },
        {
            "timestamp": "2026-01-15T22:30:00-05:00",
            "topic": "Chart Annotation Standards",
            "content": "Be SPECIFIC and SURGICAL. Thin lines, small boxes on exact levels. Tell the story — show the sequence of how patterns connect. Don't use vague circles.",
            "category": "preference",
            "applied_to": ["visualization", "analysis"]
        },
        {
            "timestamp": "2026-01-15T10:00:00-05:00",
            "topic": "Quality Over Quantity",
            "content": "EU with ONE entry = +$534. GU with 6 entries = -$234. One good trade beats many forced trades. Commissions ($2.50/lot) destroy profits from being 'nimble'.",
            "category": "rule",
            "applied_to": ["risk_management", "entry_discipline"]
        },
        {
            "timestamp": "2026-01-15T10:00:00-05:00",
            "topic": "First Loss Best Loss",
            "content": "Take the first loss and move on. Re-entries on same thesis multiply losses. Check HTF before re-entering — is structure different or am I emotional?",
            "category": "rule",
            "applied_to": ["psychology", "risk_management"]
        },
        {
            "timestamp": "2026-01-15T10:00:00-05:00",
            "topic": "IRL/ERL Framework",
            "content": "ALL ICT trades are either IRL→ERL (enter at FVG/OB, target liquidity) or ERL→IRL (turtle soup, target FVG/equilibrium). This is the decoder ring for everything.",
            "category": "insight",
            "applied_to": ["irl_erl", "trade_models", "entry_rules", "exit_rules"]
        },
        {
            "timestamp": "2026-01-15T10:00:00-05:00",
            "topic": "Stop Distance",
            "content": "4-pip stops get killed by spread. Give the trade room to breathe. Use structure-based stops, not arbitrary pip counts.",
            "category": "correction",
            "applied_to": ["risk_management", "stop_loss"]
        }
    ]

    with open(path, 'w') as f:
        json.dump(data, f, indent=2)
    print(f"  ✅ Created user_teachings.json (seeded with {len(data)} teachings from Ashton)")


def verify():
    """Verify all files exist and are valid JSON"""
    required = [
        "trade_lessons.json",
        "insights.json",
        "confluence_stats.json",
        "user_teachings.json",
        "pattern_stats.json",
        "vex_memory.json",
        "learned_concepts.json",
    ]
    
    print("\n📋 Verification:")
    all_good = True
    for fname in required:
        path = DATA_DIR / fname
        if path.exists():
            try:
                with open(path) as f:
                    data = json.load(f)
                size = path.stat().st_size
                if isinstance(data, list):
                    print(f"  ✅ {fname} ({size:,}B, {len(data)} items)")
                elif isinstance(data, dict):
                    print(f"  ✅ {fname} ({size:,}B, {len(data)} keys)")
            except json.JSONDecodeError:
                print(f"  ❌ {fname} — INVALID JSON!")
                all_good = False
        else:
            print(f"  ❌ {fname} — MISSING!")
            all_good = False
    
    return all_good


def main():
    print("🧠 VEX Brain Initializer")
    print(f"   Data dir: {DATA_DIR}")
    print()

    init_trade_lessons()
    init_insights()
    init_confluence_stats()
    init_user_teachings()

    ok = verify()
    
    if ok:
        print("\n🟢 Brain is initialized. VEX has memory.")
        print("   TradeLearner and KnowledgeManager can now load all data files.")
    else:
        print("\n🔴 Some files are missing or corrupt. Check above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
