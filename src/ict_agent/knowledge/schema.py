from enum import Enum
from typing import List, Dict, Optional, Any, Set
from pydantic import BaseModel, Field
import yaml
import json
from pathlib import Path


class ConceptType(str, Enum):
    CONCEPT = "concept"
    MODEL = "model"
    TIME_WINDOW = "time_window"
    KILLZONE = "killzone"
    ANTI_PATTERN = "anti_pattern"
    RULE = "rule"
    CONFLUENCE = "confluence_factor"
    SYSTEM = "system"
    CATEGORY = "category"
    LOGIC_FLOW = "logic_flow"
    SEQUENCE_STEP = "sequence_step"
    PAIR = "pair"


class ICTNode(BaseModel):
    """
    Represents a single node in the ICT Knowledge Graph.
    This schema unifies entries from YAML, JSON, and Markdown sources.
    """

    id: str = Field(..., description="Unique identifier (snake_case)")
    label: str = Field(..., description="Human-readable label")
    type: ConceptType = Field(default=ConceptType.CONCEPT)
    description: str = Field(
        default="", description="Detailed definition or explanation"
    )
    source: Optional[str] = Field(
        None, description="Source file or origin (e.g. 'transcript', 'yaml')"
    )
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Flexible metadata storage (e.g. time ranges, weights)",
    )

    class Config:
        use_enum_values = True


class ICTRelationship(BaseModel):
    """
    Represents a directed edge between two ICT nodes.
    """

    source_id: str
    target_id: str
    relation_type: str = Field(
        ..., description="e.g. 'requires', 'related_to', 'part_of'"
    )
    weight: float = Field(
        default=1.0, description="Strength or importance of the relationship"
    )
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SequenceStep(BaseModel):
    id: str
    order: int
    concept_id: str
    action: str
    validation: str = ""
    metadata: Dict[str, Any] = Field(default_factory=dict)


class LogicFlow(BaseModel):
    id: str
    name: str
    description: str = ""
    steps: List[SequenceStep] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ICTGraphInternal(BaseModel):
    """
    Internal Canonical Representation of the Knowledge Graph.
    Used for export, visualization, and reasoning.
    """

    nodes: Dict[str, ICTNode] = Field(default_factory=dict)
    edges: List[ICTRelationship] = Field(default_factory=list)
    flows: Dict[str, LogicFlow] = Field(default_factory=dict)
    generated_at: str = Field(default_factory=str)
    version: str = "1.0.0"

    def add_node(self, node: ICTNode):
        if node.id not in self.nodes:
            self.nodes[node.id] = node
        else:
            # Merge logic: verify if we want to overwrite description
            existing = self.nodes[node.id]
            if not existing.description and node.description:
                existing.description = node.description
            existing.metadata.update(node.metadata)

    def add_edge(
        self,
        source: str,
        target: str,
        type: str,
        weight: float = 1.0,
        metadata: Dict = None,
    ):
        self.edges.append(
            ICTRelationship(
                source_id=source,
                target_id=target,
                relation_type=type,
                weight=weight,
                metadata=metadata or {},
            )
        )

    @classmethod
    def from_yaml(cls, yaml_path: Path) -> "ICTGraphInternal":
        """Load graph from the canonical concept_relationships.yaml file.

        Parses all sections:
          - models: trade setup blueprints
          - concept_requirements: dependency graph (requires, enhanced_by, invalidated_by)
          - causal_chains: sequential step chains (reversal_sequence, power_of_3, etc.)
          - time_rules: killzones, macros, avoid_times
          - confluence_weights: scoring system
          - anti_patterns: common mistakes
          - pd_array_taxonomy: PD array hierarchy and is_a relationships
          - pair_rules: currency pair metadata and correlations
        """
        graph = cls()
        if not yaml_path.exists():
            return graph

        with open(yaml_path, "r") as f:
            data = yaml.safe_load(f) or {}

        # 1. Models
        for model_id, info in data.get("models", {}).items():
            graph.add_node(
                ICTNode(
                    id=model_id,
                    label=model_id.replace("_", " ").title(),
                    type=ConceptType.MODEL,
                    description=info.get("description", ""),
                    source="yaml",
                    metadata={
                        k: v
                        for k, v in info.items()
                        if k
                        not in (
                            "description",
                            "required",
                            "time_windows",
                            "anti_patterns",
                        )
                    },
                )
            )
            # Requirements — handle both string list and dict list
            for req in info.get("required", []):
                if isinstance(req, str):
                    graph.add_edge(model_id, req, "requires", weight=2.0)
                # If req is a dict (shouldn't be for models, but defensive)
            # Time Windows
            for tw in info.get("time_windows", []):
                tw_id = f"tw_{tw['name'].lower().replace(' ', '_')}"
                graph.add_node(
                    ICTNode(
                        id=tw_id,
                        label=tw["name"],
                        type=ConceptType.TIME_WINDOW,
                        description=tw.get("time", ""),
                        source="yaml",
                        metadata={
                            "time": tw.get("time", ""),
                            "timezone": tw.get("timezone", ""),
                        },
                    )
                )
                graph.add_edge(model_id, tw_id, "active_during", weight=1.5)
            # Anti-Patterns
            for ap in info.get("anti_patterns", []):
                graph.add_edge(model_id, ap, "avoids", weight=1.0)

        # 2. Concept Requirements (with enhanced_by, invalidated_by, targets)
        for concept_id, info in data.get("concept_requirements", {}).items():
            # Build description from definition or other fields
            desc = info.get("definition", "")
            if not desc and info.get("key_insight"):
                desc = info["key_insight"]

            graph.add_node(
                ICTNode(
                    id=concept_id,
                    label=concept_id.replace("_", " ").title(),
                    type=ConceptType.CONCEPT,
                    description=desc,
                    source="yaml",
                    metadata={
                        k: v
                        for k, v in info.items()
                        if k
                        in (
                            "entry_rules",
                            "zone",
                            "sweet_spot",
                            "usage",
                            "types",
                            "forms",
                            "behavior",
                            "elements",
                            "identification",
                            "sequence",
                            "condition",
                            "signal",
                            "weight",
                            "without_displacement",
                            "indicates",
                        )
                    },
                )
            )
            # requires edges
            for req in info.get("requires", []):
                if isinstance(req, dict):
                    target = req.get("concept", "")
                    if target:
                        graph.add_edge(
                            concept_id,
                            target,
                            "requires",
                            weight=1.0,
                            metadata={"reason": req.get("why", "")},
                        )
                elif isinstance(req, str):
                    graph.add_edge(concept_id, req, "requires", weight=1.0)
            # enhanced_by edges
            for enh in info.get("enhanced_by", []):
                if isinstance(enh, dict):
                    target = enh.get("concept", "")
                    if target:
                        graph.add_edge(
                            concept_id,
                            target,
                            "enhanced_by",
                            weight=enh.get("bonus", 1.0),
                            metadata={"reason": enh.get("why", "")},
                        )
            # invalidated_by edges
            for inv in info.get("invalidated_by", []):
                if isinstance(inv, dict):
                    condition = inv.get("condition", "")
                    if condition:
                        graph.add_edge(
                            concept_id,
                            condition,
                            "invalidated_by",
                            weight=1.0,
                            metadata={"reason": inv.get("why", "")},
                        )
            # targets edges
            for tgt in info.get("targets", []):
                if isinstance(tgt, dict):
                    target = tgt.get("concept", "")
                    if target:
                        graph.add_edge(
                            concept_id,
                            target,
                            "targets",
                            weight=1.0,
                            metadata={"reason": tgt.get("why", "")},
                        )
            # creates edges (displacement -> fvg, order_block)
            for cr in info.get("creates", []):
                if isinstance(cr, dict):
                    target = cr.get("concept", "")
                    if target:
                        graph.add_edge(
                            concept_id,
                            target,
                            "creates",
                            weight=1.5,
                            metadata={"likelihood": cr.get("likelihood", "")},
                        )

        # 3. Causal Chains
        for chain_id, chain_info in data.get("causal_chains", {}).items():
            flow_node_id = f"chain_{chain_id}"
            graph.add_node(
                ICTNode(
                    id=flow_node_id,
                    label=chain_id.replace("_", " ").title(),
                    type=ConceptType.LOGIC_FLOW,
                    description=chain_info.get("description", ""),
                    source="yaml",
                    metadata={
                        "key_insight": chain_info.get("key_insight", ""),
                        "failure_mode": chain_info.get("failure_mode", ""),
                        "failure_at_step": chain_info.get("failure_at_step", {}),
                    },
                )
            )
            # Build sequential step edges
            steps = chain_info.get("steps", {})
            sorted_keys = sorted(
                steps.keys(),
                key=lambda k: int(k) if isinstance(k, int) or str(k).isdigit() else k,
            )
            prev_step_id = None
            for idx, step_key in enumerate(sorted_keys):
                step = steps[step_key]
                if not isinstance(step, dict):
                    continue
                step_id = f"{chain_id}_step_{step_key}"
                # Use concept, phase, or action as label
                label = step.get(
                    "concept", step.get("phase", step.get("action", f"Step {step_key}"))
                )
                graph.add_node(
                    ICTNode(
                        id=step_id,
                        label=f"{step_key}. {label}",
                        type=ConceptType.SEQUENCE_STEP,
                        description=step.get("signal", step.get("action", "")),
                        source="yaml",
                        metadata=step,
                    )
                )
                # Link chain -> first step
                if idx == 0:
                    graph.add_edge(flow_node_id, step_id, "starts_with", weight=2.0)
                # Sequential links
                if prev_step_id:
                    graph.add_edge(prev_step_id, step_id, "leads_to", weight=2.0)
                # Link step to concept node if it exists
                concept_ref = step.get("concept")
                if concept_ref and concept_ref in graph.nodes:
                    graph.add_edge(step_id, concept_ref, "references", weight=1.0)
                prev_step_id = step_id

        # 4. Time Rules
        time_rules = data.get("time_rules", {})
        # 4a. Killzones
        for kz_id, kz_info in time_rules.get("killzones", {}).items():
            node_id = f"kz_{kz_id}"
            graph.add_node(
                ICTNode(
                    id=node_id,
                    label=f"{kz_id.replace('_', ' ').title()} Killzone",
                    type=ConceptType.KILLZONE,
                    description=kz_info.get("behavior", ""),
                    source="yaml",
                    metadata={
                        "time": kz_info.get("time", ""),
                        "trade_style": kz_info.get("trade_style", ""),
                        "best_setups": kz_info.get("best_setups", []),
                        "liquidity_builds": kz_info.get("liquidity_builds", []),
                    },
                )
            )
            # Link killzone to its best setups
            for setup in kz_info.get("best_setups", []):
                if setup in graph.nodes:
                    graph.add_edge(node_id, setup, "best_for", weight=1.5)
        # 4b. Macro Times
        for macro in time_rules.get("macros", []):
            m_id = f"macro_{macro['name'].split()[0].replace(':', '')}"
            graph.add_node(
                ICTNode(
                    id=m_id,
                    label=macro["name"],
                    type=ConceptType.TIME_WINDOW,
                    description=macro.get("action", ""),
                    source="yaml",
                )
            )

        # 5. Anti-Patterns
        for ap_id, info in data.get("anti_patterns", {}).items():
            graph.add_node(
                ICTNode(
                    id=ap_id,
                    label=ap_id.replace("_", " ").title(),
                    type=ConceptType.ANTI_PATTERN,
                    description=info.get("description", ""),
                    source="yaml",
                    metadata={
                        "fix": info.get("fix", ""),
                        "why_fails": info.get("why_fails", ""),
                        "symptom": info.get("symptom", ""),
                    },
                )
            )

        # 6. PD Array Taxonomy
        pd_tax = data.get("pd_array_taxonomy", {})
        if pd_tax:
            graph.add_node(
                ICTNode(
                    id="pd_array",
                    label="PD Array",
                    type=ConceptType.CATEGORY,
                    description=pd_tax.get("definition", ""),
                    source="yaml",
                    metadata={
                        "hierarchy": pd_tax.get("hierarchy", []),
                        "premium_arrays": pd_tax.get("premium_arrays", []),
                        "discount_arrays": pd_tax.get("discount_arrays", []),
                    },
                )
            )
            # is_a relationships
            for rel in pd_tax.get("type_relationships", []):
                source = rel.get("source", "").lower().replace(" ", "_")
                target = rel.get("target", "").lower().replace(" ", "_")
                if source and target:
                    graph.add_edge(source, target, rel.get("type", "is_a"), weight=1.0)

        # 7. Pair Rules
        for pair_id, pair_info in data.get("pair_rules", {}).items():
            node_id = f"pair_{pair_id.lower()}"
            graph.add_node(
                ICTNode(
                    id=node_id,
                    label=pair_id,
                    type=ConceptType.PAIR,
                    description=pair_info.get("characteristics", ""),
                    source="yaml",
                    metadata={
                        "correlations": pair_info.get("correlations", []),
                        "best_sessions": pair_info.get("best_sessions", []),
                        "smt_partner": pair_info.get("smt_partner", ""),
                        "typical_daily_range": pair_info.get("typical_daily_range", ""),
                        "warning": pair_info.get("warning", ""),
                    },
                )
            )

        return graph

        with open(yaml_path, "r") as f:
            data = yaml.safe_load(f) or {}

        # 1. Models
        for model_id, info in data.get("models", {}).items():
            graph.add_node(
                ICTNode(
                    id=model_id,
                    label=model_id.replace("_", " ").title(),
                    type=ConceptType.MODEL,
                    description=info.get("description", ""),
                    source="yaml",
                )
            )
            # Requirements
            for req in info.get("required", []):
                graph.add_edge(model_id, req, "requires", weight=2.0)
            # Time Windows
            for tw in info.get("time_windows", []):
                tw_id = f"tw_{tw['name'].lower().replace(' ', '_')}"
                graph.add_node(
                    ICTNode(
                        id=tw_id,
                        label=tw["name"],
                        type=ConceptType.TIME_WINDOW,
                        description=tw["time"],
                        metadata={"time": tw["time"]},
                    )
                )
                graph.add_edge(model_id, tw_id, "active_during", weight=1.5)
            # Anti-Patterns
            for ap in info.get("anti_patterns", []):
                graph.add_edge(model_id, ap, "avoids", weight=1.0)

        # 2. Concept Requirements
        for concept_id, info in data.get("concept_requirements", {}).items():
            graph.add_node(
                ICTNode(
                    id=concept_id,
                    label=concept_id.replace("_", " ").title(),
                    type=ConceptType.CONCEPT,
                    source="yaml",
                )
            )
            requires_list = info.get("requires", [])
            # Handle list of dicts or strings
            for req in requires_list:
                if isinstance(req, dict):
                    target = req.get("concept")
                    meta = {"reason": req.get("why")}
                else:
                    target = req
                    meta = {}
                graph.add_edge(
                    concept_id, target, "requires", weight=1.0, metadata=meta
                )

        # 3. Macro Times
        for macro in data.get("time_rules", {}).get("macros", []):
            m_id = f"macro_{macro['name'].split()[0].replace(':', '')}"
            graph.add_node(
                ICTNode(
                    id=m_id,
                    label=macro["name"],
                    type=ConceptType.TIME_WINDOW,
                    description=macro.get("action", ""),
                    source="yaml",
                )
            )

        # 4. Anti-Patterns
        for ap_id, info in data.get("anti_patterns", {}).items():
            graph.add_node(
                ICTNode(
                    id=ap_id,
                    label=ap_id.replace("_", " ").title(),
                    type=ConceptType.ANTI_PATTERN,
                    description=info.get("description", ""),
                    metadata={
                        "fix": info.get("fix", ""),
                        "why_fails": info.get("why_fails", ""),
                    },
                )
            )

        return graph

    def enrich_from_ontology(self, yaml_path: Path):
        """
        Ingest ict_ontology.yaml — the comprehensive ICT vocabulary.
        Creates/updates concept nodes with definitions from each ontology category.
        Ontology categories: market_context, structures, liquidity, pd_arrays,
        time_and_sessions, analysis_techniques, trade_management, etc.
        """
        if not yaml_path.exists():
            return

        with open(yaml_path, "r") as f:
            data = yaml.safe_load(f) or {}

        # Skip top-level metadata keys
        skip_keys = {"version", "updated", "description"}

        for category, entries in data.items():
            if category in skip_keys or not isinstance(entries, dict):
                continue
            for term_id, term_info in entries.items():
                if not isinstance(term_info, dict):
                    continue
                # Build concept ID
                concept_id = term_id.lower().replace(" ", "_").replace("-", "_")
                # Extract definition/description
                definition = term_info.get("definition", "")
                if not definition:
                    # Some entries use different keys
                    definition = term_info.get(
                        "description",
                        str(term_info) if isinstance(term_info, str) else "",
                    )
                full_name = term_info.get("full_name", "")
                label = full_name if full_name else term_id.replace("_", " ").title()

                self.add_node(
                    ICTNode(
                        id=concept_id,
                        label=label,
                        type=ConceptType.CONCEPT,
                        description=definition,
                        source="ontology",
                        tags=[category],
                        metadata={
                            k: v
                            for k, v in term_info.items()
                            if k not in ("definition", "full_name")
                            and not isinstance(v, dict)
                        },
                    )
                )

    def enrich_from_terminology(self, yaml_path: Path):
        """
        Ingest terminology.yaml — the ICT glossary with aliases and detection rules.
        Creates/updates concept nodes and stores aliases, detection_rules, and
        trading_application in metadata.
        """
        if not yaml_path.exists():
            return

        with open(yaml_path, "r") as f:
            data = yaml.safe_load(f) or {}

        for term_id, term_info in data.get("terms", {}).items():
            if not isinstance(term_info, dict):
                continue
            concept_id = term_id.lower().replace(" ", "_").replace("-", "_")
            full_name = term_info.get("full_name", "")
            label = full_name if full_name else term_id.replace("_", " ").title()
            definition = term_info.get("definition", "")

            node = ICTNode(
                id=concept_id,
                label=label,
                type=ConceptType.CONCEPT,
                description=definition,
                source="terminology",
                tags=[term_info.get("category", "")],
                metadata={
                    "aliases": term_info.get("aliases", []),
                    "detection_rules": term_info.get("detection_rules", {}),
                    "key_levels": term_info.get("key_levels", []),
                    "trading_application": term_info.get("trading_application", ""),
                    "validation": term_info.get("validation", ""),
                },
            )
            self.add_node(node)

            # Create edges to related_concepts
            for related in term_info.get("related_concepts", []):
                related_id = related.lower().replace(" ", "_").replace("-", "_")
                self.add_edge(concept_id, related_id, "related_to", weight=0.5)

    def enrich_from_logic_flows(self, yaml_path: Path):
        """
        Load procedural logic flows from YAML.
        Creates LogicFlow nodes and SequenceStep nodes, linking them sequentially.
        """
        if not yaml_path.exists():
            return

        with open(yaml_path, "r") as f:
            data = yaml.safe_load(f) or {}

        for flow_id, info in data.get("patterns", {}).items():
            # 1. Create the Flow Node (The "Parent")
            flow_node_id = f"flow_{flow_id}"

            # Add Flow node
            self.add_node(
                ICTNode(
                    id=flow_node_id,
                    label=str(info.get("name", flow_id)),  # Ensure string label
                    type=ConceptType.LOGIC_FLOW,
                    description=str(info.get("context", "")),
                    source="logic_flows_yaml",
                )
            )

            steps = []
            sequence_data = info.get("sequence", {})

            # Sort keys to ensure order (assuming keys like 1_step, 2_step)
            # We want string sorting but "10_" should come after "2_"
            # For now, simple string sort works if users use "01_", "02_" or single digits
            sorted_keys = sorted(sequence_data.keys())

            previous_step_id = None

            for idx, step_key in enumerate(sorted_keys):
                step_info = sequence_data[step_key]
                if not isinstance(step_info, dict):
                    continue

                # 2. Create the Step Node
                # Clean key: "1_erl_capture" -> "Erl Capture"
                clean_name = (
                    step_key.split("_", 1)[1].replace("_", " ").title()
                    if "_" in step_key
                    else step_key
                )
                step_node_id = f"{flow_id}_step_{idx + 1}"
                step_label = f"{idx + 1}. {clean_name}"

                self.add_node(
                    ICTNode(
                        id=step_node_id,
                        label=step_label,
                        type=ConceptType.SEQUENCE_STEP,
                        description=str(step_info.get("validation", str(step_info))),
                        metadata=step_info,
                    )
                )

                # Link Flow -> Step 1 (Start)
                if idx == 0:
                    self.add_edge(flow_node_id, step_node_id, "starts_with", weight=2.0)

                # Link Step N -> Step N+1 (Sequence)
                if previous_step_id:
                    self.add_edge(
                        previous_step_id, step_node_id, "leads_to", weight=2.0
                    )

                # Link Step -> Related Concept (Graph Connection)
                concept_ref = step_info.get("concept")
                if concept_ref:
                    # Check graph for concept
                    if concept_ref in self.nodes:
                        self.add_edge(
                            step_node_id, concept_ref, "engine_uses", weight=1.0
                        )

                previous_step_id = step_node_id

    def enrich_from_directory(self, directory: Path):
        """
        Scan a directory of markdown files.
        Parses headers (H1-H6) to identify multiple concepts within a single file.
        Matches header text to node IDs (e.g. "3. Fair Value Gaps" -> "fair_value_gap").
        """
        if not directory.exists():
            print(f"Warning: Directory {directory} not found.")
            return

        for md_file in directory.glob("*.md"):
            self.enrich_from_file(md_file)

    def enrich_from_file(self, file_path: Path):
        """
        Ingest a single markdown file into the graph.
        Parses headers to identify concepts and updates/creates nodes.
        """
        if not file_path.exists():
            print(f"Warning: File {file_path} not found.")
            return

        import re

        # Regex for headers: # ... ######
        header_pattern = re.compile(r"^(#{1,6})\s+(.+)$")
        # Regex to strip leading numbering "1. ", "2.3 ", "IV. "
        clean_pattern = re.compile(r"^(\d+\.|[IVX]+\.)\s+")

        try:
            content = file_path.read_text(encoding="utf-8")
            # Calculate relative path for frontend - Assuming standard structure
            # We try to make it relative to the knowledge_base root if possible
            try:
                # heuristic to find relative path from project root
                parts = file_path.parts
                if "knowledge_base" in parts:
                    kb_index = parts.index("knowledge_base")
                    rel_path = f"../../knowledge_base/{'/'.join(parts[kb_index + 1 :])}"
                else:
                    rel_path = f"../../{file_path.name}"
            except ValueError:
                rel_path = f"../../{file_path.name}"

            # Default: File itself is a concept node (if name is meaningful)
            file_concept_id = file_path.stem.lower().replace(" ", "_")

            # Update file node if exists
            if file_concept_id in self.nodes:
                self.nodes[file_concept_id].metadata["file_path"] = rel_path

            lines = content.splitlines()
            current_concept = file_concept_id
            current_text = []

            def match_concept_id(text: str) -> str:
                """Try to map header text to an existing or valid concept ID."""
                # 1. Clean numbering
                clean = clean_pattern.sub("", text.strip())
                # 2. Strict ID generation
                strict_id = (
                    clean.lower()
                    .replace(" ", "_")
                    .replace("/", "_")
                    .replace("-", "_")
                    .replace("(", "")
                    .replace(")", "")
                )

                # 3. Check against existing nodes (Exact Match)
                if strict_id in self.nodes:
                    return strict_id

                # 4. Check against existing nodes (Fuzzy / Substring)
                # "Fair Value Gaps (FVGs)" -> matches "fair_value_gap"
                clean_lower = clean.lower()
                for node_id, node in self.nodes.items():
                    # Standardize node label for comparison
                    node_label = node.label.lower()
                    # If node label/id is contained in header, or header in node label
                    if (
                        node_label in clean_lower
                        or node_id.replace("_", " ") in clean_lower
                    ):
                        # Prefer exact word matches if possible
                        return node_id

                return strict_id

            def save_concept(cid, text_lines):
                if not text_lines:
                    return
                desc = ""
                for l in text_lines:
                    if l.strip() and not l.startswith("#"):
                        desc = l.strip()
                        break

                if not desc:
                    return

                # Update existing node
                if cid in self.nodes:
                    node = self.nodes[cid]
                    # Only update if description is missing or looks like a placeholder
                    if (
                        not node.description
                        or len(desc) > len(node.description)
                        or "no description" in node.description.lower()
                    ):
                        node.description = desc
                    node.source = "markdown+yaml"
                    if "file_path" not in node.metadata:
                        node.metadata["file_path"] = rel_path
                    if cid != file_concept_id:
                        node.metadata["file_anchor"] = cid

                # Create new node
                elif cid not in ("introduction", "summary", "conclusion", "references"):
                    # Avoid creating nodes for generic headers if they don't look like concepts
                    if len(cid) > 3:
                        self.add_node(
                            ICTNode(
                                id=cid,
                                label=cid.replace("_", " ").title(),
                                type=ConceptType.CONCEPT,
                                description=desc,
                                source="markdown",
                                metadata={"file_path": rel_path, "file_anchor": cid},
                            )
                        )

            for line in lines:
                match = header_pattern.match(line)
                if match:
                    save_concept(current_concept, current_text)

                    header_text = match.group(2).strip()
                    current_concept = match_concept_id(header_text)
                    current_text = []
                else:
                    current_text.append(line)

            save_concept(current_concept, current_text)

        except Exception as e:
            print(f"Error reading {file_path}: {e}")

    def to_d3_json(self) -> Dict[str, Any]:
        """Export to format expected by force-graph library."""
        output = {"nodes": [], "links": []}

        for node in self.nodes.values():
            output["nodes"].append(
                {
                    "id": node.id,
                    "label": node.label,
                    "group": node.type,
                    "type": node.type,
                    "description": node.description,
                    "rel_path": node.metadata.get("file_path", ""),
                    "metadata": node.metadata,
                }
            )

        for edge in self.edges:
            # Ensure both source and target exist
            if edge.source_id in self.nodes and edge.target_id in self.nodes:
                output["links"].append(
                    {
                        "source": edge.source_id,
                        "target": edge.target_id,
                        "label": edge.relation_type,
                        "value": edge.weight,
                        "metadata": edge.metadata,
                    }
                )

        return output
