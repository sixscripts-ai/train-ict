import json
import random
import re

# ICT Terminology Mapping
ICT_TERMS = {
    "Fair Value Gap": ["FVG", "Imbalance", "Inefficiency"],
    "Order Block": ["OB", "Block"],
    "Breaker Block": ["BB", "Breaker"],
    "Mitigation Block": ["MB", "Mitigation"],
    "Liquidity Void": ["LV", "Void"],
    "Buy Side Liquidity": ["BSL", "Buy Side"],
    "Sell Side Liquidity": ["SSL", "Sell Side"],
    "Equal Highs": ["EQH"],
    "Equal Lows": ["EQL"],
    "Market Structure Shift": ["MSS", "sms", "shift"],
    "Break of Structure": ["BOS", "break"],
    "Change of Character": ["CHoCH"],
    "Point of Interest": ["POI"],
    "Premium Discount Array": ["PD Array"],
    "Optimal Trade Entry": ["OTE"],
    "Kill Zone": ["KZ"],
    "London Open": ["LO"],
    "New York Open": ["NYO"],
    "Asian Range": ["AR"],
    "Initial Balance": ["IB"],
    "Previous Day High": ["PDH"],
    "Previous Day Low": ["PDL"],
    "Previous Weekly High": ["PWH"],
    "Previous Weekly Low": ["PWL"],
    "Monday High": ["MonH"],
    "Monday Low": ["MonL"],
    "Return to Impulse": ["RTI"],
    "Smart Money Tool": ["SMT"],
    "Smart Money Reversal": ["SMR"],
    "Institutional Price Delivery Algorithm": ["IPDA"],
    "Interbank Price Delivery Algorithm": ["IPDA"],
    "Judas Swing": ["Judas"],
    "Power of Three": ["PO3", "AMD"],
    "Accumulation Manipulation Distribution": ["AMD"],
    "Sell Side Imbalance Buy Side Inefficiency": ["SIBI"],
    "Buy Side Imbalance Sell Side Inefficiency": ["BISI"],
    "Volume Imbalance": ["VI"],
    "Standard Deviation": ["SD", "StdDev"],
    "Consequent Encroachment": ["CE"],
    "Mean Threshold": ["MT"],
    "Rejection Block": ["RB"],
    "Propulsion Block": ["PB"],
    "Vacuum Block": ["VB"],
    "Liquidity Run": ["Run"],
    "Stop Hunt": ["SH"],
    "Turtle Soup": ["TS"],
    "Displacement": ["Speed"],
    "Expansion": ["Exp"],
    "Retracement": ["Ret"],
    "Reversal": ["Rev"],
    "Consolidation": ["Cons", "Range"],
    "Dealing Range": ["DR"],
    "Implied Fair Value Gap": ["IFVG"],
    "Inversion Fair Value Gap": ["IFVG", "Inversion"],
    "Balanced Price Range": ["BPR"],
    "Internal Range Liquidity": ["IRL"],
    "External Range Liquidity": ["ERL"],
    "Long Term High": ["LTH"],
    "Long Term Low": ["LTL"],
    "Intermediate Term High": ["ITH"],
    "Intermediate Term Low": ["ITL"],
    "Short Term High": ["STH"],
    "Short Term Low": ["STL"],
    "Swing High": ["SH"],
    "Swing Low": ["SL"]
}

TEMPLATES = [
    "Look for a {term} on the 15m chart.",
    "The price tapped into the {term} and rejected.",
    "We need to see a {term} before entering.",
    "Target the {term} for your take profit.",
    "The {term} was respected perfectly.",
    "Ignore the {term} if time of day is wrong.",
    "A valid {term} implies smart money participation.",
    "Wait for a {term} inside the kill zone.",
    "The market is drawing towards the {term}.",
    "Identify the {term} on the higher timeframe.",
    "Did you see the {term} form at the open?",
    "Use the {term} to define your risk.",
    "The {term} aligns with the bias.",
    "Watch for a reaction at the {term}.",
    "The {term} is a high probability array.",
    "After the {term}, look for an entry.",
    "The {term} confirms the narrative.",
    "Don't trade against the {term}.",
    "The {term} suggests higher prices.",
    "The {term} suggests lower prices."
]

def generate_shorthand_data(num_samples=1000):
    data = []
    
    # Flatten terms for easier access
    all_terms = list(ICT_TERMS.keys())
    
    for _ in range(num_samples):
        term = random.choice(all_terms)
        shorthand = random.choice(ICT_TERMS[term])
        template = random.choice(TEMPLATES)
        
        full_sentence = template.format(term=term)
        short_sentence = template.format(term=shorthand)
        
        # Create a training entry pair
        entry = {
            "input": f"Rewrite this using ICT shorthand: {full_sentence}",
            "output": short_sentence,
            "term": term,
            "shorthand": shorthand
        }
        data.append(entry)
        
        # Also create the reverse mapping for robustness
        entry_reverse = {
            "input": f"Expand this ICT shorthand: {short_sentence}",
            "output": full_sentence,
            "term": term,
            "shorthand": shorthand
        }
        data.append(entry_reverse)

    return data

if __name__ == "__main__":
    generated_data = generate_shorthand_data(2000)
    
    import os
    # Get the directory of the current script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # Construct absolute path for output
    output_path = os.path.join(script_dir, "../data/training/shorthand_training_data.json")
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    with open(output_path, "w") as f:
        json.dump(generated_data, f, indent=2)
        
    print(f"Generated {len(generated_data)} shorthand training examples in {output_path}")
