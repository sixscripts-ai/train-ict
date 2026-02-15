"""
LearnSkill — Learns from trade outcomes.
Wraps: TradeLearner, KnowledgeManager
"""

import time
from typing import Any, Dict, List
from datetime import datetime
from zoneinfo import ZoneInfo

from ict_agent.skills.base import Skill, SkillResult
from ict_agent.events.event_types import LearningEvent, EventType

NY_TZ = ZoneInfo("America/New_York")


class LearnSkill(Skill):
    name = "learn"
    description = "Learn from trade outcomes — extract lessons, update patterns, generate insights"
    version = "1.0.0"

    def execute(self, context: Dict[str, Any]) -> SkillResult:
        """
        Learn from a completed trade.
        
        Context:
            trade_learner: TradeLearner instance
            trade_data: dict with trade outcome data:
                - trade_id, symbol, model, outcome (win/loss/breakeven)
                - pnl, rr_achieved, killzone, confluences
                - entry_price, exit_price, stop_loss, take_profit
                
        Returns:
            SkillResult with lessons learned and pattern updates.
        """
        start = time.time()
        err = self.validate_context(context, ["trade_learner", "trade_data"])
        if err:
            return SkillResult(success=False, error=err)

        learner = context["trade_learner"]
        trade = context["trade_data"]
        events = []

        trade_id = trade.get("trade_id", "")
        symbol = trade.get("symbol", "")
        model = trade.get("model", "unknown")
        outcome = trade.get("outcome", "")
        pnl = trade.get("pnl", 0.0)
        rr_achieved = trade.get("rr_achieved", 0.0)
        killzone = trade.get("killzone", "")
        confluences = trade.get("confluences", [])

        try:
            # 1. Learn from the trade
            lesson_result = learner.learn_from_trade(
                trade_id=trade_id,
                symbol=symbol,
                model=model,
                outcome=outcome,
                pnl=pnl,
                rr_achieved=rr_achieved,
                killzone=killzone,
                confluences=confluences,
                entry_price=trade.get("entry_price", 0),
                exit_price=trade.get("exit_price", 0),
                stop_loss=trade.get("stop_loss", 0),
                take_profit=trade.get("take_profit", 0),
            )

            # Extract the lesson text
            lesson_text = ""
            category = "general"
            if lesson_result and isinstance(lesson_result, dict):
                lesson_text = lesson_result.get("lesson", "")
                category = lesson_result.get("category", "general")
            elif lesson_result and isinstance(lesson_result, str):
                lesson_text = lesson_result

            events.append(LearningEvent(
                event_type=EventType.LESSON_LEARNED,
                source="skill:learn",
                trade_id=trade_id,
                symbol=symbol,
                model=model,
                lesson=lesson_text,
                category=category,
                importance=2.0 if outcome == "loss" else 1.0,  # Losses teach more
            ))

            # 2. Get updated pattern stats
            pattern_name = f"{symbol}_{model}"
            pattern_stats = None
            if hasattr(learner, "patterns") and pattern_name in learner.patterns:
                ps = learner.patterns[pattern_name]
                pattern_stats = {
                    "pattern_name": pattern_name,
                    "total_trades": ps.total_trades,
                    "win_rate": round(ps.win_rate * 100, 1),
                    "avg_rr": round(ps.avg_rr, 2),
                    "total_pnl": round(ps.total_pnl, 2),
                }
                events.append(LearningEvent(
                    event_type=EventType.PATTERN_UPDATE,
                    source="skill:learn",
                    pattern_name=pattern_name,
                    win_rate=ps.win_rate,
                ))

            # 3. Check for insights (e.g. "This model has 80%+ win rate in NY AM")
            insights = []
            if hasattr(learner, "generate_insights"):
                try:
                    insights = learner.generate_insights()
                except Exception:
                    pass

            for insight in insights:
                events.append(LearningEvent(
                    event_type=EventType.INSIGHT_GENERATED,
                    source="skill:learn",
                    insight=str(insight),
                ))

            # 4. Pre-trade recall (for next time)
            recall = {}
            if hasattr(learner, "recall_for_setup"):
                try:
                    recall = learner.recall_for_setup(
                        symbol=symbol,
                        model=model,
                        killzone=killzone,
                    )
                except Exception:
                    pass

            return SkillResult(
                success=True,
                data={
                    "trade_id": trade_id,
                    "symbol": symbol,
                    "model": model,
                    "outcome": outcome,
                    "lesson": lesson_text,
                    "category": category,
                    "pattern_stats": pattern_stats,
                    "insights_count": len(insights),
                    "recall": recall,
                },
                events=events,
                execution_time_ms=(time.time() - start) * 1000,
            )

        except Exception as e:
            return SkillResult(
                success=False,
                error=f"Learning failed: {e}",
                execution_time_ms=(time.time() - start) * 1000,
            )

    def pre_trade_check(self, context: Dict[str, Any]) -> SkillResult:
        """
        Before taking a trade, recall what we know about this setup.
        
        Context:
            trade_learner: TradeLearner instance
            symbol: str
            model: str
            killzone: str
        """
        start = time.time()
        learner = context.get("trade_learner")
        if not learner:
            return SkillResult(success=False, error="No trade_learner in context")

        symbol = context.get("symbol", "")
        model = context.get("model", "")
        killzone = context.get("killzone", "")

        recall = {}
        warnings = []

        # Check pattern stats
        pattern_name = f"{symbol}_{model}"
        if hasattr(learner, "patterns") and pattern_name in learner.patterns:
            ps = learner.patterns[pattern_name]
            recall["pattern"] = {
                "total_trades": ps.total_trades,
                "win_rate": round(ps.win_rate * 100, 1),
                "avg_rr": round(ps.avg_rr, 2),
            }

            # Warn if pattern has low win rate
            if ps.total_trades >= 5 and ps.win_rate < 0.4:
                warnings.append(
                    f"⚠️ {pattern_name} has only {ps.win_rate*100:.0f}% win rate "
                    f"over {ps.total_trades} trades"
                )

        # Check recent lessons for this symbol
        if hasattr(learner, "lessons"):
            recent = [
                l for l in learner.lessons[-20:]
                if l.symbol == symbol
            ]
            if recent:
                last_lesson = recent[-1]
                recall["last_lesson"] = {
                    "lesson": last_lesson.lesson,
                    "outcome": last_lesson.outcome,
                    "when": last_lesson.timestamp,
                }

        # Check memory for pair-specific notes
        if hasattr(learner, "memory") and symbol in learner.memory.get("pair_specific", {}):
            notes = learner.memory["pair_specific"][symbol]
            recall["memory_notes"] = notes
            if isinstance(notes, dict) and notes.get("caution"):
                warnings.append(f"⚠️ Memory caution for {symbol}: {notes['caution']}")

        return SkillResult(
            success=True,
            data={
                "symbol": symbol,
                "model": model,
                "recall": recall,
                "warnings": warnings,
                "has_history": bool(recall),
            },
            execution_time_ms=(time.time() - start) * 1000,
        )
