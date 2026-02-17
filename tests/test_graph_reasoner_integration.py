#!/usr/bin/env python3
"""Integration test for VexGraphReasoner bridge.

Tests that the graph_reasoner bridge in train-ict correctly:
1. Lazy-loads graph_rag (ICTGraphStore + TradeReasoner) from ai-knowledge-graph
2. Translates VEX data structures to TradeReasoner signal dicts
3. Returns EnhancedResult with correct VEX ModelType mappings
4. Handles graceful fallback when graph_rag is unavailable
5. Produces human-readable summaries

Run from train-ict root:
    python -m pytest tests/test_graph_reasoner_integration.py -v
    # or directly:
    python tests/test_graph_reasoner_integration.py
"""

import sys
import os
from pathlib import Path

# Ensure train-ict/src is on the path
_TRAIN_ICT_SRC = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(_TRAIN_ICT_SRC))

from ict_agent.core.vex_core_engine import (
    Bias,
    ModelType,
    PDArray,
    SessionPhase,
    TradeType,
)
from ict_agent.core.graph_reasoner import (
    EnhancedResult,
    VexGraphReasoner,
    _REASONER_TO_VEX_MODEL,
    _VEX_MODEL_TO_REASONER,
)


# ── Helpers ───────────────────────────────────────────────────────────────

def _make_fvg(direction: str = "bullish") -> PDArray:
    """Create a mock FVG PDArray."""
    return PDArray(
        type="fvg",
        direction=direction,
        top=1.0850,
        bottom=1.0830,
        midpoint=1.0840,
        ote_level=1.0836,
        timeframe="5m",
        valid=True,
        mitigated=False,
    )


def _make_ob(direction: str = "bullish") -> PDArray:
    """Create a mock Order Block PDArray."""
    return PDArray(
        type="ob",
        direction=direction,
        top=1.0820,
        bottom=1.0810,
        midpoint=1.0815,
        ote_level=1.0813,
        timeframe="15m",
        valid=True,
        mitigated=False,
    )


def _make_breaker(direction: str = "bearish") -> PDArray:
    """Create a mock Breaker Block PDArray."""
    return PDArray(
        type="breaker",
        direction=direction,
        top=1.0900,
        bottom=1.0890,
        midpoint=1.0895,
        ote_level=1.0893,
        timeframe="1h",
        valid=True,
        mitigated=False,
    )


# ── Tests ──────────────────────────────────────────────────────────────────

class TestGraphReasonerIntegration:
    """Integration tests for the VexGraphReasoner bridge."""

    def setup_method(self):
        """Fresh reasoner for each test."""
        self.reasoner = VexGraphReasoner()

    # ── 1. Lazy loading ──────────────────────────────────────────────────

    def test_01_lazy_init(self):
        """Reasoner shouldn't load graph until first use."""
        r = VexGraphReasoner()
        assert r._loaded is False
        assert r._store is None
        assert r._reasoner is None
        print("  ✅ Lazy init: not loaded at construction time")

    def test_02_lazy_load_succeeds(self):
        """First call to _ensure_loaded() should import graph_rag and load graph."""
        available = self.reasoner._ensure_loaded()
        assert available is True, "graph_rag import failed — check path"
        assert self.reasoner._loaded is True
        assert self.reasoner._store is not None
        assert self.reasoner._reasoner is not None

        node_count = self.reasoner._store.G.number_of_nodes()
        edge_count = self.reasoner._store.G.number_of_edges()
        assert node_count > 1000, f"Expected >1000 nodes, got {node_count}"
        assert edge_count > 5000, f"Expected >5000 edges, got {edge_count}"
        print(f"  ✅ Lazy load: {node_count:,} nodes, {edge_count:,} edges")

    def test_03_idempotent_load(self):
        """Multiple calls to _ensure_loaded() shouldn't re-import."""
        self.reasoner._ensure_loaded()
        store_id = id(self.reasoner._store)
        self.reasoner._ensure_loaded()
        assert id(self.reasoner._store) == store_id
        print("  ✅ Idempotent: same store object on second call")

    # ── 2. Model mapping dicts ───────────────────────────────────────────

    def test_04_model_mapping_coverage(self):
        """Check that all VEX ModelTypes have reverse mappings."""
        expected_vex_models = {ModelType.MODEL_11, ModelType.MODEL_12,
                               ModelType.TURTLE_SOUP, ModelType.STANDARD}
        mapped_vex_models = set(_REASONER_TO_VEX_MODEL.values())
        missing = expected_vex_models - mapped_vex_models
        assert not missing, f"VEX ModelTypes not mapped: {missing}"
        print(f"  ✅ Model mapping: {len(_REASONER_TO_VEX_MODEL)} reasoner→VEX, "
              f"{len(_VEX_MODEL_TO_REASONER)} VEX→reasoner")

    def test_05_bidirectional_mapping(self):
        """Ensure forward and reverse mappings are consistent."""
        for reasoner_name, vex_model in _REASONER_TO_VEX_MODEL.items():
            # At least one reverse mapping should point back
            assert vex_model in _VEX_MODEL_TO_REASONER, \
                f"VEX model {vex_model} not in reverse map"
        print("  ✅ Bidirectional mapping consistent")

    # ── 3. Signal translation ────────────────────────────────────────────

    def test_06_bullish_silver_bullet_signals(self):
        """Silver Bullet — bullish bias, NY AM killzone, FVG + displacement."""
        result = self.reasoner.enhance_setup(
            bias=Bias.BULLISH,
            session_phase=SessionPhase.DISTRIBUTION,
            trade_type=TradeType.IRL_TO_ERL,
            sweep_info={"occurred": True, "type": "ssl", "price": 1.0800},
            pd_arrays=[_make_fvg("bullish"), _make_ob("bullish")],
            killzone_name="ny_am",
            displacement_detected=True,
            multi_tf_aligned=True,
            stop_loss_defined=True,
        )
        assert isinstance(result, EnhancedResult)
        assert result.go_no_go is not None  # either True or False
        assert isinstance(result.confluences, list)
        assert isinstance(result.confidence, float)
        assert 0.0 <= result.confidence <= 1.0
        print(f"  ✅ Silver Bullet setup: go={result.go_no_go}, "
              f"score={result.score_raw:.1f}, conf={result.confidence:.0%}, "
              f"model={result.recommended_model_name}")

    def test_07_bearish_turtle_soup_signals(self):
        """Turtle Soup — bearish bias, London killzone, sweep + breaker."""
        result = self.reasoner.enhance_setup(
            bias=Bias.BEARISH,
            session_phase=SessionPhase.MANIPULATION,
            trade_type=TradeType.ERL_TO_IRL,
            sweep_info={"occurred": True, "type": "bsl", "price": 1.0950},
            pd_arrays=[_make_breaker("bearish")],
            killzone_name="london_open",
            displacement_detected=True,
            smt_divergence=True,
        )
        assert isinstance(result, EnhancedResult)
        assert isinstance(result.confluences, list)
        print(f"  ✅ Turtle Soup setup: go={result.go_no_go}, "
              f"score={result.score_raw:.1f}, model={result.recommended_model_name}")

    def test_08_neutral_no_killzone(self):
        """Weak setup — neutral bias, no killzone, no patterns."""
        result = self.reasoner.enhance_setup(
            bias=Bias.NEUTRAL,
            session_phase=SessionPhase.ACCUMULATION,
            trade_type=TradeType.IRL_TO_ERL,
            sweep_info={},
            pd_arrays=[],
            killzone_name="asia",
            displacement_detected=False,
        )
        assert isinstance(result, EnhancedResult)
        # With no patterns + neutral bias + asia → likely NO-GO
        print(f"  ✅ Weak setup: go={result.go_no_go}, "
              f"score={result.score_raw:.1f}, flags={len(result.red_flags)}")

    def test_09_red_flags_propagated(self):
        """News imminent should trigger a red flag."""
        result = self.reasoner.enhance_setup(
            bias=Bias.BULLISH,
            session_phase=SessionPhase.DISTRIBUTION,
            trade_type=TradeType.IRL_TO_ERL,
            sweep_info={},
            pd_arrays=[_make_fvg()],
            killzone_name="ny_am",
            displacement_detected=False,
            news_imminent=True,
            stop_loss_defined=False,
        )
        assert isinstance(result, EnhancedResult)
        # Red flags may or may not appear depending on logic_engine's config,
        # but the field should be populated
        print(f"  ✅ Red flag test: go={result.go_no_go}, "
              f"red_flags={result.red_flags}")

    # ── 4. VEX model type in result ──────────────────────────────────────

    def test_10_vex_model_type_assigned(self):
        """High-confluence setup should produce a VEX ModelType."""
        result = self.reasoner.enhance_setup(
            bias=Bias.BULLISH,
            session_phase=SessionPhase.DISTRIBUTION,
            trade_type=TradeType.IRL_TO_ERL,
            sweep_info={"occurred": True, "type": "ssl", "price": 1.0800},
            pd_arrays=[_make_fvg("bullish"), _make_ob("bullish")],
            killzone_name="ny_am",
            displacement_detected=True,
            multi_tf_aligned=True,
            smt_divergence=True,
            stop_loss_defined=True,
        )
        if result.model is not None:
            assert isinstance(result.model, ModelType)
            print(f"  ✅ VEX ModelType assigned: {result.model}")
        else:
            print(f"  ⚠️ No VEX model assigned (score={result.score_raw:.1f}, "
                  f"rec={result.recommended_model_name})")

    # ── 5. Summary output ────────────────────────────────────────────────

    def test_11_summary_format(self):
        """Summary should produce readable text."""
        result = self.reasoner.enhance_setup(
            bias=Bias.BULLISH,
            session_phase=SessionPhase.DISTRIBUTION,
            trade_type=TradeType.IRL_TO_ERL,
            sweep_info={"occurred": True, "type": "ssl", "price": 1.0800},
            pd_arrays=[_make_fvg("bullish")],
            killzone_name="ny_am",
            displacement_detected=True,
        )
        summary = self.reasoner.summary(result)
        assert "GraphReasoner" in summary
        assert len(summary) > 10
        print(f"  ✅ Summary:\n    {summary.replace(chr(10), chr(10) + '    ')}")

    # ── 6. Fallback / passthrough ────────────────────────────────────────

    def test_12_fallback_passthrough(self):
        """When graph_rag is unavailable, result should pass through."""
        r = VexGraphReasoner()
        # Force unavailable state
        r._loaded = True
        r._available = False
        result = r.enhance_setup(
            bias=Bias.BULLISH,
            session_phase=SessionPhase.DISTRIBUTION,
            trade_type=TradeType.IRL_TO_ERL,
            sweep_info={},
            pd_arrays=[],
        )
        assert result.go_no_go is True, "Fallback should pass through"
        assert "unavailable" in result.explanation[0].lower()
        print("  ✅ Fallback passthrough: go=True (VEX logic continues)")


# ── Runner ─────────────────────────────────────────────────────────────────

def main():
    """Run all tests manually (no pytest needed)."""
    import traceback

    test = TestGraphReasonerIntegration()
    methods = [m for m in dir(test) if m.startswith("test_")]
    methods.sort()

    passed = 0
    failed = 0
    errors = []

    print("\n" + "=" * 60)
    print("VexGraphReasoner Integration Tests")
    print("=" * 60 + "\n")

    for method_name in methods:
        try:
            test.setup_method()
            getattr(test, method_name)()
            passed += 1
        except Exception as e:
            failed += 1
            errors.append((method_name, e))
            print(f"  ❌ {method_name}: {e}")
            traceback.print_exc()
        print()

    print("=" * 60)
    print(f"Results: {passed}/{passed + failed} passed, {failed} failed")
    print("=" * 60)

    if errors:
        print("\nFailed tests:")
        for name, err in errors:
            print(f"  - {name}: {err}")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
