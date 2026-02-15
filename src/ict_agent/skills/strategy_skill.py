"""
StrategySkill — Strategy evaluation and rotation based on performance data.

Responsibilities:
  1. Evaluate which models/sessions/symbols are performing best
  2. Recommend strategy adjustments (boost/downweight models)
  3. Forward-test scoring: track paper setups vs actual outcomes
  4. Provide strategy-level confidence modifiers to the analyze phase

Uses: PerformanceTracker, LongTermMemory, KnowledgeManager
"""

import time
from datetime import datetime
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

from ict_agent.skills.base import Skill, SkillResult
from ict_agent.events.event_types import LearningEvent, EventType

NY_TZ = ZoneInfo("America/New_York")

# ─── Strategy Thresholds ──────────────────────────────────────────────────
MIN_TRADES_FOR_STATS = 5       # Need 5+ trades to consider stats reliable
WIN_RATE_BOOST_THRESHOLD = 65  # Above this = boost confidence
WIN_RATE_PENALTY_THRESHOLD = 40  # Below this = reduce confidence
MODEL_COLD_STREAK_LIMIT = 3    # 3+ consecutive losses = flag model
SYMBOL_MAX_DRAWDOWN_PCT = 5.0  # 5% symbol drawdown = halt trading that pair
SESSION_RR_MIN = 1.5           # Minimum avg R:R to keep session active


class StrategySkill(Skill):
    """
    Evaluates strategy performance and recommends adjustments.
    
    Three modes:
      - "evaluate": Full strategy assessment across all dimensions
      - "recommend": Get confidence modifiers for a specific setup
      - "rotate": Suggest which models/symbols/sessions to prioritize
    """

    name = "strategy"
    description = "Strategy evaluation, rotation, and confidence adjustment"
    version = "1.0.0"

    def execute(self, context: Dict[str, Any]) -> SkillResult:
        """
        Execute strategy evaluation.
        
        Context:
            mode: "evaluate" | "recommend" | "rotate" (default: "evaluate")
            performance: PerformanceTracker instance
            long_term_memory: LongTermMemory instance (optional)
            knowledge_manager: KnowledgeManager instance (optional)
            
            For "recommend" mode:
                symbol: str
                model: str
                session: str (killzone name)
                base_confidence: float
        """
        start = time.time()
        mode = context.get("mode", "evaluate")

        if mode == "evaluate":
            return self._evaluate(context, start)
        elif mode == "recommend":
            return self._recommend(context, start)
        elif mode == "rotate":
            return self._rotate(context, start)
        else:
            return SkillResult(
                success=False,
                error=f"Unknown strategy mode: {mode}",
                execution_time_ms=(time.time() - start) * 1000,
            )

    # ─── EVALUATE ─────────────────────────────────────────────────────────

    def _evaluate(self, context: Dict[str, Any], start: float) -> SkillResult:
        """Full strategy evaluation across all dimensions."""
        err = self.validate_context(context, ["performance"])
        if err:
            return SkillResult(success=False, error=err)

        perf = context["performance"]
        status = perf.status()
        events = []

        evaluation = {
            "timestamp": datetime.now(NY_TZ).isoformat(),
            "total_trades": status["total_trades"],
            "overall": self._evaluate_overall(status),
            "by_model": {},
            "by_symbol": {},
            "by_session": {},
            "alerts": [],
            "recommendations": [],
        }

        # Evaluate each model
        for model, stats in status.get("by_model", {}).items():
            model_eval = self._evaluate_bucket(model, stats, "model")
            evaluation["by_model"][model] = model_eval
            if model_eval.get("alerts"):
                evaluation["alerts"].extend(model_eval["alerts"])

        # Evaluate each symbol
        for symbol, stats in status.get("by_symbol", {}).items():
            sym_eval = self._evaluate_bucket(symbol, stats, "symbol")
            evaluation["by_symbol"][symbol] = sym_eval
            if sym_eval.get("alerts"):
                evaluation["alerts"].extend(sym_eval["alerts"])

        # Evaluate each session
        for session, stats in status.get("by_session", {}).items():
            sess_eval = self._evaluate_bucket(session, stats, "session")
            evaluation["by_session"][session] = sess_eval
            if sess_eval.get("alerts"):
                evaluation["alerts"].extend(sess_eval["alerts"])

        # Generate recommendations
        evaluation["recommendations"] = self._generate_recommendations(evaluation)

        # Emit strategy evaluation event
        events.append(LearningEvent(
            event_type=EventType.LESSON_LEARNED,
            source="skill:strategy",
            trade_id="",
            symbol="",
            model="",
            lesson=f"Strategy evaluation: {len(evaluation['alerts'])} alerts, "
                   f"{len(evaluation['recommendations'])} recommendations",
            category="strategy",
            importance=2.0 if evaluation["alerts"] else 1.0,
        ))

        return SkillResult(
            success=True,
            data=evaluation,
            events=events,
            execution_time_ms=(time.time() - start) * 1000,
        )

    def _evaluate_overall(self, status: Dict) -> Dict:
        """Evaluate overall trading health."""
        total = status["total_trades"]
        if total == 0:
            return {
                "grade": "N/A",
                "message": "No trades yet — collecting data",
                "confidence_modifier": 0.0,
            }

        wr = status["win_rate"]
        pf = status["profit_factor"]
        avg_rr = status["avg_rr"]
        dd = status["drawdown"]["max_pct"]

        # Grade: A (excellent) → F (failing)
        score = 0
        if wr >= 60:
            score += 3
        elif wr >= 50:
            score += 2
        elif wr >= 40:
            score += 1

        if pf >= 2.0:
            score += 3
        elif pf >= 1.5:
            score += 2
        elif pf >= 1.0:
            score += 1

        if avg_rr >= 3.0:
            score += 2
        elif avg_rr >= 2.0:
            score += 1

        if dd < 3.0:
            score += 2
        elif dd < 5.0:
            score += 1

        grades = {range(9, 11): "A", range(7, 9): "B", range(5, 7): "C",
                  range(3, 5): "D", range(0, 3): "F"}
        grade = "F"
        for r, g in grades.items():
            if score in r:
                grade = g
                break

        # Confidence modifier: -0.15 to +0.1 based on grade
        modifiers = {"A": 0.1, "B": 0.05, "C": 0.0, "D": -0.05, "F": -0.15}
        modifier = modifiers.get(grade, 0.0)

        return {
            "grade": grade,
            "score": score,
            "win_rate": wr,
            "profit_factor": pf,
            "avg_rr": avg_rr,
            "max_drawdown_pct": dd,
            "confidence_modifier": modifier,
            "message": self._grade_message(grade),
        }

    def _grade_message(self, grade: str) -> str:
        messages = {
            "A": "Excellent performance — maintain discipline, slight confidence boost",
            "B": "Good performance — strategy is working, stay consistent",
            "C": "Average — review losing trades, tighten entry criteria",
            "D": "Below average — reduce position sizes, review model selection",
            "F": "Poor — STOP trading, full strategy review needed",
        }
        return messages.get(grade, "Unknown")

    def _evaluate_bucket(self, name: str, stats: Dict, bucket_type: str) -> Dict:
        """Evaluate a single model/symbol/session bucket."""
        total = stats.get("total", 0)
        evaluation = {
            "name": name,
            "type": bucket_type,
            "total_trades": total,
            "reliable": total >= MIN_TRADES_FOR_STATS,
            "alerts": [],
            "confidence_modifier": 0.0,
        }

        if total < MIN_TRADES_FOR_STATS:
            evaluation["message"] = f"Not enough data ({total}/{MIN_TRADES_FOR_STATS} trades)"
            return evaluation

        wr = stats.get("win_rate", 0)
        pnl = stats.get("pnl_usd", 0)
        avg_rr = stats.get("avg_rr", 0)
        worst = stats.get("worst_trade", 0)

        # Win rate assessment
        if wr >= WIN_RATE_BOOST_THRESHOLD:
            evaluation["confidence_modifier"] = 0.05
            evaluation["status"] = "strong"
        elif wr <= WIN_RATE_PENALTY_THRESHOLD:
            evaluation["confidence_modifier"] = -0.1
            evaluation["status"] = "weak"
            evaluation["alerts"].append(
                f"⚠️ {bucket_type.upper()} {name}: Low win rate ({wr:.1f}%)"
            )
        else:
            evaluation["status"] = "neutral"

        # P&L assessment
        if pnl < 0:
            evaluation["alerts"].append(
                f"📉 {bucket_type.upper()} {name}: Negative P&L (${pnl:+.2f})"
            )
            evaluation["confidence_modifier"] -= 0.05

        # R:R assessment for sessions
        if bucket_type == "session" and avg_rr < SESSION_RR_MIN and total >= MIN_TRADES_FOR_STATS:
            evaluation["alerts"].append(
                f"⚠️ SESSION {name}: Low avg R:R ({avg_rr:.1f}x — min {SESSION_RR_MIN}x)"
            )

        evaluation["win_rate"] = wr
        evaluation["pnl_usd"] = pnl
        evaluation["avg_rr"] = avg_rr
        return evaluation

    # ─── RECOMMEND ────────────────────────────────────────────────────────

    def _recommend(self, context: Dict[str, Any], start: float) -> SkillResult:
        """Get a confidence modifier recommendation for a specific setup."""
        err = self.validate_context(context, ["performance", "symbol", "model"])
        if err:
            return SkillResult(success=False, error=err)

        perf = context["performance"]
        symbol = context["symbol"]
        model = context["model"]
        session = context.get("session", "")
        base_confidence = context.get("base_confidence", 0.5)

        status = perf.status()
        total_modifier = 0.0
        reasons = []

        # Overall modifier
        overall = self._evaluate_overall(status)
        if overall["confidence_modifier"] != 0:
            total_modifier += overall["confidence_modifier"]
            reasons.append(f"Overall {overall['grade']}: {overall['confidence_modifier']:+.2f}")

        # Model modifier
        model_stats = status.get("by_model", {}).get(model, {})
        if model_stats.get("total", 0) >= MIN_TRADES_FOR_STATS:
            model_eval = self._evaluate_bucket(model, model_stats, "model")
            mod = model_eval["confidence_modifier"]
            if mod != 0:
                total_modifier += mod
                reasons.append(f"Model {model}: {mod:+.2f}")

        # Symbol modifier
        sym_stats = status.get("by_symbol", {}).get(symbol, {})
        if sym_stats.get("total", 0) >= MIN_TRADES_FOR_STATS:
            sym_eval = self._evaluate_bucket(symbol, sym_stats, "symbol")
            mod = sym_eval["confidence_modifier"]
            if mod != 0:
                total_modifier += mod
                reasons.append(f"Symbol {symbol}: {mod:+.2f}")

        # Session modifier
        if session:
            sess_stats = status.get("by_session", {}).get(session, {})
            if sess_stats.get("total", 0) >= MIN_TRADES_FOR_STATS:
                sess_eval = self._evaluate_bucket(session, sess_stats, "session")
                mod = sess_eval["confidence_modifier"]
                if mod != 0:
                    total_modifier += mod
                    reasons.append(f"Session {session}: {mod:+.2f}")

        # Check streaks
        streaks = status.get("streaks", {})
        if streaks.get("current_losses", 0) >= MODEL_COLD_STREAK_LIMIT:
            total_modifier -= 0.1
            reasons.append(f"Cold streak ({streaks['current_losses']} losses): -0.10")

        if streaks.get("current_wins", 0) >= 5:
            total_modifier += 0.05
            reasons.append(f"Hot streak ({streaks['current_wins']} wins): +0.05")

        # Clamp total modifier
        total_modifier = max(-0.3, min(0.15, total_modifier))

        adjusted_confidence = max(0.0, min(1.0, base_confidence + total_modifier))

        return SkillResult(
            success=True,
            data={
                "base_confidence": base_confidence,
                "strategy_modifier": round(total_modifier, 3),
                "adjusted_confidence": round(adjusted_confidence, 3),
                "reasons": reasons,
                "overall_grade": overall.get("grade", "N/A"),
            },
            execution_time_ms=(time.time() - start) * 1000,
        )

    # ─── ROTATE ───────────────────────────────────────────────────────────

    def _rotate(self, context: Dict[str, Any], start: float) -> SkillResult:
        """Suggest strategy rotation: which models/symbols/sessions to prioritize."""
        err = self.validate_context(context, ["performance"])
        if err:
            return SkillResult(success=False, error=err)

        perf = context["performance"]
        status = perf.status()

        rotation = {
            "timestamp": datetime.now(NY_TZ).isoformat(),
            "prioritize_models": [],
            "avoid_models": [],
            "prioritize_symbols": [],
            "avoid_symbols": [],
            "prioritize_sessions": [],
            "avoid_sessions": [],
        }

        # Rank models
        for model, stats in status.get("by_model", {}).items():
            if stats.get("total", 0) >= MIN_TRADES_FOR_STATS:
                wr = stats.get("win_rate", 0)
                if wr >= WIN_RATE_BOOST_THRESHOLD:
                    rotation["prioritize_models"].append({
                        "model": model, "win_rate": wr, "trades": stats["total"],
                        "pnl": stats.get("pnl_usd", 0),
                    })
                elif wr <= WIN_RATE_PENALTY_THRESHOLD:
                    rotation["avoid_models"].append({
                        "model": model, "win_rate": wr, "trades": stats["total"],
                        "pnl": stats.get("pnl_usd", 0),
                    })

        # Rank symbols
        for symbol, stats in status.get("by_symbol", {}).items():
            if stats.get("total", 0) >= MIN_TRADES_FOR_STATS:
                wr = stats.get("win_rate", 0)
                if wr >= WIN_RATE_BOOST_THRESHOLD:
                    rotation["prioritize_symbols"].append({
                        "symbol": symbol, "win_rate": wr, "trades": stats["total"],
                    })
                elif wr <= WIN_RATE_PENALTY_THRESHOLD:
                    rotation["avoid_symbols"].append({
                        "symbol": symbol, "win_rate": wr, "trades": stats["total"],
                    })

        # Rank sessions
        for session, stats in status.get("by_session", {}).items():
            if stats.get("total", 0) >= MIN_TRADES_FOR_STATS:
                wr = stats.get("win_rate", 0)
                avg_rr = stats.get("avg_rr", 0)
                if wr >= WIN_RATE_BOOST_THRESHOLD and avg_rr >= SESSION_RR_MIN:
                    rotation["prioritize_sessions"].append({
                        "session": session, "win_rate": wr, "avg_rr": avg_rr,
                    })
                elif wr <= WIN_RATE_PENALTY_THRESHOLD:
                    rotation["avoid_sessions"].append({
                        "session": session, "win_rate": wr, "avg_rr": avg_rr,
                    })

        # Sort by win rate
        for key in ["prioritize_models", "prioritize_symbols", "prioritize_sessions"]:
            rotation[key] = sorted(rotation[key], key=lambda x: x.get("win_rate", 0), reverse=True)

        return SkillResult(
            success=True,
            data=rotation,
            execution_time_ms=(time.time() - start) * 1000,
        )

    # ─── HELPERS ──────────────────────────────────────────────────────────

    def _generate_recommendations(self, evaluation: Dict) -> List[str]:
        """Generate actionable recommendations from evaluation."""
        recs = []
        overall = evaluation.get("overall", {})
        grade = overall.get("grade", "N/A")

        if grade == "F":
            recs.append("🛑 STOP: Cease live trading. Conduct full strategy review.")
            recs.append("📊 Review last 10 losses — identify common mistakes.")
        elif grade == "D":
            recs.append("⚠️ Reduce position sizes by 50% until win rate improves.")
            recs.append("🔬 Focus on highest-confidence setups only (>70%).")

        # Model-specific recommendations
        for model, data in evaluation.get("by_model", {}).items():
            if data.get("status") == "weak" and data.get("reliable"):
                recs.append(f"📉 Downweight {model} — consider removing from rotation.")
            elif data.get("status") == "strong" and data.get("reliable"):
                recs.append(f"📈 {model} performing well — maintain or slightly increase allocation.")

        # Symbol-specific
        for symbol, data in evaluation.get("by_symbol", {}).items():
            if data.get("pnl_usd", 0) < -100 and data.get("reliable"):
                recs.append(f"🚫 Consider removing {symbol} — net negative P&L.")

        if not recs:
            if grade in ("A", "B"):
                recs.append("✅ Strategy performing well. Maintain current approach.")
            elif grade == "N/A":
                recs.append("📊 Collecting data. Continue trading per the plan.")

        return recs
