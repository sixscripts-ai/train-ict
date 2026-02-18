"""
DEPRECATED — 2026-02-17
=======================
This script originally generated `data/schemas/concept_relationships_expanded.yaml`.
That file has been deleted and its content merged into the canonical source of truth:

    knowledge_base/concept_relationships.yaml

All ICT concept relationships, PD array taxonomy, entry models, risk management,
and IPDA data ranges now live in the canonical file. Edit that file directly
instead of running this generator.

If you need to regenerate training data from the canonical file, use:
    scripts/clean_and_merge_training_data.py
"""

import yaml
import copy
import sys

# Original basic structure to start with
BASE_YAML = {
    "version": "2.0",
    "last_updated": "2026-02-17",
    "description": "Expanded ICT Concept Relationships with 5x density",
    "concepts": {},
}

# New Expanded Concepts Dictionary
NEW_CONCEPTS = {
    "PD_Arrays": {
        "definition": "Premium/Discount Arrays - The tools used to frame setup",
        "hierarchy": [
            "Mitigation Block",
            "Breaker Block",
            "Liquidity Void",
            "Fair Value Gap",
            "Order Block",
            "Rejection Block",
            "Old High/Low",
        ],
        "premium_arrays": ["Bearish OB", "Bearish Breaker", "Bearish FVG", "Old High"],
        "discount_arrays": ["Bullish OB", "Bullish Breaker", "Bullish FVG", "Old Low"],
    },
    "Liquidity": {
        "types": [
            "Buy Side (BSL)",
            "Sell Side (SSL)",
            "Internal Range (IRL)",
            "External Range (ERL)",
        ],
        "forms": [
            "Equal Highs (EQH)",
            "Equal Lows (EQL)",
            "Trendline Liquidity",
            "Previous Day High/Low",
            "Previous Week High/Low",
        ],
        "action": "Price seeks liquidity to manipulate or fuel a move",
    },
    "Market_Structure": {
        "elements": [
            "Swing High",
            "Swing Low",
            "Intermediate Term High (ITH)",
            "Intermediate Term Low (ITL)",
            "Long Term High (LTH)",
            "Long Term Low (LTL)",
        ],
        "shifts": [
            "Market Structure Shift (MSS)",
            "Break of Structure (BOS)",
            "Change of Character (CHoCH)",
        ],
        "condition": "Displacement is required to confirm a valid shift",
    },
    "Time_and_Price": {
        "kill_zones": [
            "London Open (2-5am NY)",
            "New York Open (7-10am NY)",
            "London Close (10am-12pm NY)",
            "Asian Range (8pm-12am NY)",
        ],
        "macros": [
            "02:33",
            "03:15",
            "04:03",
            "08:50",
            "09:50",
            "10:10",
            "10:50",
            "11:50",
            "13:10",
        ],
        "silver_bullet": ["3am-4am", "10am-11am", "2pm-3pm"],
        "opening_price": ["Midnight NY Opening Price", "8:30am NY Opening Price"],
    },
    "IPDA_Data_Ranges": {
        "ranges": ["20 Days", "40 Days", "60 Days"],
        "lookback": "Price refers to data points within these lookback periods",
    },
    "Entry_Models": {
        "2022_Model": ["Liquidity Sweep", "MSS", "Displacement", "FVG Entry"],
        "Silver_Bullet_Model": ["Time Window", "FVG", "Liquidity Target"],
        "Breaker_Model": ["Stop Hunt", "Displacement", "Return to Breaker"],
        "OTE_Model": ["Impulse", "Retracement to 62-79%", "Confluence"],
    },
    "Risk_Management": {
        "rules": [
            "1-2% per trade",
            "Stop Loss at Invalidation Point",
            "Partial at Low Hanging Fruit",
        ],
        "invalidation": "Close beyond the FVG or Swing Point implies idea is wrong",
    },
}

RELATIONSHIPS = [
    # Causal
    {
        "source": "Liquidity Sweep",
        "target": "Market Structure Shift",
        "type": "precedes",
        "reason": "Stop hunt fuels the reversal",
    },
    {
        "source": "Market Structure Shift",
        "target": "Displacement",
        "type": "requires",
        "reason": "Shift without energy is suspect",
    },
    {
        "source": "Displacement",
        "target": "Fair Value Gap",
        "type": "creates",
        "reason": "Fast moves leave imbalances",
    },
    {
        "source": "Fair Value Gap",
        "target": "Retracement",
        "type": "attracts",
        "reason": "Price returns to rebalance",
    },
    {
        "source": "Retracement",
        "target": "Entry",
        "type": "enables",
        "reason": "Provides reduced risk entry",
    },
    # Hierarchy / Composition
    {"source": "Order Block", "target": "PD Array", "type": "is_a"},
    {"source": "Fair Value Gap", "target": "PD Array", "type": "is_a"},
    {"source": "Breaker Block", "target": "PD Array", "type": "is_a"},
    {"source": "Mitigation Block", "target": "PD Array", "type": "is_a"},
    # Time
    {
        "source": "London Open",
        "target": "Judas Swing",
        "type": "often_contains",
        "reason": "Standard manipulation time",
    },
    {
        "source": "New York Open",
        "target": "Trend Continuation",
        "type": "often_provides",
        "reason": "NY often continues London or Reverses",
    },
    # Invalidation
    {
        "source": "Candle Close Beyond FVG",
        "target": "FVG Setup",
        "type": "invalidates",
        "reason": "Respect implies wicks only bodies tell the story",
    },
    {
        "source": "SMT Divergence",
        "target": "Validation",
        "type": "provides",
        "reason": "Cracks in correlation confirm move",
    },
]


def expand_yaml():
    data = copy.deepcopy(BASE_YAML)
    data["concepts"] = NEW_CONCEPTS
    data["relationships"] = RELATIONSHIPS

    # Logic to multiply density (simulated 5x expansion via permutation for specific sub-attributes)
    # We will generate specific "scenario" relationships

    scenarios = []

    # Scenario Generation 1: PD Array interactions
    for pda in NEW_CONCEPTS["PD_Arrays"]["hierarchy"]:
        for bias in ["Bullish", "Bearish"]:
            scenarios.append(
                {
                    "source": f"{bias} {pda}",
                    "target": "Price Reaction",
                    "type": "anticipates",
                    "context": f"When bias is {bias}, expect support/resistance at {pda}",
                }
            )

    # Scenario Generation 2: Time x Concept
    for zone in NEW_CONCEPTS["Time_and_Price"]["kill_zones"]:
        for model in NEW_CONCEPTS["Entry_Models"].keys():
            scenarios.append(
                {
                    "source": zone,
                    "target": model,
                    "type": "contextualizes",
                    "reason": f"{model} has higher probability during {zone}",
                }
            )

    data["scenarios"] = scenarios

    return data


if __name__ == "__main__":
    print("⚠️  DEPRECATED: This script is no longer needed.")
    print(
        "   All content has been merged into: knowledge_base/concept_relationships.yaml"
    )
    print(
        "   Use scripts/clean_and_merge_training_data.py for training data generation."
    )
    print()

    resp = input("Run anyway for reference? (y/N): ").strip().lower()
    if resp != "y":
        sys.exit(0)

    expanded_data = expand_yaml()

    import os

    # Get the directory of the current script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # Output now goes to canonical location (will NOT overwrite — writes to a temp file)
    output_path = os.path.join(
        script_dir, "../data/schemas/concept_relationships_expanded_GENERATED.yaml"
    )

    # Ensure directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, "w") as f:
        yaml.dump(expanded_data, f, sort_keys=False, default_flow_style=False)

    print(f"Generated expanded concept relationships in {output_path}")
    print(
        "NOTE: This is a reference copy. The canonical file is knowledge_base/concept_relationships.yaml"
    )
