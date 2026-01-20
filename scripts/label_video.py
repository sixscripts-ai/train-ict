#!/usr/bin/env python3
"""
ICT Video Labeling Tool

Converts video transcript + timestamps into structured training data.
Outputs JSON suitable for ML model training.

Usage:
    python label_video.py --video <video_path> --transcript <transcript_path> --output <output_path>
    python label_video.py --interactive  # Manual frame-by-frame labeling
"""

import json
import argparse
import re
from pathlib import Path
from datetime import datetime
from typing import Optional


# ICT Concept Labels (from ontology)
ICT_CONCEPTS = [
    # Structures
    "swing_high", "swing_low", "bos", "choch", "range_high", "range_low",
    "terminus", "prior_distribution", "origination_displacement",
    # Liquidity
    "bsl", "ssl", "equal_highs", "equal_lows", "sweep", "irl", "erl",
    # PD Arrays
    "fvg", "order_block", "imbalance", "premium", "discount", "mitigation_block",
    # Timing
    "cbdr", "asia_range", "killzone", "judas_swing", "session_open",
    # Model stages
    "accumulation", "manipulation", "distribution",
    # Entry models
    "ob_fvg_retrace", "judas_into_ob", "ltf_refinement", "cbdr_asia_sd"
]

PAIRS = ["EURUSD", "GBPUSD", "USDJPY", "GBPJPY", "XAUUSD", "US30", "NAS100"]
TIMEFRAMES = ["1M", "5M", "15M", "1H", "4H", "D", "W"]


def create_empty_frame() -> dict:
    """Create empty frame template"""
    return {
        "frame_id": None,
        "timestamp": None,
        "video_time": None,
        "pair": None,
        "timeframe": None,
        "transcript": "",
        "annotations": [],
        "labels": [],
        "price_levels": {},
        "model_stage": None,
        "action": None,
        "confidence": None
    }


def parse_transcript_file(filepath: Path) -> list[dict]:
    """
    Parse a transcript file with timestamps.
    
    Expected format:
    [00:00:15] This is what I'm saying about the chart...
    [00:00:30] Now looking at the order block here...
    """
    frames = []
    
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Match [MM:SS] or [HH:MM:SS] followed by text
    pattern = r'\[(\d{1,2}:\d{2}(?::\d{2})?)\]\s*(.+?)(?=\[|\Z)'
    matches = re.findall(pattern, content, re.DOTALL)
    
    for i, (timestamp, text) in enumerate(matches):
        frame = create_empty_frame()
        frame["frame_id"] = i + 1
        frame["video_time"] = timestamp
        frame["transcript"] = text.strip()
        frames.append(frame)
    
    return frames


def auto_detect_concepts(text: str) -> list[str]:
    """
    Auto-detect ICT concepts mentioned in transcript text.
    """
    detected = []
    text_lower = text.lower()
    
    # Pattern matching for common ICT terms
    patterns = {
        "fvg": r"\b(fvg|fair value gap|gap|imbalance)\b",
        "order_block": r"\b(ob|order block|orderblock|last down candle|last up candle)\b",
        "bos": r"\b(bos|break of structure|structure break)\b",
        "choch": r"\b(choch|change of character)\b",
        "bsl": r"\b(bsl|buy side|buyside|equal highs)\b",
        "ssl": r"\b(ssl|sell side|sellside|equal lows)\b",
        "sweep": r"\b(sweep|swept|taken out|grabbed|raided)\b",
        "judas_swing": r"\b(judas|false move|fake out)\b",
        "premium": r"\b(premium|above equilibrium)\b",
        "discount": r"\b(discount|below equilibrium)\b",
        "cbdr": r"\b(cbdr|central bank|dealer range)\b",
        "asia_range": r"\b(asia|asian session|asian range)\b",
        "terminus": r"\b(terminus|objective|target zone)\b",
        "accumulation": r"\b(accumulation|consolidat|range)\b",
        "manipulation": r"\b(manipulation|trap|fake)\b",
        "distribution": r"\b(distribution|real move|expansion)\b"
    }
    
    for concept, pattern in patterns.items():
        if re.search(pattern, text_lower):
            detected.append(concept)
    
    return detected


def auto_detect_pair(text: str) -> Optional[str]:
    """Auto-detect trading pair from text"""
    text_upper = text.upper()
    for pair in PAIRS:
        if pair in text_upper or pair.replace("USD", " USD") in text_upper:
            return pair
    return None


def auto_detect_timeframe(text: str) -> Optional[str]:
    """Auto-detect timeframe from text"""
    patterns = {
        "1M": r"\b(1[- ]?min|1m|one minute)\b",
        "5M": r"\b(5[- ]?min|5m|five minute)\b",
        "15M": r"\b(15[- ]?min|15m|fifteen minute)\b",
        "1H": r"\b(1[- ]?hour|1h|hourly|one hour)\b",
        "4H": r"\b(4[- ]?hour|4h|four hour)\b",
        "D": r"\b(daily|day|1d)\b",
        "W": r"\b(weekly|week|1w)\b"
    }
    
    text_lower = text.lower()
    for tf, pattern in patterns.items():
        if re.search(pattern, text_lower):
            return tf
    return None


def enrich_frames(frames: list[dict]) -> list[dict]:
    """
    Auto-enrich frames with detected concepts, pairs, timeframes.
    """
    for frame in frames:
        text = frame["transcript"]
        
        # Auto-detect
        frame["labels"] = auto_detect_concepts(text)
        
        detected_pair = auto_detect_pair(text)
        if detected_pair and not frame["pair"]:
            frame["pair"] = detected_pair
        
        detected_tf = auto_detect_timeframe(text)
        if detected_tf and not frame["timeframe"]:
            frame["timeframe"] = detected_tf
    
    return frames


def interactive_labeling(frames: list[dict]) -> list[dict]:
    """
    Interactive CLI for manual labeling of frames.
    """
    print("\n" + "="*60)
    print("ICT Video Frame Labeler - Interactive Mode")
    print("="*60)
    print(f"\nLabeling {len(frames)} frames...")
    print("Commands: [s]kip, [q]uit, [a]dd label, [p]air, [t]imeframe")
    print("-"*60)
    
    for i, frame in enumerate(frames):
        print(f"\n--- Frame {i+1}/{len(frames)} [{frame['video_time']}] ---")
        print(f"Transcript: {frame['transcript'][:200]}...")
        
        if frame['labels']:
            print(f"Auto-detected: {', '.join(frame['labels'])}")
        
        while True:
            cmd = input("\nAction [s/q/a/p/t]: ").strip().lower()
            
            if cmd == 's':
                break
            elif cmd == 'q':
                return frames
            elif cmd == 'a':
                print(f"Available labels: {', '.join(ICT_CONCEPTS)}")
                label = input("Add label: ").strip()
                if label in ICT_CONCEPTS and label not in frame['labels']:
                    frame['labels'].append(label)
                    print(f"Added: {label}")
            elif cmd == 'p':
                print(f"Pairs: {', '.join(PAIRS)}")
                pair = input("Set pair: ").strip().upper()
                if pair in PAIRS:
                    frame['pair'] = pair
                    print(f"Set pair: {pair}")
            elif cmd == 't':
                print(f"Timeframes: {', '.join(TIMEFRAMES)}")
                tf = input("Set timeframe: ").strip().upper()
                if tf in TIMEFRAMES:
                    frame['timeframe'] = tf
                    print(f"Set TF: {tf}")
    
    return frames


def generate_training_data(frames: list[dict], metadata: dict) -> dict:
    """
    Generate final training data structure.
    """
    return {
        "version": "1.0",
        "generated": datetime.now().isoformat(),
        "metadata": metadata,
        "frames": frames,
        "statistics": {
            "total_frames": len(frames),
            "labeled_frames": sum(1 for f in frames if f['labels']),
            "concept_counts": count_concepts(frames)
        }
    }


def count_concepts(frames: list[dict]) -> dict:
    """Count occurrences of each concept"""
    counts = {}
    for frame in frames:
        for label in frame['labels']:
            counts[label] = counts.get(label, 0) + 1
    return dict(sorted(counts.items(), key=lambda x: -x[1]))


def main():
    parser = argparse.ArgumentParser(description="ICT Video Labeling Tool")
    parser.add_argument("--transcript", "-t", type=Path, help="Path to transcript file")
    parser.add_argument("--output", "-o", type=Path, help="Output JSON path")
    parser.add_argument("--video", "-v", type=Path, help="Video file path (for metadata)")
    parser.add_argument("--interactive", "-i", action="store_true", help="Interactive labeling mode")
    parser.add_argument("--pair", "-p", type=str, help="Trading pair (e.g., EURUSD)")
    parser.add_argument("--date", "-d", type=str, help="Trade date (YYYY-MM-DD)")
    
    args = parser.parse_args()
    
    # Initialize frames
    frames = []
    
    if args.transcript and args.transcript.exists():
        print(f"Loading transcript: {args.transcript}")
        frames = parse_transcript_file(args.transcript)
        print(f"Parsed {len(frames)} frames")
    else:
        # Demo mode with sample frame
        print("No transcript provided. Creating sample frame...")
        frames = [create_empty_frame()]
        frames[0]["frame_id"] = 1
        frames[0]["transcript"] = "Sample transcript - run with --transcript to parse real data"
    
    # Auto-enrich
    frames = enrich_frames(frames)
    
    # Override pair if specified
    if args.pair:
        for frame in frames:
            frame["pair"] = args.pair.upper()
    
    # Interactive mode
    if args.interactive:
        frames = interactive_labeling(frames)
    
    # Build metadata
    metadata = {
        "source_video": str(args.video) if args.video else None,
        "source_transcript": str(args.transcript) if args.transcript else None,
        "trade_date": args.date,
        "pair": args.pair
    }
    
    # Generate output
    training_data = generate_training_data(frames, metadata)
    
    # Output
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(training_data, f, indent=2)
        print(f"\nSaved training data to: {args.output}")
    else:
        print("\n" + json.dumps(training_data, indent=2))
    
    # Print stats
    print(f"\n--- Statistics ---")
    print(f"Total frames: {training_data['statistics']['total_frames']}")
    print(f"Labeled frames: {training_data['statistics']['labeled_frames']}")
    if training_data['statistics']['concept_counts']:
        print("Top concepts:")
        for concept, count in list(training_data['statistics']['concept_counts'].items())[:5]:
            print(f"  {concept}: {count}")


if __name__ == "__main__":
    main()
