"""
AnalyzeSkill — Deep analysis of a symbol using VexCoreEngine.
Wraps: VexCoreEngine, OANDAFetcher (for OHLC data)
"""

import time
from typing import Any, Dict
from datetime import datetime
from zoneinfo import ZoneInfo

from ict_agent.skills.base import Skill, SkillResult
from ict_agent.events.event_types import SignalEvent, EventType

NY_TZ = ZoneInfo("America/New_York")


class AnalyzeSkill(Skill):
    name = "analyze"
    description = "Deep ICT analysis of a symbol using VexCoreEngine (8-gate system)"
    version = "1.0.0"

    def execute(self, context: Dict[str, Any]) -> SkillResult:
        """
        Analyze a symbol through VexCoreEngine's 8-gate system.

        Context:
            symbol: str — pair to analyze
            engine: VexCoreEngine instance

        Returns:
            SkillResult with EngineResult data and signal events.
        """
        start = time.time()
        err = self.validate_context(context, ["symbol", "engine"])
        if err:
            return SkillResult(success=False, error=err)

        symbol = context["symbol"]
        engine = context["engine"]
        killzone_override = context.get("killzone_override")
        events = []

        try:
            from ict_agent.data.oanda_fetcher import get_oanda_data
            from ict_agent.learning.knowledge_manager import KnowledgeManager

            # Initialize Knowledge Manager (The Brain)
            km = context.get("knowledge_manager") or KnowledgeManager()

            # Get market data
            df_15m = get_oanda_data(symbol, timeframe="M15", count=200)
            df_1h = get_oanda_data(symbol, timeframe="H1", count=100)

            if df_15m is None or df_15m.empty:
                return SkillResult(
                    success=False,
                    error=f"No data returned for {symbol}",
                    execution_time_ms=(time.time() - start) * 1000,
                )

            # Run the 8-gate analysis — pass killzone_override if controller already validated
            result = engine.analyze(
                symbol,
                df_15m,
                df_1h,
                timeframe="15m",
                killzone_override=killzone_override,
            )

            # Serialize gate trace for downstream consumers (controller, dashboard)
            gate_trace_data = [
                {
                    "gate": g.gate,
                    "passed": g.passed,
                    "summary": g.summary,
                    "details": g.details,
                }
                for g in (result.gate_trace or [])
            ]

            if result.trade and result.setup:
                setup = result.setup

                # === KNOWLEDGE GRAPH VALIDATION ===
                # Ask the brain if this setup makes sense
                validation = km.validate_setup(
                    confluences=setup.confluences,
                    model=setup.model.value,
                    session=setup.killzone,
                )

                if not validation["valid"]:
                    # REJECTED BY BRAIN
                    rejection_reason = f"Knowledge Check Failed: {', '.join(validation['missing'] + validation['anti_patterns'])}"
                    events.append(
                        SignalEvent(
                            event_type=EventType.SIGNAL_REJECTED,
                            source="skill:analyze",
                            symbol=symbol,
                            rejection_reason=rejection_reason,
                            metadata={"warnings": validation["warnings"]},
                        )
                    )
                    return SkillResult(
                        success=True,
                        data={
                            "trade": False,
                            "symbol": symbol,
                            "rejection_reason": rejection_reason,
                            "knowledge_validation": validation,
                            "gate_trace": gate_trace_data,
                        },
                        events=events,
                        execution_time_ms=(time.time() - start) * 1000,
                    )

                # ACCEPTED
                direction = "SELL" if setup.bias.value == "bearish" else "BUY"

                # Apply memory-based confidence adjustment
                confidence_boost = context.get("confidence_boost", 0)
                adjusted_confidence = max(
                    0.0, min(1.0, setup.confidence + confidence_boost)
                )

                signal_event = SignalEvent(
                    event_type=EventType.SIGNAL_GENERATED,
                    source="skill:analyze",
                    symbol=symbol,
                    direction=direction,
                    model=setup.model.value,
                    trade_type=setup.trade_type.value,
                    entry_price=setup.entry_price,
                    stop_loss=setup.stop_loss,
                    take_profit=setup.target_1,
                    confidence=adjusted_confidence,
                    rr_ratio=setup.rr_ratio,
                    confluences=setup.confluences,
                    metadata={
                        "knowledge_score": validation["score"],
                        "knowledge_warnings": validation["warnings"],
                        "learned_adjustment": validation.get("learned_adjustment", 0),
                        "memory_confidence_boost": confidence_boost,
                    },
                )
                events.append(signal_event)

                return SkillResult(
                    success=True,
                    data={
                        "trade": True,
                        "symbol": symbol,
                        "direction": direction,
                        "model": setup.model.value,
                        "trade_type": setup.trade_type.value,
                        "entry_price": setup.entry_price,
                        "stop_loss": setup.stop_loss,
                        "target_1": setup.target_1,
                        "target_2": setup.target_2,
                        "risk_pips": setup.risk_pips,
                        "reward_pips": setup.reward_pips,
                        "rr_ratio": setup.rr_ratio,
                        "confidence": adjusted_confidence,
                        "raw_confidence": setup.confidence,
                        "confidence_boost": confidence_boost,
                        "confluences": setup.confluences,
                        "confluence_score": validation["score"],  # Use Knowledge Score!
                        "killzone": setup.killzone,
                        "session_phase": setup.session_phase.value,
                        "bias": setup.bias.value,
                        "entry_reason": setup.entry_reason,
                        "setup_dict": setup.to_dict(),
                        "knowledge_validation": validation,
                        "gate_trace": gate_trace_data,
                    },
                    events=events,
                    execution_time_ms=(time.time() - start) * 1000,
                )
            else:
                # No trade — record rejection
                events.append(
                    SignalEvent(
                        event_type=EventType.SIGNAL_REJECTED,
                        source="skill:analyze",
                        symbol=symbol,
                        rejection_reason=result.rejection_reason or "No setup found",
                    )
                )

                return SkillResult(
                    success=True,  # Analysis succeeded, just no trade
                    data={
                        "trade": False,
                        "symbol": symbol,
                        "bias": result.bias.value,
                        "session_phase": result.session_phase.value,
                        "killzone_active": result.killzone_active,
                        "rejection_reason": result.rejection_reason,
                        "liquidity_count": len(result.liquidity_levels),
                        "pd_array_count": len(result.pd_arrays),
                        "gate_trace": gate_trace_data,
                    },
                    events=events,
                    execution_time_ms=(time.time() - start) * 1000,
                )

        except Exception as e:
            return SkillResult(
                success=False,
                error=f"Analysis failed for {symbol}: {e}",
                execution_time_ms=(time.time() - start) * 1000,
            )
