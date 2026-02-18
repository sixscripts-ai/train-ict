#!/usr/bin/env python3
"""
ICT Trade Setup Validator

Validates trade setup JSON files against the ICT schema.
Also provides helpful diagnostics for common issues.

Usage:
    python validate_setup.py <file.json>           # Validate single file
    python validate_setup.py --all                 # Validate all setups
    python validate_setup.py --watch               # Watch for changes
"""

import json
import sys
import argparse
from pathlib import Path
from datetime import datetime
from typing import Optional

try:
    from jsonschema import validate, ValidationError, Draft202012Validator
    HAS_JSONSCHEMA = True
except ImportError:
    HAS_JSONSCHEMA = False
    print("Warning: jsonschema not installed. Run: pip install jsonschema")


# Paths
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
SCHEMA_PATH = PROJECT_ROOT / "data" / "schemas" / "ict_trade_setup.schema.json"
TRAINING_DIR = PROJECT_ROOT / "data" / "training"


def load_schema() -> dict:
    """Load the ICT trade setup schema"""
    if not SCHEMA_PATH.exists():
        print(f"❌ Schema not found: {SCHEMA_PATH}")
        sys.exit(1)
    
    with open(SCHEMA_PATH) as f:
        return json.load(f)


def validate_file(filepath: Path, schema: dict, verbose: bool = True) -> tuple[bool, list[str]]:
    """
    Validate a single JSON file against the schema.
    Returns (is_valid, list_of_errors)
    """
    errors = []
    
    # Check file exists
    if not filepath.exists():
        return False, [f"File not found: {filepath}"]
    
    # Load JSON
    try:
        with open(filepath) as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        return False, [f"Invalid JSON: {e}"]
        
    # Handle list of records
    if isinstance(data, list):
        all_valid = True
        for i, item in enumerate(data):
            # Skip template files in list? unlikely but possible
            if item.get("_comment") or item.get("id", "").startswith("YYYY"):
                continue
                
            item_valid, item_errors = validate_single_item(item, schema, f"Item {i}")
            if not item_valid:
                all_valid = False
                errors.extend([f"Record {i}: {e}" for e in item_errors])
        
        return all_valid, errors

    # Single item validation
    return validate_single_item(data, schema)


def validate_single_item(data: dict, schema: dict, context: str = "") -> tuple[bool, list[str]]:
    """Validate a single item dictionary"""
    errors = []
    
    # Skip template files
    if data.get("_comment") or data.get("id", "").startswith("YYYY"):
        # if verbose: print(f"⏭️  Skipped template: {context}")
        return True, []
    
    # Validate against schema
    if HAS_JSONSCHEMA:
        validator = Draft202012Validator(schema)
        for error in validator.iter_errors(data):
            path = " → ".join(str(p) for p in error.absolute_path)
            errors.append(f"{path}: {error.message}")
    
    # Custom validation rules
    custom_errors = custom_validations(data)
    errors.extend(custom_errors)
    
    return len(errors) == 0, errors


def custom_validations(data: dict) -> list[str]:
    """
    Additional ICT-specific validations beyond JSON schema.
    """
    errors = []
    
    # 1. Negative examples must have failure_analysis
    if data.get("labels", {}).get("example_type") == "negative":
        if not data.get("failure_analysis"):
            errors.append("Negative examples require 'failure_analysis' section")
        elif not data.get("failure_analysis", {}).get("root_cause"):
            errors.append("failure_analysis.root_cause is empty")
        elif not data.get("failure_analysis", {}).get("lesson_summary"):
            errors.append("failure_analysis.lesson_summary is missing")
    
    # 2. Entry price should be between stop and first target
    execution = data.get("execution", {})
    entry = execution.get("entry_price")
    stop = execution.get("stop_loss")
    targets = execution.get("targets", [])
    
    if entry and stop and targets:
        first_target = targets[0].get("price")
        if first_target:
            # For longs: stop < entry < target
            if data.get("setup", {}).get("bias") == "long":
                if not (stop < entry < first_target):
                    errors.append(f"Long trade: stop ({stop}) should be < entry ({entry}) < target ({first_target})")
            # For shorts: target < entry < stop
            elif data.get("setup", {}).get("bias") == "short":
                if not (first_target < entry < stop):
                    errors.append(f"Short trade: target ({first_target}) should be < entry ({entry}) < stop ({stop})")
    
    # 3. Risk/Reward check - use BEST target, not first
    # Skip R:R validation for negative examples (they failed for a reason)
    if entry and stop and targets:
        example_type = data.get("labels", {}).get("example_type", "positive")
        if example_type == "positive":
            risk_pips = abs(entry - stop)
            # Find best target
            best_rr = 0
            for t in targets:
                target_price = t.get("price")
                if target_price and risk_pips > 0:
                    reward_pips = abs(target_price - entry)
                    rr = reward_pips / risk_pips
                    best_rr = max(best_rr, rr)
            
            if best_rr < 1.5:
                # Just a warning, not hard error
                pass
    
    # 4. ID format check
    trade_id = data.get("id", "")
    if trade_id:
        parts = trade_id.split("_")
        if len(parts) < 4:
            errors.append(f"ID format should be: YYYY-MM-DD_SESSION_PAIR_SETUP_NUM")
        else:
            # Check date format
            try:
                datetime.strptime(parts[0], "%Y-%m-%d")
            except ValueError:
                errors.append(f"ID date portion '{parts[0]}' is not YYYY-MM-DD format")
    
    # 5. Displacement required for OB_FVG_retrace
    setup_type = data.get("setup", {}).get("setup_type", "")
    displacement = data.get("setup", {}).get("confirmation", {}).get("displacement")
    if "OB_FVG" in setup_type and displacement is False:
        errors.append("OB_FVG setups require displacement=true")
    
    # 6. Entry in discount for longs (warning only)
    discount_premium = data.get("pd_arrays", {}).get("discount_premium", {})
    bias = data.get("setup", {}).get("bias")
    entry_in_discount = discount_premium.get("entry_in_discount")
    
    if bias == "long" and entry_in_discount is False:
        errors.append("Warning: Long entry not in discount zone")
    elif bias == "short" and entry_in_discount is True:
        errors.append("Warning: Short entry in discount (should be premium)")
    
    # 7. Reasoning fields shouldn't be empty
    reasoning = data.get("reasoning", {})
    for field in ["why_here", "why_now", "what_invalidates"]:
        value = reasoning.get(field, "")
        if not value or len(value) < 10:
            errors.append(f"reasoning.{field} is empty or too short")
    
    return errors


def validate_all(verbose: bool = True) -> tuple[int, int, int]:
    """
    Validate all setup files in training directory.
    Returns (valid_count, error_count, skipped_count)
    """
    schema = load_schema()
    
    valid = 0
    errors = 0
    skipped = 0
    
    # Find all JSON files
    json_files = list(TRAINING_DIR.rglob("*.json"))
    
    if not json_files:
        print(f"No JSON files found in {TRAINING_DIR}")
        return 0, 0, 0
    
    print(f"\nValidating {len(json_files)} files...\n")
    
    for filepath in sorted(json_files):
        # Skip .gitkeep and other non-setup files
        if filepath.name.startswith("."):
            continue
        
        is_valid, errs = validate_file(filepath, schema, verbose=False)
        
        rel_path = filepath.relative_to(PROJECT_ROOT)
        
        if is_valid and not errs:
            if verbose:
                print(f"✅ {rel_path}")
            valid += 1
        elif is_valid:
            # Skipped (template)
            skipped += 1
        else:
            print(f"❌ {rel_path}")
            for err in errs:
                print(f"   └─ {err}")
            errors += 1
    
    return valid, errors, skipped


def print_summary(valid: int, errors: int, skipped: int):
    """Print validation summary"""
    print(f"\n{'─' * 40}")
    print(f"Valid:   {valid}")
    print(f"Errors:  {errors}")
    print(f"Skipped: {skipped}")
    print(f"{'─' * 40}")
    
    if errors == 0:
        print("✅ All setups valid!")
    else:
        print(f"❌ {errors} file(s) need attention")


def main():
    parser = argparse.ArgumentParser(description="Validate ICT trade setup JSON files")
    parser.add_argument("file", nargs="?", help="JSON file to validate")
    parser.add_argument("--all", action="store_true", help="Validate all files in data/training/")
    parser.add_argument("--quiet", "-q", action="store_true", help="Only show errors")
    parser.add_argument("--schema", action="store_true", help="Print schema path and exit")
    
    args = parser.parse_args()
    
    if args.schema:
        print(f"Schema: {SCHEMA_PATH}")
        print(f"Training dir: {TRAINING_DIR}")
        return
    
    if not HAS_JSONSCHEMA:
        print("\n⚠️  Install jsonschema for full validation: pip install jsonschema")
        print("   Running custom validations only...\n")
    
    if args.all:
        valid, errors, skipped = validate_all(verbose=not args.quiet)
        print_summary(valid, errors, skipped)
        sys.exit(1 if errors > 0 else 0)
    
    elif args.file:
        filepath = Path(args.file)
        schema = load_schema()
        
        is_valid, errors = validate_file(filepath, schema)
        
        if is_valid:
            print(f"✅ {filepath.name} is valid")
        else:
            print(f"❌ {filepath.name} has errors:")
            for err in errors:
                print(f"   └─ {err}")
            sys.exit(1)
    
    else:
        parser.print_help()
        print("\nExamples:")
        print("  python validate_setup.py data/training/positive/my_trade.json")
        print("  python validate_setup.py --all")


if __name__ == "__main__":
    main()
