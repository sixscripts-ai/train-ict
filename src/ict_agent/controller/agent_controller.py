"""
VEX Agent Controller
====================
The brain of the agent. Drives the autonomous trading loop.

State Machine:
    BOOT → IDLE → SCANNING → ANALYZING → GATING → EXECUTING → MONITORING → LEARNING → IDLE
                                                                                          ↓
                                                                                      SHUTDOWN

Each state transition is a step(). The controller calls skills and publishes events.
All decisions flow through gates: killzone → news → risk → signal → execute → learn.

Inspired by OpenHands agent_controller.py but built for trading.

Created: 2026-02-15
Authors: VS Code Copilot + Antigravity (collaborative build)
"""

import os
import sys
import time
import traceback
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

NY_TZ = ZoneInfo("America/New_York")


# ═══════════════════════════════════════════════════════════════════════════════
# STATE & CONFIG
# ═══════════════════════════════════════════════════════════════════════════════

class VexState(Enum):
    """Agent state machine states."""
    BOOT = "boot"
    IDLE = "idle"
    SCANNING = "scanning"
    ANALYZING = "analyzing"
    GATING = "gating"          # News + Risk checks before execution
    EXECUTING = "executing"
    MONITORING = "monitoring"
    LEARNING = "learning"
    SHUTDOWN = "shutdown"
    ERROR = "error"


@dataclass
class VexConfig:
    """Configuration for the VEX agent."""
    # Trading
    symbols: List[str] = field(default_factory=lambda: [
        "EUR_USD", "GBP_USD", "XAU_USD", "USD_JPY", "AUD_USD", "EUR_GBP"
    ])
    scan_interval_seconds: int = 300  # 5 minutes between scan cycles
    max_trades_per_day: int = 8
    dry_run: bool = False  # If True, no real trades placed

    # OANDA
    api_key: str = ""
    account_id: str = ""
    environment: str = "practice"

    # Paths
    data_dir: Path = field(default_factory=lambda: Path(__file__).parent.parent.parent.parent / "data")
    learning_dir: Path = field(default_factory=lambda: Path(__file__).parent.parent.parent.parent / "data" / "learning")

    # Behavior
    learn_from_trades: bool = True
    check_news: bool = True
    use_core_engine: bool = True  # Use VexCoreEngine vs old SignalGenerator
    verbose: bool = True

    @classmethod
    def from_env(cls) -> "VexConfig":
        """Load config from environment variables."""
        return cls(
            api_key=os.getenv("OANDA_API_KEY", ""),
            account_id=os.getenv("OANDA_ACCOUNT_ID", ""),
            environment=os.getenv("OANDA_ENV", "practice"),
            dry_run=os.getenv("VEX_DRY_RUN", "false").lower() == "true",
        )


# ═══════════════════════════════════════════════════════════════════════════════
# CONTROLLER
# ═══════════════════════════════════════════════════════════════════════════════

class VexController:
    """
    The VEX Agent Controller.
    
    Drives the autonomous trading loop through a state machine.
    Each cycle: scan → analyze → gate (news+risk) → execute → monitor → learn
    
    All components are wired through the SkillRegistry and EventStream.
    The controller doesn't DO the work — it orchestrates skills that do.
    """

    def __init__(self, config: Optional[VexConfig] = None):
        self.config = config or VexConfig.from_env()
        self.state = VexState.BOOT
        self.running = False

        # Cycle tracking
        self.cycle_count = 0
        self.trades_today = 0
        self.session_start: Optional[datetime] = None
        self.last_cycle_time: Optional[datetime] = None

        # Components (initialized in boot())
        self.event_stream = None
        self.skill_registry = None
        self.executor = None
        self.risk_guardian = None
        self.journal = None
        self.trade_learner = None
        self.news_filter = None
        self.core_engine = None
        self.killzone_manager = None

        # State data
        self._pending_setups: List[Dict] = []
        self._active_trades: List[Dict] = []
        self._session_pnl: float = 0.0

    # ═══════════════════════════════════════════════════════════════════════════
    # BOOT
    # ═══════════════════════════════════════════════════════════════════════════

    def boot(self) -> bool:
        """
        Initialize all components and wire them together.
        Returns True if boot succeeded.
        """
        self.state = VexState.BOOT
        self.session_start = datetime.now(NY_TZ)

        print("═" * 62)
        print("🤖 VEX AGENT CONTROLLER — BOOTING")
        print("═" * 62)

        try:
            # 1. Load .env if needed
            self._load_env()

            if not self.config.api_key or not self.config.account_id:
                print("   ❌ Missing OANDA credentials")
                return False

            # 2. Event Stream
            from ict_agent.events.event_stream import EventStream
            self.event_stream = EventStream(
                log_dir=self.config.data_dir / "events"
            )
            print("   ✅ EventStream online")

            # 3. Skill Registry
            from ict_agent.skills.base import SkillRegistry
            self.skill_registry = SkillRegistry()

            # 4. OANDA Executor
            from ict_agent.execution.oanda_executor import OANDAExecutor
            self.executor = OANDAExecutor(
                api_key=self.config.api_key,
                account_id=self.config.account_id,
                environment=self.config.environment,
            )
            print(f"   ✅ OANDAExecutor ({self.config.environment})")

            # 5. Risk Guardian
            from ict_agent.execution.risk_guardian import RiskGuardian, RiskConfig
            risk_config = RiskConfig(
                max_risk_percent=2.5,
                max_trades_per_day=self.config.max_trades_per_day,
                max_drawdown_usd=450.0,
                max_total_exposure=450.0,
                max_open_positions=4,
            )
            self.risk_guardian = RiskGuardian(
                executor=self.executor,
                config=risk_config,
            )
            print("   ✅ RiskGuardian armed")

            # 6. Journal
            from ict_agent.execution.agent_journal import AgentJournal
            self.journal = AgentJournal()
            print("   ✅ AgentJournal ready")

            # 7. Trade Learner
            from ict_agent.learning.trade_learner import TradeLearner
            self.trade_learner = TradeLearner(data_dir=self.config.learning_dir)
            lessons_count = len(self.trade_learner.lessons) if hasattr(self.trade_learner, "lessons") else 0
            patterns_count = len(self.trade_learner.patterns) if hasattr(self.trade_learner, "patterns") else 0
            print(f"   ✅ TradeLearner ({lessons_count} lessons, {patterns_count} patterns)")

            # 8. News Filter
            if self.config.check_news:
                try:
                    from ict_agent.engine.news_filter import NewsFilter
                    self.news_filter = NewsFilter()
                    print("   ✅ NewsFilter (ForexFactory)")
                except Exception as e:
                    print(f"   ⚠️ NewsFilter failed: {e} (continuing without)")
                    self.news_filter = None

            # 9. VEX Core Engine
            if self.config.use_core_engine:
                from ict_agent.core.vex_core_engine import VexCoreEngine
                self.core_engine = VexCoreEngine()
                print("   ✅ VexCoreEngine (8-gate system)")

                # 9a. Graph-Driven Reasoner (enhances Gate 8)
                if self.core_engine.graph_reasoner is not None:
                    # Trigger lazy load during boot so any errors show up early
                    try:
                        loaded = self.core_engine.graph_reasoner._ensure_loaded()
                        if loaded:
                            store = self.core_engine.graph_reasoner._store
                            n = store.G.number_of_nodes() if store else 0
                            e = store.G.number_of_edges() if store else 0
                            print(f"   ✅ GraphReasoner ({n:,} nodes, {e:,} edges)")
                        else:
                            print("   ⚠️ GraphReasoner unavailable (graph_rag not found)")
                    except Exception as gr_err:
                        print(f"   ⚠️ GraphReasoner failed: {gr_err}")

            # 9b. Knowledge Manager (shared instance — avoid re-creation per analyze call)
            try:
                from ict_agent.learning.knowledge_manager import KnowledgeManager
                self.knowledge_manager = KnowledgeManager()
                concepts = len(self.knowledge_manager.concepts) if hasattr(self.knowledge_manager, 'concepts') else 0
                print(f"   ✅ KnowledgeManager ({concepts} concepts)")
            except Exception as e:
                print(f"   ⚠️ KnowledgeManager failed: {e}")
                self.knowledge_manager = None

            # 10. Killzone Manager
            from ict_agent.engine.killzone import KillzoneManager
            self.killzone_manager = KillzoneManager()
            print("   ✅ KillzoneManager")

            # 11. Register Skills
            from ict_agent.skills.scan_skill import ScanSkill
            from ict_agent.skills.analyze_skill import AnalyzeSkill
            from ict_agent.skills.execute_skill import ExecuteSkill
            from ict_agent.skills.learn_skill import LearnSkill
            from ict_agent.skills.news_skill import NewsSkill
            from ict_agent.skills.strategy_skill import StrategySkill

            self.skill_registry.register(ScanSkill())
            self.skill_registry.register(AnalyzeSkill())
            self.skill_registry.register(ExecuteSkill())
            self.skill_registry.register(LearnSkill())
            self.skill_registry.register(NewsSkill())
            self.skill_registry.register(StrategySkill())
            print(f"   ✅ Skills: {self.skill_registry.list_skills()}")

            # 12. Memory System
            from ict_agent.memory.memory_manager import MemoryManager
            self.memory = MemoryManager(data_dir=self.config.learning_dir)
            mem_status = self.memory.boot()
            print(f"   ✅ MemorySystem ({mem_status['knowledge_files']} knowledge files)")

            # 12b. Performance Tracker
            from ict_agent.memory.performance import PerformanceTracker
            account = self.executor.get_account_info()
            starting_bal = account.balance if account and hasattr(account, 'balance') else 10000.0
            self.performance = PerformanceTracker(starting_balance=starting_bal)
            print(f"   ✅ PerformanceTracker (${starting_bal:,.2f})")

            # 13. Wire event subscribers (including memory)
            self._wire_event_handlers()

            # 14. Verify OANDA connection (reuse account from above)
            if account:
                balance = account.balance if hasattr(account, 'balance') else 0
                print(f"   ✅ OANDA verified — Balance: ${balance:,.2f}")
            else:
                print("   ⚠️ Could not verify OANDA (will retry)")

            print("═" * 62)
            print(f"🟢 VEX AGENT READY — {len(self.config.symbols)} symbols")
            print(f"   Mode: {'DRY RUN' if self.config.dry_run else 'LIVE TRADING'}")
            print(f"   Skills: {len(self.skill_registry)} loaded")
            print("═" * 62)

            # Publish boot event
            from ict_agent.events.event_types import SystemEvent, EventType
            self.event_stream.publish(SystemEvent(
                event_type=EventType.SYSTEM_START,
                source="controller",
                message="VEX Agent booted successfully",
                level="info",
                component="controller",
            ))

            self.state = VexState.IDLE
            return True

        except Exception as e:
            print(f"\n   ❌ BOOT FAILED: {e}")
            traceback.print_exc()
            self.state = VexState.ERROR
            return False

    def _load_env(self) -> None:
        """Load .env file."""
        env_locations = [
            Path(__file__).parent.parent.parent.parent / ".env",
            Path.home() / "Documents" / "train-ict" / ".env",
        ]
        for env_path in env_locations:
            if env_path.exists():
                for line in open(env_path):
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, value = line.split("=", 1)
                        os.environ[key.strip()] = value.strip()
                # Update config from loaded env
                self.config.api_key = os.getenv("OANDA_API_KEY", self.config.api_key)
                self.config.account_id = os.getenv("OANDA_ACCOUNT_ID", self.config.account_id)
                self.config.environment = os.getenv("OANDA_ENV", self.config.environment)
                return

    def _wire_event_handlers(self) -> None:
        """Subscribe to events for logging, coordination, and memory."""
        from ict_agent.events.event_types import EventType

        if self.config.verbose:
            def log_event(event):
                ts = event.timestamp.strftime("%H:%M:%S")
                print(f"   [{ts}] 📡 {event.event_type.value} | {event.source} | {event.data.get('symbol', '')}")

            self.event_stream.subscribe_all(log_event)

        # Wire memory manager into event stream
        if hasattr(self, 'memory') and self.memory:
            self.event_stream.subscribe_all(self.memory.on_event)

    # ═══════════════════════════════════════════════════════════════════════════
    # MAIN LOOP
    # ═══════════════════════════════════════════════════════════════════════════

    def _safe_execute(self, skill_name: str, context: Dict[str, Any]) -> Optional[Any]:
        """Execute a skill with error handling — returns SkillResult or None on crash."""
        try:
            return self.skill_registry.execute(skill_name, context)
        except Exception as e:
            if self.config.verbose:
                print(f"   ❌ Skill '{skill_name}' crashed: {e}")
            from ict_agent.events.event_types import SystemEvent, EventType
            if self.event_stream:
                self.event_stream.publish(SystemEvent(
                    event_type=EventType.SYSTEM_ERROR,
                    source=f"skill:{skill_name}",
                    message=f"Skill crash: {e}",
                    level="error",
                    component=skill_name,
                ))
            return None

    def run(self, duration_minutes: Optional[int] = None, max_cycles: Optional[int] = None) -> None:
        """
        Main trading loop. Runs until stopped, duration expires, or max cycles reached.
        
        Args:
            duration_minutes: Run for this many minutes, then stop
            max_cycles: Run this many cycles, then stop
        """
        if self.state == VexState.BOOT:
            if not self.boot():
                return

        self.running = True
        start_time = datetime.now(NY_TZ)
        end_time = start_time + timedelta(minutes=duration_minutes) if duration_minutes else None

        print(f"\n🚀 VEX starting at {start_time.strftime('%H:%M:%S ET')}")
        if duration_minutes:
            print(f"   Duration: {duration_minutes} minutes")
        if max_cycles:
            print(f"   Max cycles: {max_cycles}")
        if self.config.dry_run:
            print("   ⚠️ DRY RUN MODE — no real trades will be placed")

        try:
            while self.running:
                # Check stop conditions
                if self.state == VexState.SHUTDOWN:
                    print("\n🛑 SHUTDOWN state reached")
                    break
                if end_time and datetime.now(NY_TZ) > end_time:
                    print("\n⏰ Duration complete")
                    break
                if max_cycles and self.cycle_count >= max_cycles:
                    print(f"\n🔄 Max cycles ({max_cycles}) reached")
                    break

                # Run one complete cycle
                self.step()

                # Wait before next cycle
                if self.running and self.state != VexState.SHUTDOWN:
                    time.sleep(self.config.scan_interval_seconds)

        except KeyboardInterrupt:
            print("\n\n⚠️ Agent stopped by user (Ctrl+C)")
        except Exception as e:
            print(f"\n❌ Fatal error: {e}")
            traceback.print_exc()
        finally:
            self.running = False
            self._session_summary()

    # ═══════════════════════════════════════════════════════════════════════════
    # STEP — One complete trading cycle
    # ═══════════════════════════════════════════════════════════════════════════

    def step(self) -> None:
        """
        Execute one complete trading cycle.
        
        IDLE → SCAN → ANALYZE (per symbol) → GATE → EXECUTE → MONITOR → LEARN → IDLE
        """
        self.cycle_count += 1
        self.last_cycle_time = datetime.now(NY_TZ)
        now = self.last_cycle_time

        if self.config.verbose:
            kz = self.killzone_manager.get_current_killzone(now) if self.killzone_manager else None
            kz_name = kz.value if kz else "No Session"
            print(f"\n{'─' * 50}")
            print(f"🔄 Cycle #{self.cycle_count} | {now.strftime('%H:%M:%S ET')} | {kz_name}")
            print(f"{'─' * 50}")

        # ─── PHASE 1: SCAN ───────────────────────────────────────────────
        self.state = VexState.SCANNING
        scan_result = self._safe_execute("scan", {
            "symbols": self.config.symbols,
            "killzone_manager": self.killzone_manager,
        })

        # Publish scan events
        if scan_result and scan_result.events:
            for event in scan_result.events:
                self.event_stream.publish(event)

        if not scan_result or not scan_result.success:
            self.state = VexState.IDLE
            return

        is_killzone = scan_result.data.get("is_primary_killzone", False)
        killzone_name = scan_result.data.get("killzone", "none")

        if not is_killzone:
            if self.config.verbose:
                print(f"   💤 Outside killzone ({killzone_name}) — waiting")
            self.state = VexState.IDLE
            # Still monitor positions even outside killzone
            self._monitor_positions()
            return

        # ─── PHASE 2: ANALYZE ────────────────────────────────────────────
        self.state = VexState.ANALYZING
        best_setup = None
        best_confidence = 0

        for symbol in self.config.symbols:
            # Build rich analysis context with memory recall
            analyze_context = {
                "symbol": symbol,
                "engine": self.core_engine,
                "killzone_override": killzone_name,
            }

            # Inject shared KnowledgeManager (avoids re-creation each call)
            if hasattr(self, 'knowledge_manager') and self.knowledge_manager:
                analyze_context["knowledge_manager"] = self.knowledge_manager

            # Inject memory recall — gives engine pre-trade intelligence
            if hasattr(self, 'memory') and self.memory:
                recall = self.memory.recall_for_analysis(
                    symbol=symbol,
                    session=killzone_name,
                )
                analyze_context["memory_recall"] = recall

                # Apply confidence adjustment from memory
                assessment = recall.get("should_trade", {})
                analyze_context["confidence_boost"] = assessment.get("confidence_boost", 0)
                if assessment.get("warnings"):
                    for w in assessment["warnings"]:
                        if self.config.verbose:
                            print(f"   ⚠️ Memory: {w}")

            analyze_result = self._safe_execute("analyze", analyze_context)

            # Publish analysis events
            if analyze_result and analyze_result.events:
                for event in analyze_result.events:
                    self.event_stream.publish(event)

            if analyze_result and analyze_result.data.get("trade"):
                confidence = analyze_result.data.get("confidence", 0)
                if confidence > best_confidence:
                    best_confidence = confidence
                    best_setup = analyze_result.data

        if not best_setup:
            if self.config.verbose:
                print("   📊 No setups found across all symbols")
            self.state = VexState.IDLE
            self._monitor_positions()
            return

        # ─── PHASE 2b: STRATEGY ADJUSTMENT ───────────────────────────────
        # Apply strategy-level confidence modifier based on historical performance
        if hasattr(self, 'performance') and self.performance and self.performance.total_trades >= 5:
            strategy_result = self._safe_execute("strategy", {
                "mode": "recommend",
                "performance": self.performance,
                "symbol": best_setup["symbol"],
                "model": best_setup.get("model", ""),
                "session": killzone_name,
                "base_confidence": best_setup["confidence"],
            })
            if strategy_result and strategy_result.success:
                old_conf = best_setup["confidence"]
                best_setup["confidence"] = strategy_result.data["adjusted_confidence"]
                modifier = strategy_result.data["strategy_modifier"]
                if modifier != 0 and self.config.verbose:
                    print(f"   📈 Strategy: {modifier:+.3f} confidence "
                          f"({old_conf*100:.0f}% → {best_setup['confidence']*100:.0f}%) "
                          f"[{strategy_result.data.get('overall_grade', '?')}]")

        if self.config.verbose:
            print(f"   🎯 Best: {best_setup['model']} {best_setup['direction']} "
                  f"{best_setup['symbol']} | Conf: {best_setup['confidence']*100:.0f}% | "
                  f"R:R: {best_setup['rr_ratio']:.1f}")

        # ─── PHASE 3: GATE (News + Risk) ─────────────────────────────────
        self.state = VexState.GATING

        # Gate 1: News check
        if self.config.check_news:
            news_result = self._safe_execute("news", {
                "symbol": best_setup["symbol"],
                "news_filter": self.news_filter,
            })
            if news_result and news_result.events:
                for event in news_result.events:
                    self.event_stream.publish(event)

            if news_result and not news_result.data.get("safe_to_trade", True):
                danger = news_result.data.get("next_danger", {})
                print(f"   🚫 NEWS GATE: Blocked — {danger.get('title', 'High impact event')} "
                      f"in {danger.get('minutes_away', '?')} min")
                self.state = VexState.IDLE
                return

        # Gate 2: Pre-trade learning check
        if self.config.learn_from_trades and self.trade_learner:
            learn_skill = self.skill_registry.get("learn")
            if learn_skill and hasattr(learn_skill, "pre_trade_check"):
                recall_result = learn_skill.pre_trade_check({
                    "trade_learner": self.trade_learner,
                    "symbol": best_setup["symbol"],
                    "model": best_setup.get("model", ""),
                    "killzone": killzone_name,
                })
                if recall_result and recall_result.data.get("warnings"):
                    for warning in recall_result.data["warnings"]:
                        print(f"   {warning}")

        # Gate 3: Trade count check
        if self.trades_today >= self.config.max_trades_per_day:
            print(f"   ⛔ Max trades/day ({self.config.max_trades_per_day}) reached")
            self.state = VexState.IDLE
            return

        # ─── PHASE 4: EXECUTE ────────────────────────────────────────────
        self.state = VexState.EXECUTING
        exec_result = self._safe_execute("execute", {
            "setup": best_setup,
            "executor": self.executor,
            "risk_guardian": self.risk_guardian,
            "journal": self.journal,
            "dry_run": self.config.dry_run,
        })

        if exec_result and exec_result.events:
            for event in exec_result.events:
                self.event_stream.publish(event)

        if exec_result and exec_result.success:
            self.trades_today += 1
            trade_data = exec_result.data
            self._active_trades.append(trade_data)

            if trade_data.get("dry_run"):
                print(f"   🏷️ DRY RUN: Would {trade_data['direction']} "
                      f"{trade_data['units']} {trade_data['symbol']} "
                      f"@ {trade_data['entry_price']:.5f}")
            else:
                print(f"   ✅ FILLED: {trade_data['direction']} "
                      f"{trade_data['units']} {trade_data['symbol']} "
                      f"@ {trade_data.get('fill_price', trade_data.get('entry_price', 0)):.5f} "
                      f"(Trade #{trade_data.get('trade_id', 'N/A')})")
        elif exec_result:
            print(f"   ❌ Execution failed: {exec_result.error}")

        # ─── PHASE 5: MONITOR ────────────────────────────────────────────
        self.state = VexState.MONITORING
        self._monitor_positions()

        # ─── PHASE 6: LEARN ──────────────────────────────────────────────
        if self.config.learn_from_trades:
            self.state = VexState.LEARNING
            self._check_and_learn_from_closed_trades()

        self.state = VexState.IDLE

    # ═══════════════════════════════════════════════════════════════════════════
    # MONITORING
    # ═══════════════════════════════════════════════════════════════════════════

    def _monitor_positions(self) -> None:
        """Monitor open positions for status updates."""
        if not self.executor:
            return

        try:
            open_trades = self.executor.get_open_trades()
            if not open_trades:
                return

            for trade in open_trades:
                unrealized = float(trade.get("unrealizedPL", 0))
                if abs(unrealized) > 25:  # Only show significant P&L
                    symbol = trade.get("instrument", "")
                    trade_id = trade.get("id", "")
                    print(f"   📊 #{trade_id} {symbol}: ${unrealized:+.2f}")
        except Exception:
            pass

    def _check_and_learn_from_closed_trades(self) -> None:
        """Check for recently closed trades and learn from them."""
        if not self.executor or not self.trade_learner:
            return

        try:
            # Get current open trade IDs from OANDA
            open_trades = self.executor.get_open_trades() or []
            open_ids = {t.get("id", "") for t in open_trades}

            # Check our active trades list for any that closed
            still_active = []
            for trade_data in self._active_trades:
                trade_id = trade_data.get("trade_id", "")
                if trade_id and trade_id not in open_ids:
                    # This trade was closed — learn from it
                    self._learn_from_closed_trade(trade_data)
                else:
                    still_active.append(trade_data)

            self._active_trades = still_active

        except Exception:
            pass

    def _learn_from_closed_trade(self, trade_data: Dict) -> None:
        """Learn from a trade that has closed."""
        from ict_agent.data.oanda_fetcher import get_current_price

        symbol = trade_data.get("symbol", "")
        entry_price = trade_data.get("fill_price", trade_data.get("entry_price", 0))
        stop_loss = trade_data.get("stop_loss", 0)
        take_profit = trade_data.get("take_profit", 0)
        direction = trade_data.get("direction", "BUY")

        # Try to get exit price
        price_data = get_current_price(symbol)
        exit_price = price_data.get("mid", entry_price) if price_data else entry_price

        # Determine outcome
        pip_value = 0.01 if "JPY" in symbol.upper() else 0.0001
        if direction == "BUY":
            pnl_pips = (exit_price - entry_price) / pip_value
        else:
            pnl_pips = (entry_price - exit_price) / pip_value

        outcome = "win" if pnl_pips > 0 else ("loss" if pnl_pips < 0 else "breakeven")
        risk_pips = abs(entry_price - stop_loss) / pip_value if stop_loss else 1
        rr_achieved = abs(pnl_pips / risk_pips) if risk_pips > 0 else 0

        # Learn
        learn_result = self._safe_execute("learn", {
            "trade_learner": self.trade_learner,
            "trade_data": {
                "trade_id": trade_data.get("trade_id", ""),
                "symbol": symbol,
                "model": trade_data.get("model", "unknown"),
                "outcome": outcome,
                "pnl": pnl_pips,
                "rr_achieved": rr_achieved,
                "killzone": trade_data.get("killzone", ""),
                "confluences": trade_data.get("confluences", []),
                "entry_price": entry_price,
                "exit_price": exit_price,
                "stop_loss": stop_loss,
                "take_profit": take_profit,
            },
        })

        if learn_result and learn_result.events:
            for event in learn_result.events:
                self.event_stream.publish(event)

        # Also record to memory manager for long-term storage
        if hasattr(self, 'memory') and self.memory:
            self.memory.record_trade_outcome(
                symbol=symbol,
                model=trade_data.get("model", "unknown"),
                direction=direction,
                outcome=outcome,
                pnl=pnl_pips,
                lesson=f"{outcome}: {symbol} {direction} | {pnl_pips:+.1f} pips | R:R {rr_achieved:.1f}",
                setup_details=trade_data,
            )

        # Record to performance tracker
        if hasattr(self, 'performance') and self.performance:
            units = trade_data.get("units", 0)
            pnl_usd = pnl_pips * (0.1 if "JPY" in symbol.upper() else 10.0) * (units / 100000) if units else pnl_pips
            self.performance.record_trade(
                trade_id=trade_data.get("trade_id", ""),
                symbol=symbol,
                model=trade_data.get("model", "unknown"),
                direction=direction,
                entry_price=entry_price,
                exit_price=exit_price,
                pnl_pips=pnl_pips,
                pnl_usd=pnl_usd,
                rr_achieved=rr_achieved,
                killzone=trade_data.get("killzone", ""),
            )

        if self.config.verbose:
            emoji = "✅" if outcome == "win" else ("❌" if outcome == "loss" else "➖")
            print(f"   {emoji} Closed trade {symbol} | {outcome.upper()} | "
                  f"{pnl_pips:+.1f} pips | R:R {rr_achieved:.1f}")

        if learn_result and learn_result.success:
            lesson = learn_result.data.get("lesson", "")
            print(f"   🧠 Learned from {outcome}: {lesson[:80]}" if lesson else
                  f"   🧠 Learned: {outcome} on {symbol}")

    # ═══════════════════════════════════════════════════════════════════════════
    # SESSION MANAGEMENT
    # ═══════════════════════════════════════════════════════════════════════════

    def _session_summary(self) -> None:
        """Print summary at end of session."""
        now = datetime.now(NY_TZ)
        duration = now - self.session_start if self.session_start else timedelta(0)

        print("\n")
        print("═" * 62)
        print("📊 VEX SESSION SUMMARY")
        print("═" * 62)
        print(f"   Duration: {duration}")
        print(f"   Cycles:   {self.cycle_count}")
        print(f"   Trades:   {self.trades_today}")
        print(f"   Mode:     {'DRY RUN' if self.config.dry_run else 'LIVE'}")

        if self.event_stream:
            summary = self.event_stream.get_summary()
            print(f"\n   Event Summary:")
            for event_type, count in sorted(summary.items()):
                print(f"     {event_type}: {count}")

        if self.risk_guardian and hasattr(self.risk_guardian, "state"):
            print(f"\n   Risk State:")
            print(f"     Daily P&L:  ${self.risk_guardian.state.daily_pnl:+.2f}")
            print(f"     Drawdown:   ${self.risk_guardian.state.current_drawdown:.2f}")

        if self.journal:
            print(f"\n   Journal:")
            print(f"   {self.journal.format_daily_report()}")

        print("═" * 62)
        print("🛑 VEX Agent stopped.\n")

    def stop(self) -> None:
        """Stop the agent gracefully."""
        self.running = False
        self.state = VexState.SHUTDOWN

        from ict_agent.events.event_types import SystemEvent, EventType
        if self.event_stream:
            self.event_stream.publish(SystemEvent(
                event_type=EventType.SYSTEM_STOP,
                source="controller",
                message="VEX Agent stopped",
                level="info",
                component="controller",
            ))

    def reset_daily(self) -> None:
        """Reset daily counters (call at start of new trading day)."""
        self.trades_today = 0
        self._session_pnl = 0.0
        if self.risk_guardian and hasattr(self.risk_guardian, "reset_daily"):
            self.risk_guardian.reset_daily()
        print("   🔄 Daily state reset")

    def get_status(self) -> Dict[str, Any]:
        """Get current agent status."""
        status = {
            "state": self.state.value,
            "running": self.running,
            "cycle_count": self.cycle_count,
            "trades_today": self.trades_today,
            "active_trades": len(self._active_trades),
            "dry_run": self.config.dry_run,
            "symbols": self.config.symbols,
            "skills": self.skill_registry.list_skills() if self.skill_registry else [],
            "events_total": self.event_stream.event_count if self.event_stream else 0,
            "session_start": self.session_start.isoformat() if self.session_start else None,
            "last_cycle": self.last_cycle_time.isoformat() if self.last_cycle_time else None,
        }
        if hasattr(self, 'memory') and self.memory:
            status["memory"] = self.memory.get_status()
        if hasattr(self, 'performance') and self.performance:
            status["performance"] = self.performance.status()
        return status
