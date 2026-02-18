"""
VEX Graph Reasoner Bridge
==========================
Bridges the GraphRAG TradeReasoner into VEX's data structures.

This module translates VEX's detector outputs (PDArrays, LiquidityLevels,
sweep_info, bias, session state) into the signal dict format expected by
TradeReasoner, and converts the resulting TradeDecision back into VEX's
ModelType, confluence list, and confidence score.

Usage (inside VexCoreEngine):
    from ict_agent.core.graph_reasoner import VexGraphReasoner

    reasoner = VexGraphReasoner()  # loads graph store on init
    enhanced = reasoner.enhance_setup(
        bias=bias,
        session_phase=session_phase,
        trade_type=trade_type,
        sweep_info=sweep_info,
        pd_arrays=valid_entries,
        killzone_name=killzone_name,
        displacement_detected=True,
    )
    # enhanced.model  -> ModelType or None
    # enhanced.confluences -> list[str]
    # enhanced.confluence_score -> int
    # enhanced.confidence -> float
    # enhanced.go_no_go -> bool
    # enhanced.decision -> TradeDecision (full object)
"""

from __future__ import annotations

import logging
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .vex_core_engine import (
    Bias,
    LiquidityLevel,
    ModelType,
    PDArray,
    SessionPhase,
    TradeType,
)
from ict_agent.logic.reasoner import GraphReasoner, TradeDecision
from ict_agent.knowledge.schema import ICTGraphInternal

logger = logging.getLogger(__name__)

# ── Model name mapping: TradeReasoner names ↔ VEX ModelType ──────────────────

_REASONER_TO_VEX_MODEL: Dict[str, ModelType] = {
    "silver_bullet": ModelType.MODEL_11,
    "ict_2022": ModelType.STANDARD,
    "unicorn": ModelType.MODEL_12,
    "turtle_soup": ModelType.TURTLE_SOUP,
    "judas_swing": ModelType.STANDARD,
    "model_11": ModelType.MODEL_11,
    "model_12": ModelType.MODEL_12,
    "standard": ModelType.STANDARD,
}

_VEX_MODEL_TO_REASONER: Dict[ModelType, str] = {
    ModelType.MODEL_11: "silver_bullet",
    ModelType.MODEL_12: "unicorn",
    ModelType.TURTLE_SOUP: "turtle_soup",
    ModelType.STANDARD: "ict_2022",
}


@dataclass
class EnhancedResult:
    """Result from the graph reasoner bridge, ready for VEX consumption."""

    # Drop-in replacements for VEX's existing values
    model: Optional[ModelType] = None
    confluences: List[str] = field(default_factory=list)
    confluence_score: int = 0
    confidence: float = 0.0
    go_no_go: bool = False

    # Extra graph-derived data
    recommended_model_name: Optional[str] = None
    score_raw: float = 0.0
    red_flags: List[str] = field(default_factory=list)
    missing: List[str] = field(default_factory=list)
    explanation: List[str] = field(default_factory=list)

    # Full decision object (for logging / journaling)
    decision: object = None  # TradeDecision


class VexGraphReasoner:
    """Adapts the GraphRAG Reasoner to work with VEX's dataclasses.

    Initialisation is intentionally lazy — the heavy graph store is only
    loaded the first time ``enhance_setup`` is called.  This keeps VEX's
    boot time unaffected if the graph files are missing.
    """

    def __init__(self):
        self._reasoner = None
        self._loaded = False
        self._available = True

    # ── Lazy loading ──────────────────────────────────────────────────────

    def _ensure_loaded(self) -> bool:
        """Lazy-load the graph store + reasoner on first use."""
        if self._loaded:
            return self._available

        try:
            # Locate Knowledge Base
            # Default: ../../knowledge_base relative to src/ict_agent/core
            current_dir = Path(__file__).parent.resolve()
            kb_root = current_dir.parent.parent.parent / "knowledge_base"

            if not kb_root.exists():
                # Try env var
                env_root = os.environ.get("TRAIN_ICT_ROOT")
                if env_root:
                    kb_root = Path(env_root) / "knowledge_base"

            if not kb_root.exists():
                logger.warning(f"Knowledge Base not found at {kb_root}")
                self._available = False
                self._loaded = True
                return False

            self._reasoner = GraphReasoner.from_knowledge_base(kb_root)
            self._loaded = True
            self._available = True

            node_count = len(self._reasoner.graph.nodes)
            logger.info(f"GraphReasoner loaded: {node_count} nodes")

        except Exception as exc:
            logger.warning("GraphReasoner unavailable: %s", exc)
            self._loaded = True
            self._available = False

        return self._available

    # ── Public API ────────────────────────────────────────────────────────

    def enhance_setup(
        self,
        *,
        bias: Bias,
        session_phase: SessionPhase,
        trade_type: TradeType,
        sweep_info: Dict,
        pd_arrays: List[PDArray],
        killzone_name: str = "",
        displacement_detected: bool = False,
        smt_divergence: bool = False,
        current_time: str = "",
        trades_today: int = 0,
        news_imminent: bool = False,
        stop_loss_defined: bool = True,
        multi_tf_aligned: bool = False,
    ) -> EnhancedResult:
        """Translate VEX state into a TradeReasoner signal dict, evaluate,
        and return an ``EnhancedResult`` that VEX can consume directly.

        If the graph reasoner is not available (missing files, import error),
        returns a neutral ``EnhancedResult`` with ``go_no_go=True`` so the
        existing VEX logic continues unimpeded.
        """
        if not self._ensure_loaded():
            # Graceful fallback — let VEX's own logic decide
            return EnhancedResult(
                go_no_go=True, explanation=["graph_rag unavailable — passthrough"]
            )

        # ── Build signal dict ────────────────────────────────────────────
        signals = self._translate_signals(
            bias=bias,
            session_phase=session_phase,
            trade_type=trade_type,
            sweep_info=sweep_info,
            pd_arrays=pd_arrays,
            killzone_name=killzone_name,
            displacement_detected=displacement_detected,
            smt_divergence=smt_divergence,
            current_time=current_time,
            trades_today=trades_today,
            news_imminent=news_imminent,
            stop_loss_defined=stop_loss_defined,
            multi_tf_aligned=multi_tf_aligned,
        )

        # ── Evaluate ─────────────────────────────────────────────────────
        decision = self._reasoner.evaluate(signals)

        # ── Convert back to VEX types ────────────────────────────────────
        return self._translate_decision(decision, pd_arrays)

    # ── Signal translation (VEX → TradeReasoner) ─────────────────────────

    def _translate_signals(
        self,
        *,
        bias: Bias,
        session_phase: SessionPhase,
        trade_type: TradeType,
        sweep_info: Dict,
        pd_arrays: List[PDArray],
        killzone_name: str,
        displacement_detected: bool,
        smt_divergence: bool,
        current_time: str,
        trades_today: int,
        news_imminent: bool,
        stop_loss_defined: bool,
        multi_tf_aligned: bool,
    ) -> Dict:
        """Map VEX's typed data structures into the flat signal dict
        that ``TradeReasoner.evaluate()`` expects."""

        # Pattern list — derived from pd_arrays + sweep + displacement
        patterns: List[str] = []

        has_fvg = any(p.type == "fvg" for p in pd_arrays)
        has_ob = any(p.type == "ob" for p in pd_arrays)
        has_breaker = any(p.type == "breaker" for p in pd_arrays)
        has_void = any(p.type == "void" for p in pd_arrays)

        if has_fvg:
            patterns.append("fvg")
        if has_ob:
            patterns.append("order_block")
        if has_breaker:
            patterns.append("breaker_block")
        if has_void:
            patterns.append("volume_imbalance")
        if displacement_detected:
            patterns.append("displacement")
        if sweep_info.get("occurred"):
            patterns.append("liquidity_sweep")

        # Session mapping
        session_map = {
            "london_open": "london",
            "london": "london",
            "ny_am": "ny_am",
            "new_york_am": "ny_am",
            "ny_pm": "ny_pm",
            "new_york_pm": "ny_pm",
            "asia": "asia",
            "asian": "asia",
        }
        session = (
            session_map.get(killzone_name.lower(), killzone_name.lower())
            if killzone_name
            else ""
        )

        # Determine if killzone
        in_killzone = session in ("london", "ny_am", "ny_pm")

        # Trade direction for red-flag cross-check
        trade_direction = None
        if bias == Bias.BULLISH:
            trade_direction = "bullish"
        elif bias == Bias.BEARISH:
            trade_direction = "bearish"

        # Check if at OTE (any pd_array with valid OTE level)
        at_ote = any(p.ote_level and p.valid and not p.mitigated for p in pd_arrays)

        return {
            "patterns": patterns,
            "htf_bias": bias.value,  # "bullish" / "bearish" / "neutral"
            "htf_aligned": bias in (Bias.BULLISH, Bias.BEARISH),
            "session": session,
            "time": current_time,
            "in_killzone": in_killzone,
            "displacement": displacement_detected,
            "liquidity_swept": sweep_info.get("occurred", False),
            "smt_divergence": smt_divergence,
            "at_ote": at_ote,
            "multi_tf_aligned": multi_tf_aligned,
            "trade_direction": trade_direction,
            "trades_today": trades_today,
            "news_imminent": news_imminent,
            "stop_loss_defined": stop_loss_defined,
            "revenge_trading": False,  # VEX doesn't track this yet
        }

    # ── Decision translation (TradeDecision → EnhancedResult) ────────────

    def _translate_decision(
        self,
        decision,  # TradeDecision
        pd_arrays: List[PDArray],
    ) -> EnhancedResult:
        """Convert the TradeReasoner's TradeDecision into VEX-native types."""

        # Map the recommended model name to VEX's ModelType enum
        vex_model: Optional[ModelType] = None
        if decision.recommendation:
            rec_lower = (
                decision.recommendation.lower().replace(" ", "_").replace("-", "_")
            )
            vex_model = _REASONER_TO_VEX_MODEL.get(rec_lower)
            if vex_model is None:
                # Try partial matching
                for key, mt in _REASONER_TO_VEX_MODEL.items():
                    if key in rec_lower or rec_lower in key:
                        vex_model = mt
                        break

        # Build VEX-style confluence list from graph decision
        confluences: List[str] = []

        for factor, weight in decision.confluence_factors.items():
            if weight > 0:
                confluences.append(f"✅ Graph: {factor} (+{weight})")
            else:
                confluences.append(f"⚠️ Graph: {factor} ({weight})")

        for flag in decision.red_flags:
            confluences.append(f"🚫 Red flag: {flag}")

        if decision.recommendation:
            confluences.append(
                f"✅ Graph model: {decision.recommendation} "
                f"(fit: {decision.model_scores.get(decision.recommendation, 0):.1f})"
            )

        # Score → integer confluence count for VEX compatibility
        positive_count = len([c for c in confluences if c.startswith("✅")])

        # Confidence: blend graph score with simple count
        # Graph score is 0-10+, normalize to 0-1
        graph_confidence = min(1.0, decision.score / 10.0)

        return EnhancedResult(
            model=vex_model,
            confluences=confluences,
            confluence_score=positive_count,
            confidence=graph_confidence,
            go_no_go=decision.go_no_go,
            recommended_model_name=decision.recommendation,
            score_raw=decision.score,
            red_flags=list(decision.red_flags),
            missing=list(decision.missing_prerequisites),
            explanation=list(decision.explanation),
            decision=decision,
        )

    # ── Convenience: full decision summary for logging ────────────────────

    def summary(self, result: EnhancedResult) -> str:
        """Human-readable summary suitable for VEX controller logs."""
        if not result.decision:
            return "GraphReasoner: no decision available"

        status = "GO" if result.go_no_go else "NO-GO"
        model = result.recommended_model_name or "None"
        lines = [
            f"GraphReasoner: {status} | Model: {model} | "
            f"Score: {result.score_raw:.1f} | Confidence: {result.confidence:.0%}",
        ]
        if result.red_flags:
            lines.append(f"  Red flags: {', '.join(result.red_flags)}")
        if result.missing:
            lines.append(f"  Missing: {', '.join(result.missing[:3])}")
        return "\n".join(lines)
