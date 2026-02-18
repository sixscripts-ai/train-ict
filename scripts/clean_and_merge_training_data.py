import json
import yaml
import os


def clean_and_merge():
    # Paths - using absolute paths relative to script location
    script_dir = os.path.dirname(os.path.abspath(__file__))
    shorthand_path = os.path.join(
        script_dir, "../data/training/shorthand_training_data.json"
    )
    schema_path = os.path.join(
        script_dir, "../knowledge_base/concept_relationships.yaml"
    )
    output_path = os.path.join(
        script_dir, "../data/training/final_ict_training_mix_v9.json"
    )

    final_dataset = []

    # 1. Load Shorthand Data
    if os.path.exists(shorthand_path):
        with open(shorthand_path, "r") as f:
            shorthand_data = json.load(f)
            print(f"Loaded {len(shorthand_data)} shorthand examples")

            # Add metadata tagging
            for item in shorthand_data:
                item["source"] = "shorthand_generator"
                item["type"] = "terminology_mapping"
                final_dataset.append(item)

    # 2. Load Canonical Schema and Convert to Training Pairs
    if os.path.exists(schema_path):
        with open(schema_path, "r") as f:
            schema_data = yaml.safe_load(f)

        # --- Models (entry model blueprints) ---
        models = schema_data.get("models", {})
        for model_name, details in models.items():
            if isinstance(details, dict):
                desc = details.get("description", "")
                if desc:
                    final_dataset.append(
                        {
                            "input": f"What is the {model_name.replace('_', ' ')} model in ICT?",
                            "output": desc,
                            "source": "concept_schema",
                            "type": "definition",
                        }
                    )
                required = details.get("required", [])
                if required:
                    final_dataset.append(
                        {
                            "input": f"What are the requirements for the {model_name.replace('_', ' ')} model?",
                            "output": f"The required elements are: {', '.join(required)}.",
                            "source": "concept_schema",
                            "type": "list",
                        }
                    )
                anti = details.get("anti_patterns", [])
                if anti:
                    final_dataset.append(
                        {
                            "input": f"What are the anti-patterns for the {model_name.replace('_', ' ')} model?",
                            "output": f"Avoid: {', '.join(anti)}.",
                            "source": "concept_schema",
                            "type": "anti_pattern",
                        }
                    )

        # --- Concept Requirements (relationships) ---
        concept_reqs = schema_data.get("concept_requirements", {})
        for concept, details in concept_reqs.items():
            if not isinstance(details, dict):
                continue

            # Definition if present
            defn = details.get("definition", "")
            if defn:
                final_dataset.append(
                    {
                        "input": f"What is {concept.replace('_', ' ')} in ICT trading?",
                        "output": defn,
                        "source": "concept_schema",
                        "type": "definition",
                    }
                )

            # Requires relationships
            for req in details.get("requires", []):
                if isinstance(req, dict):
                    target = req.get("concept", "")
                    why = req.get("why", "")
                    final_dataset.append(
                        {
                            "input": f"How does {concept.replace('_', ' ')} relate to {target.replace('_', ' ')}?",
                            "output": f"{concept.replace('_', ' ')} requires {target.replace('_', ' ')}. {why}",
                            "source": "relationship_schema",
                            "type": "relationship",
                        }
                    )

            # Enhanced_by
            for enh in details.get("enhanced_by", []):
                if isinstance(enh, dict):
                    target = enh.get("concept", "")
                    why = enh.get("why", "")
                    final_dataset.append(
                        {
                            "input": f"What enhances a {concept.replace('_', ' ')} setup?",
                            "output": f"{target.replace('_', ' ')} enhances {concept.replace('_', ' ')}. {why}",
                            "source": "relationship_schema",
                            "type": "relationship",
                        }
                    )

            # Invalidated_by
            for inv in details.get("invalidated_by", []):
                if isinstance(inv, dict):
                    cond = inv.get("condition", "")
                    why = inv.get("why", "")
                    final_dataset.append(
                        {
                            "input": f"What invalidates a {concept.replace('_', ' ')} setup?",
                            "output": f"{cond.replace('_', ' ')} invalidates {concept.replace('_', ' ')}. {why}",
                            "source": "relationship_schema",
                            "type": "invalidation",
                        }
                    )

            # Entry rules
            for rule in details.get("entry_rules", []):
                final_dataset.append(
                    {
                        "input": f"What are the entry rules for {concept.replace('_', ' ')}?",
                        "output": rule,
                        "source": "concept_schema",
                        "type": "entry_rule",
                    }
                )

            # List-like sub-attributes (types, forms, elements, etc.)
            for key, val in details.items():
                if isinstance(val, list) and key not in (
                    "requires",
                    "enhanced_by",
                    "invalidated_by",
                    "entry_rules",
                    "creates",
                ):
                    str_vals = [str(v) for v in val if isinstance(v, str)]
                    if str_vals:
                        final_dataset.append(
                            {
                                "input": f"List the {key} of {concept.replace('_', ' ')}.",
                                "output": f"The {key} are: {', '.join(str_vals)}.",
                                "source": "concept_schema",
                                "type": "list",
                            }
                        )

        # --- Causal Chains ---
        chains = schema_data.get("causal_chains", {})
        for chain_name, chain in chains.items():
            if not isinstance(chain, dict):
                continue
            desc = chain.get("description", "")
            steps = chain.get("steps", {})
            if desc and steps:
                step_text = " -> ".join(
                    s.get("concept", s.get("phase", s.get("action", "")))
                    for s in (steps.values() if isinstance(steps, dict) else steps)
                    if isinstance(s, dict)
                )
                final_dataset.append(
                    {
                        "input": f"Explain the {chain_name.replace('_', ' ')} sequence in ICT.",
                        "output": f"{desc}. Steps: {step_text}",
                        "source": "causal_chain",
                        "type": "sequence",
                    }
                )

        # --- Anti-Patterns ---
        anti_patterns = schema_data.get("anti_patterns", {})
        for name, details in anti_patterns.items():
            if not isinstance(details, dict):
                continue
            desc = details.get("description", "")
            why = details.get("why_fails", "")
            fix = details.get("fix", "")
            if desc:
                final_dataset.append(
                    {
                        "input": f"What is the {name.replace('_', ' ')} anti-pattern?",
                        "output": f"{desc} Why it fails: {why} Fix: {fix}",
                        "source": "anti_pattern",
                        "type": "anti_pattern",
                    }
                )

        # --- PD Array Taxonomy ---
        pd = schema_data.get("pd_array_taxonomy", {})
        if pd:
            defn = pd.get("definition", "")
            if defn:
                final_dataset.append(
                    {
                        "input": "What are PD Arrays in ICT?",
                        "output": defn,
                        "source": "concept_schema",
                        "type": "definition",
                    }
                )
            for key in ("hierarchy", "premium_arrays", "discount_arrays"):
                vals = pd.get(key, [])
                if vals:
                    final_dataset.append(
                        {
                            "input": f"What are the {key.replace('_', ' ')} of PD Arrays?",
                            "output": f"The {key.replace('_', ' ')} are: {', '.join(vals)}.",
                            "source": "concept_schema",
                            "type": "list",
                        }
                    )
            for rel in pd.get("type_relationships", []):
                if isinstance(rel, dict):
                    final_dataset.append(
                        {
                            "input": f"How does {rel['source']} relate to {rel['target']}?",
                            "output": f"{rel['source']} {rel['type']} {rel['target']}.",
                            "source": "relationship_schema",
                            "type": "relationship",
                        }
                    )

        # --- Entry Models (quick reference) ---
        entry_models = schema_data.get("entry_models", {})
        for model_name, details in entry_models.items():
            if isinstance(details, dict):
                steps = details.get("steps", [])
                if steps:
                    final_dataset.append(
                        {
                            "input": f"What are the steps for the {model_name.replace('_', ' ')} entry model?",
                            "output": f"Steps: {' -> '.join(steps)}.",
                            "source": "entry_model",
                            "type": "sequence",
                        }
                    )

        # --- Risk Management ---
        risk = schema_data.get("risk_management", {})
        if risk:
            rules = risk.get("rules", [])
            if rules:
                final_dataset.append(
                    {
                        "input": "What are the ICT risk management rules?",
                        "output": f"Rules: {'; '.join(rules)}. {risk.get('invalidation', '')}",
                        "source": "concept_schema",
                        "type": "risk_management",
                    }
                )

        # --- Pair Rules ---
        pair_rules = schema_data.get("pair_rules", {})
        for pair, details in pair_rules.items():
            if isinstance(details, dict):
                chars = details.get("characteristics", "")
                sessions = details.get("best_sessions", [])
                final_dataset.append(
                    {
                        "input": f"What should I know about trading {pair.replace('_', '/')}?",
                        "output": f"{chars}. Best sessions: {', '.join(sessions) if sessions else 'N/A'}.",
                        "source": "pair_rules",
                        "type": "pair_info",
                    }
                )

        print(f"Loaded training data from canonical schema")
    else:
        print(f"WARNING: Canonical schema not found at {schema_path}")

    # 3. Deduplicate and clean
    # Simple deduplication based on input string
    unique_data = {}
    for item in final_dataset:
        if item["input"] not in unique_data:
            unique_data[item["input"]] = item

    final_list = list(unique_data.values())

    # 4. Write Final Mix
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(final_list, f, indent=2)

    print(
        f"Final dataset created with {len(final_list)} unique entries at {output_path}"
    )


if __name__ == "__main__":
    clean_and_merge()
