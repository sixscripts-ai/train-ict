#!/usr/bin/env python3
"""
VEX CORE ENGINE
===============
The unified ICT trading system combining:
- IRL → ERL Framework (The Decoder Key)
- Model 11/12 Quick Scalping
- PO3 Session-Based AMD Tracking

Every trade is classified as either:
  TYPE A: Internal Range Liquidity → External Range Liquidity
  TYPE B: External Range Liquidity → Internal Range Liquidity (Turtle Soup)

Created: January 15, 2026
Author: VEX (ICT Trading AI Agent)
"""

import sys
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Tuple, Any
from datetime import datetime, time
from enum import Enum
from zoneinfo import ZoneInfo

import pandas as pd
import numpy as np

# Ensure imports work
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from ict_agent.engine.killzone import KillzoneManager
from ict_agent.engine.asian_range import AsianRangeCalculator
from ict_agent.engine.cbdr import CBDRCalculator
from ict_agent.detectors.fvg import FVGDetector
from ict_agent.detectors.order_block import OrderBlockDetector
from ict_agent.detectors.market_structure import MarketStructureAnalyzer
from ict_agent.detectors.liquidity import LiquidityDetector
from ict_agent.detectors.displacement import DisplacementDetector


NY_TZ = ZoneInfo("America/New_York")


# =============================================================================
# ENUMS & DATA CLASSES
# =============================================================================


class TradeType(Enum):
    """The two types of ICT trades - The Decoder Key"""

    IRL_TO_ERL = "irl_to_erl"  # Internal → External (standard)
    ERL_TO_IRL = "erl_to_irl"  # External → Internal (turtle soup)


class SessionPhase(Enum):
    """Power of Three session phases"""

    ACCUMULATION = "accumulation"  # Asia - range building
    MANIPULATION = "manipulation"  # London - Judas swing
    DISTRIBUTION = "distribution"  # NY - true move
    UNKNOWN = "unknown"


class ModelType(Enum):
    """ICT Model being executed"""

    MODEL_11 = "model_11"  # 30 pip bread & butter
    MODEL_12 = "model_12"  # 20 pip OB+FVG scalp
    TURTLE_SOUP = "turtle_soup"  # Fade the sweep
    STANDARD = "standard"  # Generic IRL→ERL


class Bias(Enum):
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"


@dataclass
class LiquidityLevel:
    """Represents a liquidity pool"""

    price: float
    type: str  # "bsl" (buy-side) or "ssl" (sell-side)
    source: str  # "equal_highs", "equal_lows", "pdh", "pdl", "asia_high", etc.
    external: bool  # True = ERL, False = IRL
    swept: bool = False
    swept_time: Optional[datetime] = None


@dataclass
class PDArray:
    """Premium/Discount Array (entry zone)"""

    type: str  # "fvg", "ob", "breaker", "void"
    direction: str  # "bullish" or "bearish"
    top: float
    bottom: float
    midpoint: float
    ote_level: float  # 70.5% level
    timeframe: str
    valid: bool = True
    mitigated: bool = False


@dataclass
class SessionState:
    """Current PO3 session state"""

    phase: SessionPhase
    asia_high: Optional[float] = None
    asia_low: Optional[float] = None
    asia_swept: Optional[str] = None  # "high", "low", or None
    judas_direction: Optional[str] = None  # Direction of manipulation
    true_direction: Optional[str] = None  # Expected distribution direction


@dataclass
class GateLog:
    """Structured log entry for a single gate in the analysis pipeline."""

    gate: str  # e.g. "G1_KILLZONE"
    passed: bool  # Did analysis continue past this gate?
    summary: str  # One-line human summary
    details: Dict[str, Any] = field(default_factory=dict)  # Structured data


@dataclass
class TradeSetup:
    """A complete trade setup from VEX Core Engine"""

    # Classification
    trade_type: TradeType
    model: ModelType

    # Bias & Context
    bias: Bias
    session_phase: SessionPhase
    killzone: str

    # Entry
    entry_price: float
    entry_zone: PDArray
    entry_reason: str

    # Risk Management
    stop_loss: float
    stop_reason: str

    # Targets
    target_1: float
    target_2: Optional[float]
    target_type: str  # "erl" or "irl"
    target_liquidity: LiquidityLevel

    # Metrics
    risk_pips: float
    reward_pips: float
    rr_ratio: float

    # Confluence
    confluences: List[str]
    confluence_score: int
    confidence: float  # 0-1

    # Meta
    symbol: str
    timeframe: str
    timestamp: datetime

    def to_dict(self) -> Dict:
        return {
            "trade_type": self.trade_type.value,
            "model": self.model.value,
            "bias": self.bias.value,
            "session_phase": self.session_phase.value,
            "killzone": self.killzone,
            "entry_price": self.entry_price,
            "stop_loss": self.stop_loss,
            "target_1": self.target_1,
            "target_2": self.target_2,
            "risk_pips": self.risk_pips,
            "reward_pips": self.reward_pips,
            "rr_ratio": self.rr_ratio,
            "confluences": self.confluences,
            "confluence_score": self.confluence_score,
            "confidence": self.confidence,
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class EngineResult:
    """Result from VEX Core Engine analysis"""

    # Decision
    trade: bool
    setup: Optional[TradeSetup]

    # Context
    bias: Bias
    session_phase: SessionPhase
    killzone_active: bool

    # Analysis Details
    liquidity_levels: List[LiquidityLevel]
    pd_arrays: List[PDArray]
    session_state: SessionState

    # Rejection Reason (if no trade)
    rejection_reason: Optional[str] = None

    # Gate trace — structured log of every gate decision
    gate_trace: List[GateLog] = field(default_factory=list)

    # Raw Data
    analysis_time: datetime = field(default_factory=lambda: datetime.now(NY_TZ))


# =============================================================================
# VEX CORE ENGINE
# =============================================================================


class VexCoreEngine:
    """
    The unified ICT trading system.

    Combines:
    - IRL → ERL Framework (decoder key for ALL ICT trades)
    - Model 11/12 Quick Scalping (bread & butter)
    - PO3 Session Engine (AMD tracking)

    Every trade must pass through gates:
    1. Killzone Check
    2. Session Phase (PO3)
    3. Bias Determination
    4. Liquidity Mapping (IRL vs ERL)
    5. Sweep Detection
    6. PD Array Entry Zone
    7. Trade Classification (Type A or B)
    8. Model Selection (11, 12, or Turtle Soup)
    """

    def __init__(
        self,
        model_11_target: float = 30.0,  # pips
        model_12_target: float = 20.0,  # pips
        default_stop: float = 20.0,  # pips
        min_rr: float = 1.5,
        pip_size: float = 0.0001,
    ):
        self.model_11_target = model_11_target
        self.model_12_target = model_12_target
        self.default_stop = default_stop
        self.min_rr = min_rr
        self.pip_size = pip_size

        # Initialize detectors
        self.killzone_mgr = KillzoneManager()
        self.fvg_detector = FVGDetector()
        self.ob_detector = OrderBlockDetector()
        self.structure_analyzer = MarketStructureAnalyzer()
        self.liquidity_detector = LiquidityDetector()
        self.displacement_detector = DisplacementDetector()

        # Graph-driven reasoning (lazy-loaded, graceful fallback)
        try:
            from ict_agent.core.graph_reasoner import VexGraphReasoner

            self.graph_reasoner = VexGraphReasoner()
        except Exception:
            self.graph_reasoner = None

        # Session state tracking
        self.session_state = SessionState(phase=SessionPhase.UNKNOWN)

    # =========================================================================
    # MAIN ANALYSIS METHOD
    # =========================================================================

    def analyze(
        self,
        symbol: str,
        df: pd.DataFrame,
        htf_df: Optional[pd.DataFrame] = None,
        timeframe: str = "15m",
        killzone_override: Optional[str] = None,
        current_time: Optional[datetime] = None,
    ) -> EngineResult:
        """
        Main entry point - analyzes market and returns trade decision.
        """
        now = current_time if current_time else datetime.now(NY_TZ)
        trace: List[GateLog] = []
        current_price = float(df["close"].iloc[-1])

        # ---------------------------------------------------------------------
        # GATE 1: KILLZONE CHECK
        # ---------------------------------------------------------------------
        if killzone_override:
            killzone_active = True
            killzone_name = killzone_override
        else:
            killzone = self.killzone_mgr.get_current_killzone(now)
            killzone_active = killzone is not None
            killzone_name = killzone.name if killzone else "none"

        trace.append(
            GateLog(
                gate="G1_KILLZONE",
                passed=killzone_active,
                summary=f"{killzone_name}" if killzone_active else "Outside killzone",
                details={
                    "killzone": killzone_name,
                    "time": now.strftime("%H:%M ET"),
                    "override": killzone_override is not None,
                },
            )
        )

        if not killzone_active:
            return EngineResult(
                trade=False,
                setup=None,
                bias=Bias.NEUTRAL,
                session_phase=self._get_session_phase(now),
                killzone_active=False,
                liquidity_levels=[],
                pd_arrays=[],
                session_state=self.session_state,
                rejection_reason="Outside killzone - no trades allowed",
                gate_trace=trace,
            )

        # ---------------------------------------------------------------------
        # GATE 2: SESSION PHASE (PO3)
        # ---------------------------------------------------------------------
        session_phase = self._get_session_phase(now)
        self._update_session_state(df, session_phase, now)

        trace.append(
            GateLog(
                gate="G2_SESSION",
                passed=True,
                summary=f"{session_phase.value} (PO3)",
                details={
                    "phase": session_phase.value,
                    "asia_high": self.session_state.asia_high,
                    "asia_low": self.session_state.asia_low,
                    "asia_swept": self.session_state.asia_swept,
                    "judas_dir": self.session_state.judas_direction,
                    "true_dir": self.session_state.true_direction,
                },
            )
        )

        # ---------------------------------------------------------------------
        # GATE 3: BIAS DETERMINATION
        # ---------------------------------------------------------------------
        bias = self._determine_bias(df, htf_df)

        trace.append(
            GateLog(
                gate="G3_BIAS",
                passed=bias != Bias.NEUTRAL,
                summary=f"{bias.value}"
                if bias != Bias.NEUTRAL
                else "Neutral — no clear structure",
                details={"bias": bias.value, "price": current_price},
            )
        )

        if bias == Bias.NEUTRAL:
            return EngineResult(
                trade=False,
                setup=None,
                bias=bias,
                session_phase=session_phase,
                killzone_active=killzone_active,
                liquidity_levels=[],
                pd_arrays=[],
                session_state=self.session_state,
                rejection_reason="No clear bias - structure is neutral",
                gate_trace=trace,
            )

        # ---------------------------------------------------------------------
        # GATE 4: LIQUIDITY MAPPING (IRL vs ERL)
        # ---------------------------------------------------------------------
        liquidity_levels = self._map_liquidity(df, symbol)
        erl_levels = [l for l in liquidity_levels if l.external]
        irl_levels = [l for l in liquidity_levels if not l.external]

        trace.append(
            GateLog(
                gate="G4_LIQUIDITY",
                passed=len(erl_levels) > 0,
                summary=f"{len(erl_levels)} ERL + {len(irl_levels)} IRL = {len(liquidity_levels)} total",
                details={
                    "total": len(liquidity_levels),
                    "erl_count": len(erl_levels),
                    "irl_count": len(irl_levels),
                    "erl_types": {l.source: round(l.price, 5) for l in erl_levels[:8]},
                    "irl_types": {l.source: round(l.price, 5) for l in irl_levels[:8]},
                },
            )
        )

        if not erl_levels:
            return EngineResult(
                trade=False,
                setup=None,
                bias=bias,
                session_phase=session_phase,
                killzone_active=killzone_active,
                liquidity_levels=liquidity_levels,
                pd_arrays=[],
                session_state=self.session_state,
                rejection_reason="No external liquidity target identified",
                gate_trace=trace,
            )

        # ---------------------------------------------------------------------
        # GATE 5: SWEEP DETECTION
        # ---------------------------------------------------------------------
        sweep_info = self._check_liquidity_sweep(df, liquidity_levels)

        trace.append(
            GateLog(
                gate="G5_SWEEP",
                passed=True,  # informational — sweep is not required
                summary=f"Sweep {sweep_info['direction']} @ {sweep_info['level'].price:.5f} ({sweep_info['candles_ago']} bars ago)"
                if sweep_info.get("occurred")
                else "No recent sweep",
                details=sweep_info
                if not sweep_info.get("occurred")
                else {
                    "occurred": True,
                    "direction": sweep_info["direction"],
                    "price": round(sweep_info["level"].price, 5),
                    "source": sweep_info["level"].source,
                    "candles_ago": sweep_info["candles_ago"],
                },
            )
        )

        # ---------------------------------------------------------------------
        # GATE 6: PD ARRAY ENTRY ZONES
        # ---------------------------------------------------------------------
        pd_arrays = self._find_pd_arrays(df, bias, timeframe)
        valid_entries = [p for p in pd_arrays if p.valid and not p.mitigated]

        trace.append(
            GateLog(
                gate="G6_PD_ARRAYS",
                passed=len(valid_entries) > 0,
                summary=f"{len(valid_entries)} valid entries ({len(pd_arrays)} total)"
                if valid_entries
                else f"0 valid ({len(pd_arrays)} found, all mitigated/invalid)",
                details={
                    "total_found": len(pd_arrays),
                    "valid_count": len(valid_entries),
                    "entries": [
                        {
                            "type": p.type,
                            "dir": p.direction,
                            "top": round(p.top, 5),
                            "bot": round(p.bottom, 5),
                            "ote": round(p.ote_level, 5),
                            "mitigated": p.mitigated,
                        }
                        for p in pd_arrays[:6]
                    ],
                },
            )
        )

        if not valid_entries:
            return EngineResult(
                trade=False,
                setup=None,
                bias=bias,
                session_phase=session_phase,
                killzone_active=killzone_active,
                liquidity_levels=liquidity_levels,
                pd_arrays=pd_arrays,
                session_state=self.session_state,
                rejection_reason="No valid PD array entry zones",
                gate_trace=trace,
            )

        # ---------------------------------------------------------------------
        # GATE 7: TRADE CLASSIFICATION (Type A or B)
        # ---------------------------------------------------------------------
        trade_type, target_liquidity = self._classify_trade(
            current_price, bias, sweep_info, erl_levels, irl_levels
        )

        trace.append(
            GateLog(
                gate="G7_CLASSIFY",
                passed=True,
                summary=f"{trade_type.value} → target {target_liquidity.source} @ {target_liquidity.price:.5f}",
                details={
                    "trade_type": trade_type.value,
                    "target_price": round(target_liquidity.price, 5),
                    "target_source": target_liquidity.source,
                    "target_type": target_liquidity.type,
                },
            )
        )

        # ---------------------------------------------------------------------
        # GATE 7b: DISPLACEMENT CHECK
        # ---------------------------------------------------------------------
        displacement_detected = False
        try:
            disp_result = self.displacement_detector.detect(df)
            if disp_result is not None and not disp_result.empty:
                # Check last few candles for displacement
                recent = disp_result.tail(5)
                if "displacement" in recent.columns:
                    displacement_detected = bool(recent["displacement"].any())
                elif len(recent) > 0:
                    displacement_detected = True
        except Exception:
            pass  # detector may fail on insufficient data

        trace.append(
            GateLog(
                gate="G7b_DISPLACEMENT",
                passed=True,  # informational
                summary="Displacement confirmed"
                if displacement_detected
                else "No displacement",
                details={"detected": displacement_detected},
            )
        )

        # ---------------------------------------------------------------------
        # GATE 7c: GRAPH-DRIVEN REASONING
        # ---------------------------------------------------------------------
        graph_result = None
        if self.graph_reasoner is not None:
            try:
                graph_result = self.graph_reasoner.enhance_setup(
                    bias=bias,
                    session_phase=session_phase,
                    trade_type=trade_type,
                    sweep_info=sweep_info,
                    pd_arrays=valid_entries,
                    killzone_name=killzone_name,
                    displacement_detected=bool(displacement_detected),
                    current_time=now.strftime("%H:%M") if now else "",
                )
                trace.append(
                    GateLog(
                        gate="G7c_GRAPH",
                        passed=True,
                        summary=f"{'GO' if graph_result.go_no_go else 'NO-GO'} "
                        f"score={graph_result.score_raw:.1f} "
                        f"model={graph_result.recommended_model_name} "
                        f"conf={graph_result.confidence:.0%}",
                        details={
                            "go_no_go": graph_result.go_no_go,
                            "score": graph_result.score_raw,
                            "model": graph_result.recommended_model_name,
                            "confidence": round(graph_result.confidence, 2),
                            "confluences": graph_result.confluences[:6],
                            "red_flags": graph_result.red_flags,
                            "missing": graph_result.missing,
                        },
                    )
                )
            except Exception as e:
                trace.append(
                    GateLog(
                        gate="G7c_GRAPH",
                        passed=True,
                        summary=f"Error: {e}",
                        details={"error": str(e)},
                    )
                )
                graph_result = None
        else:
            trace.append(
                GateLog(
                    gate="G7c_GRAPH",
                    passed=True,
                    summary="GraphReasoner not loaded",
                    details={},
                )
            )

        # ---------------------------------------------------------------------
        # GATE 8: MODEL SELECTION
        # (Graph reasoner recommendation takes priority when available and
        #  the graph signals GO; otherwise fall back to original heuristic)
        # ---------------------------------------------------------------------
        if (
            graph_result is not None
            and graph_result.go_no_go
            and graph_result.model is not None
        ):
            model = graph_result.model
            # Pick entry zone matching the model's preferred PD array type
            entry_zone = self._pick_entry_for_model(model, valid_entries)
        else:
            model, entry_zone = self._select_model(
                valid_entries, trade_type, session_phase, sweep_info
            )

        trace.append(
            GateLog(
                gate="G8_MODEL",
                passed=True,
                summary=f"{model.value} via {'graph' if (graph_result and graph_result.go_no_go) else 'heuristic'}",
                details={
                    "model": model.value,
                    "source": "graph"
                    if (graph_result and graph_result.go_no_go)
                    else "heuristic",
                    "entry_type": entry_zone.type if entry_zone else None,
                    "entry_mid": round(entry_zone.midpoint, 5) if entry_zone else None,
                },
            )
        )

        # ---------------------------------------------------------------------
        # BUILD TRADE SETUP
        # ---------------------------------------------------------------------
        setup = self._build_setup(
            symbol=symbol,
            timeframe=timeframe,
            bias=bias,
            trade_type=trade_type,
            model=model,
            entry_zone=entry_zone,
            target_liquidity=target_liquidity,
            session_phase=session_phase,
            killzone_name=killzone_name,
            current_price=current_price,
            sweep_info=sweep_info,
            now=now,
            graph_result=graph_result,
        )

        # Check minimum R:R
        rr_ok = setup.rr_ratio >= self.min_rr

        trace.append(
            GateLog(
                gate="G9_RR_CHECK",
                passed=rr_ok,
                summary=f"R:R {setup.rr_ratio:.1f} {'≥' if rr_ok else '<'} min {self.min_rr} | "
                f"entry={setup.entry_price:.5f} SL={setup.stop_loss:.5f} "
                f"TP1={setup.target_1:.5f}",
                details={
                    "rr_ratio": round(setup.rr_ratio, 2),
                    "min_rr": self.min_rr,
                    "entry": round(setup.entry_price, 5),
                    "stop_loss": round(setup.stop_loss, 5),
                    "target_1": round(setup.target_1, 5),
                    "target_2": round(setup.target_2, 5) if setup.target_2 else None,
                    "risk_pips": round(setup.risk_pips, 1),
                    "reward_pips": round(setup.reward_pips, 1),
                    "confluences": setup.confluences,
                    "confluence_score": setup.confluence_score,
                    "confidence": round(setup.confidence, 2),
                },
            )
        )

        if not rr_ok:
            return EngineResult(
                trade=False,
                setup=setup,
                bias=bias,
                session_phase=session_phase,
                killzone_active=killzone_active,
                liquidity_levels=liquidity_levels,
                pd_arrays=pd_arrays,
                session_state=self.session_state,
                rejection_reason=f"R:R {setup.rr_ratio:.1f} below minimum {self.min_rr}",
                gate_trace=trace,
            )

        # ALL GATES PASSED
        return EngineResult(
            trade=True,
            setup=setup,
            bias=bias,
            session_phase=session_phase,
            killzone_active=killzone_active,
            liquidity_levels=liquidity_levels,
            pd_arrays=pd_arrays,
            session_state=self.session_state,
            gate_trace=trace,
        )

    # =========================================================================
    # GATE METHODS
    # =========================================================================

    def _get_session_phase(self, now: datetime) -> SessionPhase:
        """Determine current PO3 session phase based on time."""
        hour = now.hour

        # Asia: 7PM - 12AM NY (accumulation)
        if 19 <= hour <= 23:
            return SessionPhase.ACCUMULATION

        # London: 2AM - 5AM NY (manipulation)
        if 2 <= hour <= 5:
            return SessionPhase.MANIPULATION

        # NY: 7AM - 11AM NY (distribution)
        if 7 <= hour <= 11:
            return SessionPhase.DISTRIBUTION

        return SessionPhase.UNKNOWN

    def _update_session_state(
        self, df: pd.DataFrame, phase: SessionPhase, now: datetime
    ) -> None:
        """Update session state tracking for PO3."""

        if phase == SessionPhase.ACCUMULATION:
            # Calculate Asia range
            try:
                asian_calc = AsianRangeCalculator()
                asian_range = asian_calc.calculate(df)
                if asian_range:
                    self.session_state.asia_high = asian_range.high
                    self.session_state.asia_low = asian_range.low
                    self.session_state.phase = phase
            except Exception:
                pass

        elif phase == SessionPhase.MANIPULATION:
            # Check if Asia was swept
            if self.session_state.asia_high and self.session_state.asia_low:
                current_high = df["high"].iloc[-20:].max()
                current_low = df["low"].iloc[-20:].min()

                if current_high > self.session_state.asia_high:
                    self.session_state.asia_swept = "high"
                    self.session_state.judas_direction = "up"
                    self.session_state.true_direction = "down"  # Expect reversal
                elif current_low < self.session_state.asia_low:
                    self.session_state.asia_swept = "low"
                    self.session_state.judas_direction = "down"
                    self.session_state.true_direction = "up"

            self.session_state.phase = phase

        elif phase == SessionPhase.DISTRIBUTION:
            self.session_state.phase = phase

    def _determine_bias(self, df: pd.DataFrame, htf_df: Optional[pd.DataFrame]) -> Bias:
        """Determine directional bias from structure."""
        from ict_agent.detectors.market_structure import StructureType

        # Analyze structure
        self.structure_analyzer.analyze(df)
        trend = self.structure_analyzer.get_current_trend()

        # HTF confirmation if available
        htf_bias = None
        if htf_df is not None and len(htf_df) > 50:
            htf_analyzer = MarketStructureAnalyzer()
            htf_analyzer.analyze(htf_df)
            htf_trend = htf_analyzer.get_current_trend()

            # StructureType is an Enum with values: BULLISH=1, BEARISH=-1, NEUTRAL=0
            if htf_trend == StructureType.BULLISH:
                htf_bias = Bias.BULLISH
            elif htf_trend == StructureType.BEARISH:
                htf_bias = Bias.BEARISH

        # Determine bias from LTF trend
        if trend == StructureType.BULLISH:
            return Bias.BULLISH
        elif trend == StructureType.BEARISH:
            return Bias.BEARISH

        # If LTF neutral, defer to HTF
        if htf_bias:
            return htf_bias

        return Bias.NEUTRAL

    def _map_liquidity(self, df: pd.DataFrame, symbol: str) -> List[LiquidityLevel]:
        """Map all liquidity levels - both IRL and ERL."""
        levels = []
        current_price = float(df["close"].iloc[-1])

        # Get swings for reference
        swing_highs = []
        swing_lows = []

        for i in range(5, len(df) - 5):
            # Swing high
            if df["high"].iloc[i] == df["high"].iloc[i - 5 : i + 6].max():
                swing_highs.append(df["high"].iloc[i])
            # Swing low
            if df["low"].iloc[i] == df["low"].iloc[i - 5 : i + 6].min():
                swing_lows.append(df["low"].iloc[i])

        # EXTERNAL RANGE LIQUIDITY (ERL)
        # Equal highs (BSL)
        if len(swing_highs) >= 2:
            for i in range(len(swing_highs) - 1):
                for j in range(i + 1, len(swing_highs)):
                    diff = abs(swing_highs[i] - swing_highs[j])
                    if diff < 0.0005:  # Within 5 pips
                        avg = (swing_highs[i] + swing_highs[j]) / 2
                        levels.append(
                            LiquidityLevel(
                                price=avg,
                                type="bsl",
                                source="equal_highs",
                                external=True,
                            )
                        )

        # Equal lows (SSL)
        if len(swing_lows) >= 2:
            for i in range(len(swing_lows) - 1):
                for j in range(i + 1, len(swing_lows)):
                    diff = abs(swing_lows[i] - swing_lows[j])
                    if diff < 0.0005:
                        avg = (swing_lows[i] + swing_lows[j]) / 2
                        levels.append(
                            LiquidityLevel(
                                price=avg,
                                type="ssl",
                                source="equal_lows",
                                external=True,
                            )
                        )

        # Previous day high/low (ERL)
        if len(df) > 96:  # At least 1 day of 15m data
            pdh = df["high"].iloc[-96:-1].max()
            pdl = df["low"].iloc[-96:-1].min()
            levels.append(
                LiquidityLevel(price=pdh, type="bsl", source="pdh", external=True)
            )
            levels.append(
                LiquidityLevel(price=pdl, type="ssl", source="pdl", external=True)
            )

        # Session highs/lows (ERL)
        if len(df) > 20:
            session_high = df["high"].iloc[-20:].max()
            session_low = df["low"].iloc[-20:].min()
            levels.append(
                LiquidityLevel(
                    price=session_high, type="bsl", source="session_high", external=True
                )
            )
            levels.append(
                LiquidityLevel(
                    price=session_low, type="ssl", source="session_low", external=True
                )
            )

        # INTERNAL RANGE LIQUIDITY (IRL)
        # FVGs are IRL - use get_active_fvgs() which returns FVG objects
        self.fvg_detector.detect(df)  # Populate internal state
        active_fvgs = self.fvg_detector.get_active_fvgs()
        for fvg in active_fvgs:
            fvg_type = "bsl" if fvg.direction.value == 1 else "ssl"
            levels.append(
                LiquidityLevel(
                    price=fvg.midpoint,
                    type=fvg_type,
                    source="fvg_midpoint",
                    external=False,  # IRL
                )
            )

        # OBs are IRL - use get_active_obs() if available, else parse DataFrame
        ob_df = self.ob_detector.detect(df)
        if ob_df is not None and len(ob_df) > 0:
            # Check for rows with actual OB data (non-zero direction)
            ob_mask = ob_df["ob_direction"] != 0
            for idx in ob_df[ob_mask].index:
                row = ob_df.loc[idx]
                if not row.get("ob_mitigated", False):
                    top = row.get("ob_top", 0)
                    bottom = row.get("ob_bottom", 0)
                    if top > 0 and bottom > 0:
                        mid = (top + bottom) / 2
                        ob_type = "bsl" if row["ob_direction"] == 1 else "ssl"
                        levels.append(
                            LiquidityLevel(
                                price=mid,
                                type=ob_type,
                                source="order_block",
                                external=False,  # IRL
                            )
                        )

        return levels

    def _check_liquidity_sweep(
        self, df: pd.DataFrame, levels: List[LiquidityLevel]
    ) -> Dict[str, Any]:
        """Check for recent liquidity sweeps."""
        sweep_info = {
            "occurred": False,
            "level": None,
            "direction": None,
            "candles_ago": None,
        }

        current_price = float(df["close"].iloc[-1])

        # Check last 10 candles for sweep
        for i in range(1, min(11, len(df))):
            candle_high = df["high"].iloc[-i]
            candle_low = df["low"].iloc[-i]
            candle_close = df["close"].iloc[-i]

            for level in levels:
                if level.external and not level.swept:
                    # BSL sweep (ran above, closed below)
                    if level.type == "bsl":
                        if candle_high > level.price and candle_close < level.price:
                            sweep_info = {
                                "occurred": True,
                                "level": level,
                                "direction": "up_sweep",  # Swept up, expect down
                                "candles_ago": i,
                            }
                            level.swept = True
                            return sweep_info

                    # SSL sweep (ran below, closed above)
                    elif level.type == "ssl":
                        if candle_low < level.price and candle_close > level.price:
                            sweep_info = {
                                "occurred": True,
                                "level": level,
                                "direction": "down_sweep",  # Swept down, expect up
                                "candles_ago": i,
                            }
                            level.swept = True
                            return sweep_info

        return sweep_info

    def _find_pd_arrays(
        self, df: pd.DataFrame, bias: Bias, timeframe: str
    ) -> List[PDArray]:
        """Find all PD arrays (FVGs, OBs) aligned with bias."""
        from ict_agent.detectors.fvg import FVGDirection

        arrays = []

        # FVGs - use the proper get_active_fvgs() method
        self.fvg_detector.detect(df)  # Ensure detection is run
        active_fvgs = self.fvg_detector.get_active_fvgs()

        for fvg in active_fvgs:
            direction = (
                "bullish" if fvg.direction == FVGDirection.BULLISH else "bearish"
            )

            # Only include FVGs aligned with bias
            if (bias == Bias.BULLISH and direction == "bullish") or (
                bias == Bias.BEARISH and direction == "bearish"
            ):
                arrays.append(
                    PDArray(
                        type="fvg",
                        direction=direction,
                        top=fvg.top,
                        bottom=fvg.bottom,
                        midpoint=fvg.midpoint,
                        ote_level=fvg.ote_705,  # Use pre-calculated OTE
                        timeframe=timeframe,
                        valid=True,
                        mitigated=fvg.mitigated,
                    )
                )

        # Order Blocks - parse from DataFrame with correct column names
        ob_df = self.ob_detector.detect(df)
        if ob_df is not None and len(ob_df) > 0:
            ob_mask = ob_df["ob_direction"] != 0
            for idx in ob_df[ob_mask].index:
                row = ob_df.loc[idx]
                direction = "bullish" if row["ob_direction"] == 1 else "bearish"

                if (bias == Bias.BULLISH and direction == "bullish") or (
                    bias == Bias.BEARISH and direction == "bearish"
                ):
                    top = row.get("ob_top", 0)
                    bottom = row.get("ob_bottom", 0)
                    if top > 0 and bottom > 0:
                        arrays.append(
                            PDArray(
                                type="ob",
                                direction=direction,
                                top=top,
                                bottom=bottom,
                                midpoint=(top + bottom) / 2,
                                ote_level=bottom + (top - bottom) * 0.705
                                if direction == "bullish"
                                else top - (top - bottom) * 0.705,
                                timeframe=timeframe,
                                valid=True,
                                mitigated=row.get("ob_mitigated", False),
                            )
                        )

        return arrays

    def _classify_trade(
        self,
        current_price: float,
        bias: Bias,
        sweep_info: Dict,
        erl_levels: List[LiquidityLevel],
        irl_levels: List[LiquidityLevel],
    ) -> Tuple[TradeType, LiquidityLevel]:
        """
        Classify trade as Type A (IRL→ERL) or Type B (ERL→IRL).

        THE DECODER KEY:
        - If we're entering at IRL (FVG/OB) → Target is ERL (equal highs/lows)
        - If we just swept ERL → Target is IRL (FVG rebalance, equilibrium)
        """

        # If a sweep just occurred, this is a TURTLE SOUP (Type B)
        if sweep_info.get("occurred"):
            # Find nearest IRL target
            if irl_levels:
                if bias == Bias.BEARISH:
                    # Swept highs, targeting IRL below
                    targets = sorted(
                        [l for l in irl_levels if l.price < current_price],
                        key=lambda x: x.price,
                        reverse=True,
                    )
                else:
                    # Swept lows, targeting IRL above
                    targets = sorted(
                        [l for l in irl_levels if l.price > current_price],
                        key=lambda x: x.price,
                    )

                if targets:
                    return TradeType.ERL_TO_IRL, targets[0]

        # Standard IRL → ERL trade (Type A)
        if bias == Bias.BEARISH:
            # Target SSL (sell-side liquidity below)
            targets = sorted(
                [l for l in erl_levels if l.type == "ssl" and l.price < current_price],
                key=lambda x: x.price,
                reverse=True,
            )
        else:
            # Target BSL (buy-side liquidity above)
            targets = sorted(
                [l for l in erl_levels if l.type == "bsl" and l.price > current_price],
                key=lambda x: x.price,
            )

        if targets:
            return TradeType.IRL_TO_ERL, targets[0]

        # Fallback - use any ERL
        if erl_levels:
            return TradeType.IRL_TO_ERL, erl_levels[0]

        # Last resort
        return TradeType.IRL_TO_ERL, LiquidityLevel(
            price=current_price + (0.003 if bias == Bias.BULLISH else -0.003),
            type="bsl" if bias == Bias.BULLISH else "ssl",
            source="projected",
            external=True,
        )

    def _select_model(
        self,
        pd_arrays: List[PDArray],
        trade_type: TradeType,
        session_phase: SessionPhase,
        sweep_info: Dict,
    ) -> Tuple[ModelType, PDArray]:
        """Select the appropriate ICT model and entry zone."""

        # If turtle soup (sweep just happened), use that model
        if trade_type == TradeType.ERL_TO_IRL and sweep_info.get("occurred"):
            # Prefer FVG for turtle soup exit
            fvgs = [p for p in pd_arrays if p.type == "fvg"]
            if fvgs:
                return ModelType.TURTLE_SOUP, fvgs[0]
            return ModelType.TURTLE_SOUP, pd_arrays[0]

        # Check for Model 12 setup (OB → expansion → FVG)
        obs = [p for p in pd_arrays if p.type == "ob"]
        fvgs = [p for p in pd_arrays if p.type == "fvg"]

        if obs and fvgs:
            # Model 12: Use FVG that formed after OB
            return ModelType.MODEL_12, fvgs[0]

        # Model 11: Standard OTE entry
        if pd_arrays:
            # Prefer FVG, then OB
            if fvgs:
                return ModelType.MODEL_11, fvgs[0]
            return ModelType.MODEL_11, obs[0] if obs else pd_arrays[0]

        return ModelType.STANDARD, pd_arrays[0] if pd_arrays else None

    def _pick_entry_for_model(
        self, model: ModelType, pd_arrays: List[PDArray]
    ) -> PDArray:
        """Pick the best entry zone for a graph-recommended model."""
        fvgs = [p for p in pd_arrays if p.type == "fvg"]
        obs = [p for p in pd_arrays if p.type == "ob"]

        if model == ModelType.TURTLE_SOUP:
            return fvgs[0] if fvgs else pd_arrays[0]
        elif model == ModelType.MODEL_12:
            # Model 12 prefers FVG formed after OB
            return fvgs[0] if fvgs else pd_arrays[0]
        elif model == ModelType.MODEL_11:
            return fvgs[0] if fvgs else (obs[0] if obs else pd_arrays[0])
        else:
            return pd_arrays[0]

    def _build_setup(
        self,
        symbol: str,
        timeframe: str,
        bias: Bias,
        trade_type: TradeType,
        model: ModelType,
        entry_zone: PDArray,
        target_liquidity: LiquidityLevel,
        session_phase: SessionPhase,
        killzone_name: str,
        current_price: float,
        sweep_info: Dict,
        now: datetime,
        graph_result: Optional[Any] = None,
    ) -> TradeSetup:
        """Build the complete trade setup."""

        # Determine entry price (midpoint or OTE level)
        if model == ModelType.MODEL_12:
            entry_price = entry_zone.midpoint  # CE (consequent encroachment)
        else:
            entry_price = entry_zone.ote_level  # 70.5% level

        # Calculate stop loss
        if bias == Bias.BEARISH:
            stop_loss = entry_zone.top + (5 * self.pip_size)  # Above zone + buffer
            stop_reason = f"Above {entry_zone.type.upper()} top + 5 pip buffer"
        else:
            stop_loss = entry_zone.bottom - (5 * self.pip_size)  # Below zone + buffer
            stop_reason = f"Below {entry_zone.type.upper()} bottom + 5 pip buffer"

        # Calculate targets
        target_1 = target_liquidity.price

        # Model-specific targets
        if model == ModelType.MODEL_12:
            # Fixed 20 pip target
            if bias == Bias.BEARISH:
                target_1 = min(
                    target_1, entry_price - (self.model_12_target * self.pip_size)
                )
            else:
                target_1 = max(
                    target_1, entry_price + (self.model_12_target * self.pip_size)
                )
        elif model == ModelType.MODEL_11:
            # Fixed 30 pip target
            if bias == Bias.BEARISH:
                target_1 = min(
                    target_1, entry_price - (self.model_11_target * self.pip_size)
                )
            else:
                target_1 = max(
                    target_1, entry_price + (self.model_11_target * self.pip_size)
                )

        # Target 2 is the full liquidity target
        target_2 = (
            target_liquidity.price if target_liquidity.price != target_1 else None
        )

        # Calculate pips and R:R
        risk_pips = abs(entry_price - stop_loss) / self.pip_size
        reward_pips = abs(entry_price - target_1) / self.pip_size
        rr_ratio = reward_pips / risk_pips if risk_pips > 0 else 0

        # Build confluence list
        confluences = []

        # Killzone
        confluences.append(f"✅ Killzone: {killzone_name}")

        # Session phase
        if session_phase == SessionPhase.DISTRIBUTION:
            confluences.append("✅ PO3: Distribution phase (optimal)")
        elif session_phase == SessionPhase.MANIPULATION:
            confluences.append("⚠️ PO3: Manipulation phase (Judas possible)")

        # Bias
        confluences.append(f"✅ Bias: {bias.value.upper()}")

        # Entry zone
        confluences.append(
            f"✅ Entry: {entry_zone.type.upper()} @ {entry_zone.midpoint:.5f}"
        )

        # Trade type
        if trade_type == TradeType.IRL_TO_ERL:
            confluences.append(
                f"✅ Type A: IRL→ERL (target: {target_liquidity.source})"
            )
        else:
            confluences.append(f"✅ Type B: ERL→IRL (turtle soup)")

        # Sweep
        if sweep_info.get("occurred"):
            confluences.append(
                f"✅ Sweep: {sweep_info['level'].source} swept {sweep_info['candles_ago']} candles ago"
            )

        # Model
        confluences.append(f"✅ Model: {model.value.upper()}")

        # R:R
        if rr_ratio >= 2.0:
            confluences.append(f"✅ R:R: {rr_ratio:.1f} (excellent)")
        elif rr_ratio >= 1.5:
            confluences.append(f"✅ R:R: {rr_ratio:.1f} (good)")
        else:
            confluences.append(f"⚠️ R:R: {rr_ratio:.1f} (marginal)")

        confluence_score = len([c for c in confluences if c.startswith("✅")])
        confidence = min(1.0, confluence_score / 8.0)

        # ── Merge graph-derived confluences ──────────────────────────────
        if graph_result is not None and graph_result.confluences:
            confluences.append("")  # visual separator
            confluences.append("── Graph Reasoning ──")
            confluences.extend(graph_result.confluences)

            # Upgrade score: blend VEX count-based score with graph score
            graph_positive = graph_result.confluence_score
            confluence_score += graph_positive
            # Weighted confidence: 60% graph (weighted scoring) + 40% VEX (count)
            if graph_result.confidence > 0:
                confidence = 0.4 * confidence + 0.6 * graph_result.confidence
            # Attach red flags
            if graph_result.red_flags:
                for flag in graph_result.red_flags:
                    confluences.append(f"🚫 Graph: {flag}")

        # Entry reason
        entry_reason = f"{model.value.upper()} entry at {entry_zone.type.upper()} "
        if model == ModelType.MODEL_12:
            entry_reason += f"CE (midpoint) targeting {self.model_12_target} pips"
        elif model == ModelType.MODEL_11:
            entry_reason += f"OTE (70.5%) targeting {self.model_11_target} pips"
        elif model == ModelType.TURTLE_SOUP:
            entry_reason += f"fading {sweep_info.get('level', {}).source if sweep_info.get('level') else 'sweep'}"

        return TradeSetup(
            trade_type=trade_type,
            model=model,
            bias=bias,
            session_phase=session_phase,
            killzone=killzone_name,
            entry_price=entry_price,
            entry_zone=entry_zone,
            entry_reason=entry_reason,
            stop_loss=stop_loss,
            stop_reason=stop_reason,
            target_1=target_1,
            target_2=target_2,
            target_type="erl" if trade_type == TradeType.IRL_TO_ERL else "irl",
            target_liquidity=target_liquidity,
            risk_pips=risk_pips,
            reward_pips=reward_pips,
            rr_ratio=rr_ratio,
            confluences=confluences,
            confluence_score=confluence_score,
            confidence=confidence,
            symbol=symbol,
            timeframe=timeframe,
            timestamp=now,
        )

    # =========================================================================
    # UTILITY METHODS
    # =========================================================================

    def format_result(self, result: EngineResult) -> str:
        """Format engine result for display."""
        lines = []
        lines.append("=" * 60)
        lines.append("🤖 VEX CORE ENGINE ANALYSIS")
        lines.append("=" * 60)
        lines.append("")

        # Context
        lines.append(f"📊 Bias: {result.bias.value.upper()}")
        lines.append(f"⏰ Session: {result.session_phase.value.upper()}")
        lines.append(
            f"🎯 Killzone: {'ACTIVE ✅' if result.killzone_active else 'INACTIVE ❌'}"
        )
        lines.append("")

        # Liquidity
        erl = [l for l in result.liquidity_levels if l.external]
        irl = [l for l in result.liquidity_levels if not l.external]
        lines.append(f"💧 Liquidity: {len(erl)} ERL | {len(irl)} IRL")

        # PD Arrays
        lines.append(f"📐 PD Arrays: {len(result.pd_arrays)} found")
        lines.append("")

        # Decision
        if result.trade and result.setup:
            setup = result.setup
            lines.append("=" * 60)
            lines.append("✅ TRADE SIGNAL")
            lines.append("=" * 60)
            lines.append(f"  Type: {setup.trade_type.value}")
            lines.append(f"  Model: {setup.model.value.upper()}")
            lines.append(
                f"  Direction: {'SHORT' if setup.bias == Bias.BEARISH else 'LONG'}"
            )
            lines.append(f"  Entry: {setup.entry_price:.5f}")
            lines.append(f"  Stop: {setup.stop_loss:.5f} ({setup.risk_pips:.1f} pips)")
            lines.append(
                f"  Target: {setup.target_1:.5f} ({setup.reward_pips:.1f} pips)"
            )
            lines.append(f"  R:R: {setup.rr_ratio:.1f}")
            lines.append(f"  Confidence: {setup.confidence * 100:.0f}%")
            lines.append("")
            lines.append("  Confluences:")
            for c in setup.confluences:
                lines.append(f"    {c}")
        else:
            lines.append("=" * 60)
            lines.append("❌ NO TRADE")
            lines.append("=" * 60)
            lines.append(f"  Reason: {result.rejection_reason}")

        lines.append("")
        lines.append("=" * 60)

        return "\n".join(lines)


# =============================================================================
# STANDALONE TEST
# =============================================================================

if __name__ == "__main__":
    import sys

    sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

    from ict_agent.data.oanda_fetcher import get_oanda_data

    print("Testing VEX Core Engine...")
    print("=" * 60)

    # Get live data
    symbol = "EUR_USD"
    df = get_oanda_data(symbol, timeframe="15m", count=200)
    htf_df = get_oanda_data(symbol, timeframe="1h", count=100)

    print(f"Loaded {len(df)} candles of {symbol} 15m")
    print(f"Loaded {len(htf_df)} candles of {symbol} 1H")

    # Run engine
    engine = VexCoreEngine()
    result = engine.analyze(symbol, df, htf_df, timeframe="15m")

    # Display result
    print(engine.format_result(result))
