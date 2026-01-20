"""
VEX Journal Engine - Complete trade journaling system.

Handles:
- Pre-trade journal with structured questions
- Entry/exit logging
- Post-trade review workflow
- Trade database management
- Cloud sync to Turso database
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict, field
from enum import Enum
import uuid

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
MEMORY_DIR = PROJECT_ROOT / "data" / "memory"
JOURNAL_DIR = PROJECT_ROOT / "journal" / "ashton"
TRADES_DB = JOURNAL_DIR / "trades_database.json"


def get_turso_db():
    """Get Turso database connection (lazy import to avoid circular deps)."""
    try:
        from ict_agent.database import get_db
        return get_db()
    except Exception as e:
        print(f"  ⚠️ Turso not available: {e}")
        return None


class TradeStatus(Enum):
    PLANNED = "planned"
    ACTIVE = "active"
    CLOSED = "closed"
    CANCELLED = "cancelled"


class TradeResult(Enum):
    WIN = "WIN"
    LOSS = "LOSS"
    BREAKEVEN = "BREAKEVEN"
    PENDING = "PENDING"


@dataclass
class PreTradeJournal:
    """Pre-trade checklist and journal entry."""
    # Market Analysis
    daily_bias: str  # BULLISH, BEARISH, NEUTRAL
    htf_structure: str  # Description of 4H structure
    key_levels: List[float]
    
    # Setup Details
    pair: str
    direction: str  # LONG, SHORT
    entry_zone: str  # Description
    entry_price: float
    stop_price: float
    target_price: float
    
    # Confluence Factors
    displacement: bool
    htf_fvg: bool
    ltf_confluence: bool
    liquidity_swept: bool
    killzone: str  # LONDON, NY_AM, NY_PM, ASIAN
    
    # Psychology Check
    emotional_state: str  # 1-10 scale description
    fomo_check: bool  # False = no FOMO
    revenge_check: bool  # False = not revenge trading
    confidence_level: int  # 1-10
    
    # Risk Management
    risk_percent: float
    risk_dollars: float
    rr_ratio: float
    
    # Final Checklist
    setup_grade: str  # A+, A, B+, B, C, D, F
    trade_thesis: str  # Why this trade?
    invalidation: str  # What would invalidate this?
    
    timestamp: str = ""
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


@dataclass
class TradeEntry:
    """Complete trade record."""
    id: str
    status: str
    
    # Pre-trade
    pre_trade: Dict
    
    # Execution
    entry_time: Optional[str] = None
    actual_entry: Optional[float] = None
    position_size: Optional[float] = None
    
    # In-Trade Updates
    updates: List[Dict] = field(default_factory=list)
    partials: List[Dict] = field(default_factory=list)
    stop_moved: bool = False
    
    # Exit
    exit_time: Optional[str] = None
    exit_price: Optional[float] = None
    exit_reason: str = ""
    
    # Result
    result: str = "PENDING"
    pnl_dollars: float = 0.0
    pnl_pips: float = 0.0
    pnl_percent: float = 0.0
    
    # Post-Trade Review
    post_trade: Optional[Dict] = None
    
    # Metadata
    created_at: str = ""
    updated_at: str = ""
    screenshots: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)


@dataclass
class PostTradeReview:
    """Post-trade analysis and lessons."""
    trade_id: str
    
    # Execution Analysis
    entry_quality: int  # 1-10
    exit_quality: int  # 1-10
    plan_followed: bool
    
    # What Worked
    worked_well: List[str]
    
    # What Didn't
    needs_improvement: List[str]
    
    # Market Analysis
    market_did: str  # What actually happened
    expected_vs_actual: str
    
    # Lessons
    key_lesson: str
    
    # Psychology
    emotional_during: str
    emotional_after: str
    
    # Rating
    overall_grade: str  # A-F
    would_take_again: bool
    
    # Optional fields with defaults
    add_to_rules: Optional[str] = None
    timestamp: str = ""
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


class JournalEngine:
    """
    Complete trade journaling system for ICT trading.
    Syncs to both local JSON and Turso cloud database.
    """
    
    def __init__(self, sync_to_cloud: bool = True):
        self.trades_db = self._load_trades_db()
        self.memory = self._load_memory()
        self.sync_to_cloud = sync_to_cloud
        self._turso = None
        JOURNAL_DIR.mkdir(parents=True, exist_ok=True)
    
    @property
    def turso(self):
        """Lazy load Turso connection."""
        if self._turso is None and self.sync_to_cloud:
            self._turso = get_turso_db()
        return self._turso
    
    def _load_trades_db(self) -> Dict:
        """Load trades database."""
        if TRADES_DB.exists():
            with open(TRADES_DB) as f:
                return json.load(f)
        return {
            "trades": [],
            "stats": {
                "total_trades": 0,
                "wins": 0,
                "losses": 0,
                "breakeven": 0,
                "total_pnl": 0.0
            },
            "last_updated": datetime.now().isoformat()
        }
    
    def _save_trades_db(self):
        """Save trades database."""
        self.trades_db["last_updated"] = datetime.now().isoformat()
        with open(TRADES_DB, "w") as f:
            json.dump(self.trades_db, f, indent=2)
    
    def _sync_trade_to_cloud(self, trade: Dict):
        """Sync a trade to Turso cloud database."""
        if not self.turso:
            return
        
        try:
            pre = trade.get("pre_trade", {})
            post = trade.get("post_trade", {})
            
            # Handle both old and new trade formats
            # Old format: pair at top level
            # New format: pair inside pre_trade
            pair = trade.get("pair") or pre.get("pair")
            direction = trade.get("direction") or pre.get("direction")
            
            if not pair or not direction:
                print(f"  ⚠️ Skipping trade without pair/direction: {trade.get('id')}")
                return
            
            # Convert to Turso format
            turso_trade = {
                "id": str(trade.get("id")),
                "pair": pair,
                "direction": direction,
                "entry_price": trade.get("entry") or pre.get("entry_price"),
                "stop_loss": trade.get("stop") or pre.get("stop_price"),
                "take_profit": trade.get("target1") or trade.get("target") or pre.get("target_price"),
                "position_size": trade.get("position_size"),
                "status": trade.get("status", "closed").upper(),
                "result": trade.get("outcome") or trade.get("result"),
                "pnl_dollars": trade.get("net_pnl") or trade.get("realized_pnl") or trade.get("pnl_dollars"),
                "pnl_pips": trade.get("realized_pips") or trade.get("pnl_pips"),
                "daily_bias": trade.get("daily_bias") or pre.get("daily_bias"),
                "killzone": trade.get("session") or pre.get("killzone"),
                "setup_type": trade.get("model") or pre.get("setup_type", ""),
                "setup_grade": trade.get("confidence") or pre.get("setup_grade"),
                "confluence_score": trade.get("confluence_count") or pre.get("confidence_level"),
                "emotional_state": pre.get("emotional_state"),
                "confidence": trade.get("confluence_count") or pre.get("confidence_level"),
                "reasoning": trade.get("notes") or pre.get("trade_thesis"),
                "executed_as_planned": post.get("plan_followed") if post else None,
                "lessons_learned": ", ".join(trade.get("lessons", [])) if trade.get("lessons") else (post.get("key_lesson") if post else None),
                "what_worked": ", ".join(post.get("worked_well", [])) if post else None,
                "what_didnt": ", ".join(trade.get("mistakes", [])) if trade.get("mistakes") else (", ".join(post.get("needs_improvement", [])) if post else None),
                "overall_grade": post.get("overall_grade") if post else None,
                "created_at": trade.get("date") or trade.get("created_at"),
                "entry_time": trade.get("open_time") or trade.get("entry_time"),
                "exit_time": trade.get("close_time") or trade.get("exit_time"),
            }
            
            self.turso.save_trade(turso_trade)
            print(f"  ☁️  Synced to cloud: {trade.get('id')}")
            
        except Exception as e:
            print(f"  ⚠️ Cloud sync failed: {e}")
    
    def _load_memory(self) -> Dict:
        """Load memory files."""
        memory = {}
        for name in ["rules", "patterns", "triggers", "lessons"]:
            path = MEMORY_DIR / f"{name}.json"
            if path.exists():
                with open(path) as f:
                    memory[name] = json.load(f)
        return memory
    
    def create_pre_trade(
        self,
        pair: str,
        direction: str,
        entry_price: float,
        stop_price: float,
        target_price: float,
        **kwargs
    ) -> TradeEntry:
        """
        Create a new trade with pre-trade journal.
        
        Returns TradeEntry with status=PLANNED
        """
        # Calculate R:R
        risk = abs(entry_price - stop_price)
        reward = abs(target_price - entry_price)
        rr_ratio = reward / risk if risk > 0 else 0
        
        pre_trade = PreTradeJournal(
            pair=pair,
            direction=direction,
            entry_price=entry_price,
            stop_price=stop_price,
            target_price=target_price,
            rr_ratio=round(rr_ratio, 2),
            daily_bias=kwargs.get("daily_bias", ""),
            htf_structure=kwargs.get("htf_structure", ""),
            key_levels=kwargs.get("key_levels", []),
            entry_zone=kwargs.get("entry_zone", ""),
            displacement=kwargs.get("displacement", False),
            htf_fvg=kwargs.get("htf_fvg", False),
            ltf_confluence=kwargs.get("ltf_confluence", False),
            liquidity_swept=kwargs.get("liquidity_swept", False),
            killzone=kwargs.get("killzone", ""),
            emotional_state=kwargs.get("emotional_state", ""),
            fomo_check=kwargs.get("fomo_check", False),
            revenge_check=kwargs.get("revenge_check", False),
            confidence_level=kwargs.get("confidence_level", 5),
            risk_percent=kwargs.get("risk_percent", 1.0),
            risk_dollars=kwargs.get("risk_dollars", 100.0),
            setup_grade=kwargs.get("setup_grade", ""),
            trade_thesis=kwargs.get("trade_thesis", ""),
            invalidation=kwargs.get("invalidation", "")
        )
        
        trade_id = f"{pair}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
        
        trade = TradeEntry(
            id=trade_id,
            status=TradeStatus.PLANNED.value,
            pre_trade=asdict(pre_trade),
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat()
        )
        
        # Add to database
        trade_dict = asdict(trade)
        self.trades_db["trades"].append(trade_dict)
        self._save_trades_db()
        
        # Sync to cloud
        self._sync_trade_to_cloud(trade_dict)
        
        return trade
    
    def activate_trade(
        self,
        trade_id: str,
        actual_entry: float,
        position_size: float
    ) -> Optional[TradeEntry]:
        """Mark trade as active (entry filled)."""
        for trade in self.trades_db["trades"]:
            if trade["id"] == trade_id:
                trade["status"] = TradeStatus.ACTIVE.value
                trade["entry_time"] = datetime.now().isoformat()
                trade["actual_entry"] = actual_entry
                trade["position_size"] = position_size
                trade["updated_at"] = datetime.now().isoformat()
                self._save_trades_db()
                return trade
        return None
    
    def add_update(self, trade_id: str, update: str, screenshot: Optional[str] = None):
        """Add in-trade update/note."""
        for trade in self.trades_db["trades"]:
            if trade["id"] == trade_id:
                trade["updates"].append({
                    "timestamp": datetime.now().isoformat(),
                    "note": update,
                    "screenshot": screenshot
                })
                trade["updated_at"] = datetime.now().isoformat()
                self._save_trades_db()
                return True
        return False
    
    def add_partial(
        self,
        trade_id: str,
        exit_price: float,
        size_closed: float,
        reason: str
    ):
        """Record partial take profit."""
        for trade in self.trades_db["trades"]:
            if trade["id"] == trade_id:
                trade["partials"].append({
                    "timestamp": datetime.now().isoformat(),
                    "exit_price": exit_price,
                    "size_closed": size_closed,
                    "reason": reason
                })
                trade["updated_at"] = datetime.now().isoformat()
                self._save_trades_db()
                return True
        return False
    
    def close_trade(
        self,
        trade_id: str,
        exit_price: float,
        exit_reason: str,
        pnl_dollars: float,
        pnl_pips: float
    ) -> Optional[Dict]:
        """Close trade and record result."""
        for trade in self.trades_db["trades"]:
            if trade["id"] == trade_id:
                trade["status"] = TradeStatus.CLOSED.value
                trade["exit_time"] = datetime.now().isoformat()
                trade["exit_price"] = exit_price
                trade["exit_reason"] = exit_reason
                trade["pnl_dollars"] = pnl_dollars
                trade["pnl_pips"] = pnl_pips
                
                # Determine result
                if pnl_dollars > 0:
                    trade["result"] = TradeResult.WIN.value
                    self.trades_db["stats"]["wins"] += 1
                elif pnl_dollars < 0:
                    trade["result"] = TradeResult.LOSS.value
                    self.trades_db["stats"]["losses"] += 1
                else:
                    trade["result"] = TradeResult.BREAKEVEN.value
                    self.trades_db["stats"]["breakeven"] += 1
                
                self.trades_db["stats"]["total_trades"] += 1
                self.trades_db["stats"]["total_pnl"] += pnl_dollars
                trade["updated_at"] = datetime.now().isoformat()
                
                self._save_trades_db()
                
                # Sync to cloud
                self._sync_trade_to_cloud(trade)
                
                return trade
        return None
    
    def add_post_trade_review(
        self,
        trade_id: str,
        review: PostTradeReview
    ) -> bool:
        """Add post-trade review to closed trade."""
        for trade in self.trades_db["trades"]:
            if trade["id"] == trade_id:
                trade["post_trade"] = asdict(review)
                trade["updated_at"] = datetime.now().isoformat()
                
                # If there's a lesson, add to lessons memory
                if review.key_lesson:
                    self._add_lesson(review.key_lesson, trade_id)
                
                # If there's a new rule suggestion
                if review.add_to_rules:
                    self._suggest_rule(review.add_to_rules, trade_id)
                
                self._save_trades_db()
                
                # Sync to cloud
                self._sync_trade_to_cloud(trade)
                
                return True
        return False
    
    def _add_lesson(self, lesson: str, trade_id: str):
        """Add lesson to lessons memory."""
        lessons_path = MEMORY_DIR / "lessons.json"
        if lessons_path.exists():
            with open(lessons_path) as f:
                lessons = json.load(f)
        else:
            lessons = {"key_lessons": []}
        
        lessons["key_lessons"].append({
            "lesson": lesson,
            "source_trade": trade_id,
            "date": datetime.now().isoformat()
        })
        
        with open(lessons_path, "w") as f:
            json.dump(lessons, f, indent=2)
    
    def _suggest_rule(self, rule: str, trade_id: str):
        """Suggest new rule based on trade."""
        rules_path = MEMORY_DIR / "rules.json"
        if rules_path.exists():
            with open(rules_path) as f:
                rules = json.load(f)
        else:
            rules = {"suggested_rules": []}
        
        if "suggested_rules" not in rules:
            rules["suggested_rules"] = []
        
        rules["suggested_rules"].append({
            "rule": rule,
            "source_trade": trade_id,
            "date": datetime.now().isoformat(),
            "status": "pending_review"
        })
        
        with open(rules_path, "w") as f:
            json.dump(rules, f, indent=2)
    
    def get_trade(self, trade_id: str) -> Optional[Dict]:
        """Get single trade by ID."""
        for trade in self.trades_db["trades"]:
            if trade["id"] == trade_id:
                return trade
        return None
    
    def get_active_trades(self) -> List[Dict]:
        """Get all active trades."""
        return [t for t in self.trades_db["trades"] if t["status"] == TradeStatus.ACTIVE.value]
    
    def get_planned_trades(self) -> List[Dict]:
        """Get all planned (not yet active) trades."""
        return [t for t in self.trades_db["trades"] if t["status"] == TradeStatus.PLANNED.value]
    
    def get_recent_trades(self, limit: int = 10) -> List[Dict]:
        """Get most recent trades."""
        sorted_trades = sorted(
            self.trades_db["trades"],
            key=lambda x: x.get("created_at", ""),
            reverse=True
        )
        return sorted_trades[:limit]
    
    def get_stats(self) -> Dict:
        """Get trading statistics."""
        stats = self.trades_db["stats"].copy()
        
        # Calculate win rate
        total = stats["wins"] + stats["losses"]
        stats["win_rate"] = round(stats["wins"] / total * 100, 1) if total > 0 else 0
        
        # Calculate average win/loss
        wins = [t for t in self.trades_db["trades"] if t["result"] == "WIN"]
        losses = [t for t in self.trades_db["trades"] if t["result"] == "LOSS"]
        
        stats["avg_win"] = sum(t["pnl_dollars"] for t in wins) / len(wins) if wins else 0
        stats["avg_loss"] = sum(t["pnl_dollars"] for t in losses) / len(losses) if losses else 0
        
        # Profit factor
        gross_profit = sum(t["pnl_dollars"] for t in wins)
        gross_loss = abs(sum(t["pnl_dollars"] for t in losses))
        stats["profit_factor"] = round(gross_profit / gross_loss, 2) if gross_loss > 0 else float('inf')
        
        return stats
    
    def sync_all_to_cloud(self) -> int:
        """Sync all local trades to cloud database. Returns count synced."""
        if not self.turso:
            print("  ❌ Turso database not available")
            return 0
        
        count = 0
        for trade in self.trades_db["trades"]:
            try:
                self._sync_trade_to_cloud(trade)
                count += 1
            except Exception as e:
                print(f"  ⚠️ Failed to sync {trade.get('id')}: {e}")
        
        print(f"\n  ✅ Synced {count} trades to cloud")
        return count
    
    def get_cloud_trades(self, limit: int = 50) -> List[Dict]:
        """Get trades from cloud database."""
        if not self.turso:
            return []
        
        try:
            return self.turso.get_trades(limit=limit)
        except Exception as e:
            print(f"  ⚠️ Failed to fetch cloud trades: {e}")
            return []
    
    def get_cloud_stats(self) -> Optional[Dict]:
        """Get trade statistics from cloud database."""
        if not self.turso:
            return None
        
        try:
            return self.turso.get_trade_stats()
        except Exception as e:
            print(f"  ⚠️ Failed to fetch cloud stats: {e}")
            return None
    
    def interactive_pre_trade(self) -> TradeEntry:
        """Interactive pre-trade journal via CLI."""
        print("\n" + "=" * 60)
        print("  PRE-TRADE JOURNAL")
        print("=" * 60 + "\n")
        
        # Basic Info
        pair = input("Pair (e.g., EURUSD): ").strip().upper()
        direction = input("Direction (LONG/SHORT): ").strip().upper()
        
        print("\n--- PRICE LEVELS ---")
        entry = float(input("Entry price: "))
        stop = float(input("Stop price: "))
        target = float(input("Target price: "))
        
        print("\n--- MARKET ANALYSIS ---")
        daily_bias = input("Daily bias (BULLISH/BEARISH/NEUTRAL): ").strip().upper()
        htf_structure = input("4H structure description: ").strip()
        
        print("\n--- CONFLUENCE CHECKLIST ---")
        displacement = input("Prior displacement present? (y/n): ").lower() == 'y'
        htf_fvg = input("4H FVG entry zone? (y/n): ").lower() == 'y'
        ltf_confluence = input("15M OB + FVG confluence? (y/n): ").lower() == 'y'
        liquidity_swept = input("Liquidity already swept? (y/n): ").lower() == 'y'
        killzone = input("Killzone (LONDON/NY_AM/NY_PM/ASIAN): ").strip().upper()
        
        print("\n--- PSYCHOLOGY CHECK ---")
        emotional = input("Emotional state (1-10, 10=calm): ")
        fomo = input("FOMO present? (y/n): ").lower() == 'y'
        revenge = input("Revenge trading? (y/n): ").lower() == 'y'
        confidence = int(input("Confidence level (1-10): "))
        
        print("\n--- RISK MANAGEMENT ---")
        risk_pct = float(input("Risk % of account: "))
        risk_dollars = float(input("Risk in dollars: "))
        
        print("\n--- TRADE THESIS ---")
        thesis = input("Why this trade? ").strip()
        invalidation = input("What invalidates this? ").strip()
        setup_grade = input("Setup grade (A+/A/B+/B/C/D/F): ").strip().upper()
        
        trade = self.create_pre_trade(
            pair=pair,
            direction=direction,
            entry_price=entry,
            stop_price=stop,
            target_price=target,
            daily_bias=daily_bias,
            htf_structure=htf_structure,
            displacement=displacement,
            htf_fvg=htf_fvg,
            ltf_confluence=ltf_confluence,
            liquidity_swept=liquidity_swept,
            killzone=killzone,
            emotional_state=emotional,
            fomo_check=fomo,
            revenge_check=revenge,
            confidence_level=confidence,
            risk_percent=risk_pct,
            risk_dollars=risk_dollars,
            trade_thesis=thesis,
            invalidation=invalidation,
            setup_grade=setup_grade
        )
        
        print(f"\n✅ Trade created: {trade.id}")
        return trade
    
    def interactive_post_trade(self, trade_id: str) -> bool:
        """Interactive post-trade review via CLI."""
        trade = self.get_trade(trade_id)
        if not trade:
            print(f"Trade not found: {trade_id}")
            return False
        
        print("\n" + "=" * 60)
        print("  POST-TRADE REVIEW")
        print(f"  Trade: {trade_id}")
        print("=" * 60 + "\n")
        
        # Execution Analysis
        print("--- EXECUTION ANALYSIS ---")
        entry_quality = int(input("Entry quality (1-10): "))
        exit_quality = int(input("Exit quality (1-10): "))
        plan_followed = input("Did you follow the plan? (y/n): ").lower() == 'y'
        
        # What Worked
        print("\n--- WHAT WORKED WELL ---")
        worked = input("List what worked (comma-separated): ").strip()
        worked_well = [w.strip() for w in worked.split(",") if w.strip()]
        
        # What Didn't
        print("\n--- NEEDS IMPROVEMENT ---")
        improve = input("List improvements (comma-separated): ").strip()
        needs_improvement = [i.strip() for i in improve.split(",") if i.strip()]
        
        # Market Analysis
        print("\n--- MARKET ANALYSIS ---")
        market_did = input("What did the market actually do? ").strip()
        expected_vs_actual = input("Expected vs actual: ").strip()
        
        # Lessons
        print("\n--- LESSONS ---")
        key_lesson = input("Key lesson from this trade: ").strip()
        add_rule = input("New rule to add? (leave blank if none): ").strip()
        
        # Psychology
        print("\n--- PSYCHOLOGY ---")
        emotional_during = input("Emotional state during trade: ").strip()
        emotional_after = input("Emotional state after trade: ").strip()
        
        # Final Rating
        print("\n--- FINAL RATING ---")
        overall_grade = input("Overall grade (A-F): ").strip().upper()
        would_take = input("Would you take this trade again? (y/n): ").lower() == 'y'
        
        review = PostTradeReview(
            trade_id=trade_id,
            entry_quality=entry_quality,
            exit_quality=exit_quality,
            plan_followed=plan_followed,
            worked_well=worked_well,
            needs_improvement=needs_improvement,
            market_did=market_did,
            expected_vs_actual=expected_vs_actual,
            key_lesson=key_lesson,
            add_to_rules=add_rule if add_rule else None,
            emotional_during=emotional_during,
            emotional_after=emotional_after,
            overall_grade=overall_grade,
            would_take_again=would_take
        )
        
        self.add_post_trade_review(trade_id, review)
        print(f"\n✅ Post-trade review saved for {trade_id}")
        return True
    
    def format_trade_summary(self, trade: Dict) -> str:
        """Format trade as readable summary."""
        lines = []
        pre = trade.get("pre_trade", {})
        
        status_icons = {
            "planned": "📋",
            "active": "🔥",
            "closed": "✅" if trade.get("result") == "WIN" else "❌",
            "cancelled": "🚫"
        }
        
        icon = status_icons.get(trade.get("status"), "❓")
        
        lines.append(f"\n{icon} {trade['id']}")
        lines.append(f"   {pre.get('pair', '?')} {pre.get('direction', '?')} | Status: {trade.get('status', '?').upper()}")
        lines.append(f"   Entry: {pre.get('entry_price')} | Stop: {pre.get('stop_price')} | Target: {pre.get('target_price')}")
        lines.append(f"   R:R: {pre.get('rr_ratio', 0)}:1 | Grade: {pre.get('setup_grade', '?')}")
        
        if trade.get("result") != "PENDING":
            lines.append(f"   Result: {trade.get('result')} | P&L: ${trade.get('pnl_dollars', 0):.2f} ({trade.get('pnl_pips', 0):.1f} pips)")
        
        return "\n".join(lines)
    
    def format_stats_report(self) -> str:
        """Format statistics as readable report."""
        stats = self.get_stats()
        
        lines = []
        lines.append("\n" + "=" * 50)
        lines.append("  TRADING STATISTICS")
        lines.append("=" * 50)
        lines.append(f"\n  Total Trades: {stats['total_trades']}")
        lines.append(f"  Wins: {stats['wins']} | Losses: {stats['losses']} | BE: {stats['breakeven']}")
        lines.append(f"  Win Rate: {stats['win_rate']}%")
        lines.append(f"\n  Total P&L: ${stats['total_pnl']:.2f}")
        lines.append(f"  Avg Win: ${stats['avg_win']:.2f}")
        lines.append(f"  Avg Loss: ${stats['avg_loss']:.2f}")
        lines.append(f"  Profit Factor: {stats['profit_factor']}")
        lines.append("=" * 50)
        
        return "\n".join(lines)


def main():
    """CLI entry point for journal engine."""
    import sys
    
    engine = JournalEngine()
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python journal_engine.py new        - Create new trade")
        print("  python journal_engine.py review ID  - Post-trade review")
        print("  python journal_engine.py list       - List recent trades")
        print("  python journal_engine.py stats      - Show statistics")
        return
    
    cmd = sys.argv[1].lower()
    
    if cmd == "new":
        engine.interactive_pre_trade()
    elif cmd == "review" and len(sys.argv) >= 3:
        engine.interactive_post_trade(sys.argv[2])
    elif cmd == "list":
        trades = engine.get_recent_trades()
        for trade in trades:
            print(engine.format_trade_summary(trade))
    elif cmd == "stats":
        print(engine.format_stats_report())
    else:
        print(f"Unknown command: {cmd}")


if __name__ == "__main__":
    main()
