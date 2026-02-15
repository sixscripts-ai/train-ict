"""
MemoryManager — Unified interface to the VEX memory system.

Coordinates ShortTermMemory, LongTermMemory, and KnowledgeRecall.
Subscribes to EventStream for automatic memory updates.

Inspired by OpenHands Memory class:
  - Listens to events and updates memory automatically
  - Provides contextual recall for analysis enrichment
  - Bridges session state with persistent knowledge
"""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

from ict_agent.memory.short_term import ShortTermMemory, SignalMemory, TradeMemory
from ict_agent.memory.long_term import LongTermMemory
from ict_agent.memory.recall import KnowledgeRecall

NY_TZ = ZoneInfo("America/New_York")


class MemoryManager:
    """
    Unified memory interface for the VEX agent.
    
    Lifecycle:
      1. boot() — Initialize all memory tiers
      2. on_event() — Called by EventStream, auto-updates memory
      3. recall_for_analysis() — Called before trade decisions
      4. record_trade_outcome() — Called after trade closes
      5. session_summary() — Export session stats at shutdown
    """

    def __init__(self, data_dir: Optional[Path] = None):
        self.short_term = ShortTermMemory()
        self.long_term = LongTermMemory(data_dir=data_dir)
        self.knowledge = KnowledgeRecall()
        self._booted = False

    def boot(self) -> Dict[str, Any]:
        """Initialize memory system and return status."""
        self._booted = True
        return {
            "short_term": "ready",
            "long_term": repr(self.long_term),
            "knowledge": repr(self.knowledge),
            "long_term_summary": self.long_term.summary(),
            "knowledge_files": self.knowledge.knowledge_files_loaded,
        }

    def on_event(self, event: Any) -> None:
        """
        Process an event and update memory accordingly.
        
        This is the EventStream callback — all events flow through here.
        The memory manager decides what to remember and what to discard.
        """
        # Always store in short-term recent events
        self.short_term.record_event(event)

        # Route by event type
        event_type = getattr(event, "event_type", None)
        if event_type is None:
            return

        type_value = event_type.value if hasattr(event_type, "value") else str(event_type)

        if type_value == "market_scan":
            self._handle_market_scan(event)
        elif type_value == "signal_generated":
            self._handle_signal_generated(event)
        elif type_value == "signal_rejected":
            self._handle_signal_rejected(event)
        elif type_value == "trade_executed":
            self._handle_trade_executed(event)
        elif type_value == "trade_closed":
            self._handle_trade_closed(event)

    def _handle_market_scan(self, event: Any) -> None:
        """Update price memory from scan events."""
        data = getattr(event, "data", {})
        symbol = data.get("symbol", "")
        if symbol:
            bid = getattr(event, "bid", 0) or data.get("bid", 0)
            ask = getattr(event, "ask", 0) or data.get("ask", 0)
            spread = getattr(event, "spread", 0) or data.get("spread", 0)
            self.short_term.update_price(symbol, bid, ask, spread)
            
            # Track killzone
            kz = data.get("killzone") or getattr(event, "killzone", None)
            self.short_term.update_killzone(kz if kz != "none" else None)

    def _handle_signal_generated(self, event: Any) -> None:
        """Record accepted signal in short-term memory."""
        self.short_term.record_signal(SignalMemory(
            symbol=getattr(event, "symbol", ""),
            direction=getattr(event, "direction", ""),
            model=getattr(event, "model", ""),
            confidence=getattr(event, "confidence", 0),
            rr_ratio=getattr(event, "rr_ratio", 0),
            accepted=True,
            entry_price=getattr(event, "entry_price", 0),
            stop_loss=getattr(event, "stop_loss", 0),
            take_profit=getattr(event, "take_profit", 0),
        ))

    def _handle_signal_rejected(self, event: Any) -> None:
        """Record rejected signal with reason."""
        self.short_term.record_signal(SignalMemory(
            symbol=getattr(event, "symbol", ""),
            direction=getattr(event, "direction", ""),
            model=getattr(event, "model", ""),
            confidence=getattr(event, "confidence", 0),
            rr_ratio=getattr(event, "rr_ratio", 0),
            accepted=False,
            rejection_reason=getattr(event, "rejection_reason", "Unknown"),
        ))

    def _handle_trade_executed(self, event: Any) -> None:
        """Record new trade in short-term memory."""
        data = getattr(event, "data", {})
        self.short_term.record_trade(TradeMemory(
            trade_id=data.get("trade_id", str(id(event))),
            symbol=getattr(event, "symbol", ""),
            direction=data.get("direction", ""),
            model=data.get("model", ""),
            entry_price=getattr(event, "entry_price", 0),
            stop_loss=getattr(event, "stop_loss", 0),
            take_profit=getattr(event, "take_profit", 0),
            units=data.get("units", 0),
        ))

    def _handle_trade_closed(self, event: Any) -> None:
        """Record trade close in both short and long term memory."""
        data = getattr(event, "data", {})
        trade_id = data.get("trade_id", "")
        pnl = data.get("pnl", 0)
        close_price = data.get("close_price", 0)

        # Update short-term
        self.short_term.close_trade(trade_id, close_price, pnl)

        # Record lesson in long-term
        outcome = "win" if pnl > 0 else ("breakeven" if pnl == 0 else "loss")
        self.long_term.record_trade_lesson(
            symbol=data.get("symbol", ""),
            model=data.get("model", ""),
            direction=data.get("direction", ""),
            outcome=outcome,
            pnl=pnl,
            lesson=data.get("lesson", f"Trade closed with {outcome}"),
            setup_details=data.get("setup_details"),
        )

        # Update pattern stats
        pattern = f"{data.get('symbol', '')}_{data.get('model', '')}"
        self.long_term.update_pattern_stats(pattern, pnl > 0, pnl)

    # ─── Context Recall ───────────────────────────────────────────────────

    def recall_for_analysis(
        self,
        symbol: str,
        model: Optional[str] = None,
        session: Optional[str] = None,
        bias: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Full contextual recall for an analysis decision.
        
        Combines:
          - Short-term session context (what happened today)
          - Long-term trade lessons (what worked before)
          - Knowledge recall (ICT patterns, trading rules)
          - Golden rules (Ashton's wisdom)
        
        Returns a rich context dict that can be injected into analysis.
        """
        result = {}

        # 1. Short-term context
        result["session"] = self.short_term.to_context()
        result["recent_rejections"] = self.short_term.get_symbol_rejections(symbol)
        last_signal = self.short_term.get_last_signal(symbol)
        if last_signal:
            result["last_signal"] = {
                "direction": last_signal.direction,
                "model": last_signal.model,
                "accepted": last_signal.accepted,
                "reason": last_signal.rejection_reason,
            }

        # 2. Long-term recall
        result["long_term"] = self.long_term.recall_for_setup(
            symbol=symbol,
            model=model or "unknown",
            session=session or "unknown",
        )

        # 3. Knowledge recall
        result["knowledge"] = self.knowledge.recall(
            symbol=symbol,
            model=model,
            session=session,
            bias=bias,
        )

        # 4. Decision aids
        result["should_trade"] = self._should_trade_assessment(symbol, model, result)

        return result

    def _should_trade_assessment(
        self, symbol: str, model: Optional[str], context: Dict
    ) -> Dict[str, Any]:
        """
        Quick assessment: should we take this trade based on memory?
        
        Returns:
          confidence_boost: float (-0.2 to +0.2) adjustment to confidence
          warnings: list of warning strings
          encouragements: list of positive signals
        """
        confidence_boost = 0.0
        warnings = []
        encouragements = []

        lt = context.get("long_term", {})

        # Check session match
        if lt.get("session_match"):
            confidence_boost += 0.05
            encouragements.append(f"Preferred session for {symbol}")
        
        # Check pair win rate
        pair_wr = lt.get("pair_win_rate")
        if pair_wr is not None:
            if pair_wr >= 0.6:
                confidence_boost += 0.05
                encouragements.append(f"Historical win rate {pair_wr*100:.0f}%")
            elif pair_wr < 0.4:
                confidence_boost -= 0.1
                warnings.append(f"Low historical win rate {pair_wr*100:.0f}%")

        # Check pattern win rate
        pattern_wr = lt.get("pattern_win_rate")
        if pattern_wr is not None:
            if pattern_wr >= 0.6:
                confidence_boost += 0.05
            elif pattern_wr < 0.4:
                confidence_boost -= 0.1
                warnings.append(f"Pattern win rate only {pattern_wr*100:.0f}%")

        # Check warnings from pair memory
        pair_warnings = lt.get("pair_warnings", [])
        warnings.extend(pair_warnings)

        # Check daily trade limit proximity
        session = context.get("session", {})
        trades_today = session.get("trades_today", 0)
        if trades_today >= 2:
            warnings.append(f"Already {trades_today} trades today — quality check")
            confidence_boost -= 0.05

        # Check session P&L
        session_pnl = session.get("session_pnl", 0)
        if session_pnl < -200:
            warnings.append(f"Session P&L ${session_pnl:.0f} — avoid revenge trading")
            confidence_boost -= 0.1

        # Recent rejections for this symbol
        rejections = context.get("recent_rejections", [])
        if len(rejections) >= 3:
            warnings.append(f"{len(rejections)} rejections on {symbol} today — market may not be setting up")

        return {
            "confidence_boost": max(-0.2, min(0.2, confidence_boost)),
            "warnings": warnings,
            "encouragements": encouragements,
        }

    def record_trade_outcome(
        self,
        symbol: str,
        model: str,
        direction: str,
        outcome: str,
        pnl: float,
        lesson: str,
        setup_details: Optional[Dict] = None,
    ) -> None:
        """Explicitly record a trade outcome (bypassing events)."""
        self.long_term.record_trade_lesson(
            symbol=symbol,
            model=model,
            direction=direction,
            outcome=outcome,
            pnl=pnl,
            lesson=lesson,
            setup_details=setup_details,
        )
        pattern = f"{symbol}_{model}"
        self.long_term.update_pattern_stats(pattern, pnl > 0, pnl)

    # ─── Reporting ────────────────────────────────────────────────────────

    def session_summary(self) -> Dict[str, Any]:
        """Full session summary for shutdown reporting."""
        return {
            "session": self.short_term.to_context(),
            "long_term": self.long_term.summary(),
            "knowledge_files": self.knowledge.knowledge_files_loaded,
        }

    def get_status(self) -> Dict[str, Any]:
        """Current memory system status."""
        return {
            "booted": self._booted,
            "short_term": {
                "trades": self.short_term.trades_today,
                "signals": len(self.short_term.signals),
                "events": len(self.short_term.recent_events),
                "pnl": self.short_term.session_pnl,
            },
            "long_term": self.long_term.summary(),
            "knowledge": {
                "files": self.knowledge.knowledge_files_loaded,
                "names": self.knowledge.list_knowledge(),
            },
        }

    def __repr__(self) -> str:
        return (
            f"MemoryManager(short={self.short_term}, "
            f"long={self.long_term}, "
            f"knowledge={self.knowledge})"
        )
