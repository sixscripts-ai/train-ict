from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from pathlib import Path
import logging
import yaml
from enum import Enum

from ict_agent.knowledge.schema import ICTGraphInternal, ConceptType

logger = logging.getLogger(__name__)


@dataclass
class TradeDecision:
    """Standardized decision output from the reasoner."""

    go_no_go: bool = False
    recommendation: Optional[str] = None  # e.g., "Silver Bullet"
    recommended_model_name: Optional[str] = None  # For compatibility
    score: float = 0.0  # Normalized 0-10
    score_raw: float = 0.0  # Raw score
    confidence: float = 0.0
    confluence_factors: Dict[str, float] = field(default_factory=dict)
    red_flags: List[str] = field(default_factory=list)
    missing_prerequisites: List[str] = field(default_factory=list)
    explanation: List[str] = field(default_factory=list)
    model_scores: Dict[str, float] = field(default_factory=dict)

    # Aliases for VexCoreEngine compatibility
    @property
    def model(self):
        # Return Enum-like object if needed, or just the string ID
        # VexCoreEngine expects an Enum or string it can map.
        from ict_agent.core.vex_core_engine import ModelType

        if self.recommendation:
            try:
                # Try to map known strings to ModelType
                if "silver_bullet" in self.recommendation:
                    return ModelType.MODEL_12  # Approx
                if "judas" in self.recommendation:
                    return ModelType.TURTLE_SOUP
                if "ote" in self.recommendation:
                    return ModelType.STANDARD
                # Default fallback
                return ModelType.STANDARD
            except:
                pass
        return None

    @property
    def missing(self):
        return self.missing_prerequisites

    @property
    def confluences(self):
        return list(self.confluence_factors.keys())


class GraphReasoner:
    """
    Native VEX Reasoner using the Canonical ICT Schema.
    Evaluates market signals against the Knowledge Graph rules.
    """

    def __init__(self, graph: Optional[ICTGraphInternal] = None):
        self.graph = graph or ICTGraphInternal()
        self.weights_config = {}

    @classmethod
    def from_knowledge_base(cls, kb_root: Path) -> "GraphReasoner":
        """Factory: Loads graph from standard locations."""
        yaml_path = kb_root / "concept_relationships.yaml"
        concepts_dir = kb_root / "concepts"

        logger.info(f"Loading Knowledge Graph from {yaml_path}")
        graph = ICTGraphInternal.from_yaml(yaml_path)
        graph.enrich_from_directory(concepts_dir)

        # Enrich with ontology and terminology if available
        ontology_path = kb_root.parent / "data" / "schemas" / "ict_ontology.yaml"
        if ontology_path.exists():
            graph.enrich_from_ontology(ontology_path)
        terminology_path = kb_root / "definitions" / "terminology.yaml"
        if terminology_path.exists():
            graph.enrich_from_terminology(terminology_path)

        # Enrich with logic flows if available
        logic_flows_path = kb_root / "logic_flows.yaml"
        if logic_flows_path.exists():
            graph.enrich_from_logic_flows(logic_flows_path)

        instance = cls(graph)

        # Try to load self-training config if it exists relative to kb_root
        # Typically config/self_training_config.yaml is ../config/ relative to knowledge_base
        config_path = kb_root.parent / "config" / "self_training_config.yaml"
        if config_path.exists():
            instance.load_weights(config_path)
        else:
            logger.warning(f"Config not found at {config_path}")

        return instance

    def load_weights(self, config_path: Path):
        """Load custom scoring weights from self_training_config.yaml"""
        try:
            with open(config_path, "r") as f:
                config = yaml.safe_load(f)

            # Extract weights
            if (
                "learning_system" in config
                and "weight_adjustment" in config["learning_system"]
            ):
                weights = config["learning_system"]["weight_adjustment"].get(
                    "initial_weights", {}
                )
                self.weights_config.update(weights)
                logger.info(f"Loaded {len(weights)} dynamic weights from config")

            # Also load base weights form models
            if "trading_models" in config:
                for model_key, data in config["trading_models"].items():
                    if "confidence_base_weight" in data:
                        # Store as 'model_name' key
                        self.weights_config[f"model_{model_key}"] = data[
                            "confidence_base_weight"
                        ]

        except Exception as e:
            logger.warning(f"Failed to load weights from {config_path}: {e}")

    def enhance_setup(
        self,
        bias,
        session_phase,
        trade_type,
        sweep_info,
        pd_arrays,
        killzone_name,
        displacement_detected,
        current_time,
    ) -> TradeDecision:
        """
        Main entry point for VexCoreEngine to request graph-based validation.
        Maps engine inputs to a signal dictionary and runs evaluation.
        """
        # 1. Map inputs to loose signal dictionary
        signals = {
            "displacement": displacement_detected,
            "liquidity_swept": sweep_info.get("occurred", False)
            if isinstance(sweep_info, dict)
            else False,
            "in_killzone": killzone_name not in ["none", "No Session", None],
            "bias_bullish": getattr(bias, "value", str(bias)) == "bullish",
            "bias_bearish": getattr(bias, "value", str(bias)) == "bearish",
            "session_phase": getattr(session_phase, "value", str(session_phase)),
            "patterns": [],
        }

        # Add PD Arrays to patterns list
        if pd_arrays:
            for p in pd_arrays:
                signals["patterns"].append(p.type)  # e.g. "fvg", "order_block"

        # 2. Add implied signals
        if signals["displacement"] and signals["liquidity_swept"]:
            signals["market_structure_shift"] = True

        # 3. Add Killzone specifics
        if signals["in_killzone"]:
            signals["killzone_active"] = True

        return self.evaluate(signals)

    def evaluate(self, signals: Dict[str, Any]) -> TradeDecision:
        """
        Evaluate current market signals against all known Models in the graph.
        Returns the best matching model and a Go/No-Go decision.
        """
        best_model = None
        best_score = -1.0
        decision = TradeDecision()

        # 1. Identify Candidate Models
        # Iterate over all nodes of type 'model'
        for node in self.graph.nodes.values():
            if node.type != ConceptType.MODEL:
                continue

            score, missing, reasons, factors = self._score_model(node.id, signals)
            decision.model_scores[node.id] = score

            if score > best_score:
                best_score = score
                best_model = node.id
                decision.missing_prerequisites = missing
                decision.explanation = reasons
                decision.confluence_factors = factors
                decision.score_raw = score
                decision.recommended_model_name = node.label  # e.g. "Silver Bullet"

        # 2. Check Anti-Patterns (Global Red Flags)
        # TODO: Implement global anti-pattern check logic
        # For now, simplistic check:
        if not signals.get("displacement", False):
            decision.red_flags.append("No Displacement detected")
        if not signals.get("liquidity_swept", False):
            decision.red_flags.append("No Liquidity Sweep detected")

        # 3. Final Decision
        # Threshold: Score > 25.0 (arbitrary high score based on weights) and no critical red flags
        decision.recommendation = best_model
        # Rough Go/No-Go logic
        decision.go_no_go = (best_score >= 20.0) and (len(decision.red_flags) == 0)

        # Calculate Confidence (normalized 0-1)
        # Assuming max practical score is around 100
        decision.confidence = min(max(best_score / 80.0, 0.0), 1.0)

        return decision

    def _score_model(
        self, model_id: str, signals: Dict
    ) -> tuple[float, List[str], List[str], Dict[str, float]]:
        """
        Score a specific model based on its graph requirements.
        Returns: (score, missing_reqs, explanation_log, confluence_factors)
        """
        score = 0.0
        missing = []
        log = []
        factors = {}

        # Base weight for the model itself (from config)
        # Check explicit config key first (e.g. 'model_silver_bullet')
        # Fallback to a default weight
        base_weight = self.weights_config.get(f"model_{model_id}", 10.0)
        score += base_weight
        factors["base_model_value"] = base_weight

        # Get edges starting from this model
        requirements = [
            e
            for e in self.graph.edges
            if e.source_id == model_id and e.relation_type == "requires"
        ]
        time_windows = [
            e
            for e in self.graph.edges
            if e.source_id == model_id and e.relation_type == "active_during"
        ]

        # 1. Check Requirements
        for req in requirements:
            req_id = req.target_id

            # Map clean IDs to signals
            is_met = False

            # Direct pattern match
            if req_id in signals.get("patterns", []):
                is_met = True

            # Detailed signal map
            elif req_id == "displacement" and signals.get("displacement"):
                is_met = True
            elif req_id == "liquidity_sweep" and signals.get("liquidity_swept"):
                is_met = True
            elif req_id == "market_structure_shift" and signals.get(
                "market_structure_shift"
            ):
                is_met = True
            elif req_id == "fair_value_gap" and "fvg" in signals.get("patterns", []):
                is_met = True
            elif req_id == "order_block" and "ob" in signals.get("patterns", []):
                is_met = True

            # Determine weight: Config override > Graph weight > Default
            # Look for config weight for the REQUIREMENT (e.g. 'displacement': 10)
            weight = self.weights_config.get(req_id, req.weight)

            if is_met:
                score += weight
                factors[req_id] = weight
                log.append(f"✅ Met Requirement: {req_id} (+{weight})")
            else:
                missing.append(req_id)
                log.append(f"❌ Missing Requirement: {req_id}")

        # 2. Check Time Windows
        for tw in time_windows:
            if signals.get("in_killzone"):
                weight = self.weights_config.get("killzone_active", tw.weight)
                score += weight
                factors["time_window"] = weight
                log.append(f"✅ Time Window Aligned (+{weight})")

        return score, missing, log, factors
