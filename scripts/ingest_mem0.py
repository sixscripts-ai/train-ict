#!/usr/bin/env python3
"""
Mem0 Ingestion Script for VEX ICT Knowledge Base
=================================================
Softly ingests VEX's ICT knowledge files into Mem0 under user_id="six-scripts".

Files ingested:
  1. knowledge_base/ICT_MASTER_LIBRARY.md  (split by PART — 10 chunks)
  2. knowledge_base/ICT_KNOWLEDGE_SOURCES.md (1 chunk)
  3. .agent/workflows/* (9 files, 1 chunk each; mastery drill split into ~6 sub-chunks)

Usage:
    python scripts/ingest_mem0.py          # full run
    python scripts/ingest_mem0.py --dry-run  # preview chunks without sending
    python scripts/ingest_mem0.py --verify   # search existing memories
"""

import os
import re
import sys
import time
import argparse
from pathlib import Path
from typing import List, Tuple

# Load .env
env_path = Path(__file__).resolve().parent.parent / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, val = line.partition("=")
            os.environ.setdefault(key.strip(), val.strip())

from mem0 import MemoryClient

USER_ID = "six-scripts"
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DELAY_SECONDS = 3  # pause between API calls


# ---------------------------------------------------------------------------
# Chunking helpers
# ---------------------------------------------------------------------------


def chunk_by_heading(text: str, heading_pattern: str) -> List[Tuple[str, str]]:
    """Split markdown text by a regex heading pattern.
    Returns list of (heading, body) tuples."""
    parts = re.split(f"({heading_pattern})", text)
    chunks = []
    i = 0
    # Skip preamble before first heading (if any and non-trivial)
    if not re.match(heading_pattern, parts[0]):
        preamble = parts[0].strip()
        if len(preamble) > 100:
            chunks.append(("Preamble", preamble))
        i = 1
    while i < len(parts):
        heading = parts[i].strip() if i < len(parts) else ""
        body = parts[i + 1].strip() if i + 1 < len(parts) else ""
        if heading or body:
            chunks.append((heading, body))
        i += 2
    return chunks


def chunk_master_library(filepath: Path) -> List[Tuple[str, str]]:
    """Split ICT_MASTER_LIBRARY.md by '# PART N:' headings."""
    text = filepath.read_text()
    pattern = r"^# PART \d+:.*$"
    parts = re.split(f"({pattern})", text, flags=re.MULTILINE)

    chunks = []
    # parts[0] is the preamble (title + intro) — merge into first Part
    preamble = parts[0].strip()

    i = 1
    while i < len(parts):
        heading = parts[i].strip()
        body = parts[i + 1].strip() if i + 1 < len(parts) else ""
        label = f"ICT Master Library — {heading.lstrip('# ')}"
        content = f"{heading}\n\n{body}"
        # Merge preamble into first chunk
        if preamble and not chunks:
            content = f"{preamble}\n\n---\n\n{content}"
            preamble = ""
        chunks.append((label, content))
        i += 2

    return chunks


def chunk_mastery_drill(filepath: Path) -> List[Tuple[str, str]]:
    """Split the 1000-line mastery drill by rounds/sets."""
    text = filepath.read_text()
    # Split by "### User Input" or "### Planner Response" blocks won't work well.
    # Instead, split by the Round/Set markers.
    # Key markers: "Set 1:", "Set 2:", "Set 3:", "Round 1:", "Round 2:", etc.
    sections = []

    # Find natural break points: the "### **Set N:" and "### **Round N:" headers
    pattern = r"(### \*\*(?:Set \d+|Round \d+|Final Round|The Final Round)[^*]*\*\*)"
    splits = re.split(pattern, text, flags=re.IGNORECASE)

    # Preamble (intro + context before first Set)
    preamble = splits[0].strip()
    if len(preamble) > 200:
        sections.append(
            (
                "ICT Mastery Drill — Intro & Context",
                _clean_drill_text(preamble[:3000]),  # cap preamble
            )
        )

    current_label = ""
    current_body = ""
    i = 1
    while i < len(splits):
        header = splits[i].strip()
        body = splits[i + 1].strip() if i + 1 < len(splits) else ""
        # Extract label
        m = re.search(
            r"(Set \d+|Round \d+|Final Round|The Final Round)", header, re.IGNORECASE
        )
        label = m.group(1) if m else f"Section {i}"

        combined = f"{header}\n\n{body}"
        cleaned = _clean_drill_text(combined)

        # Group into reasonable sizes (aim for ~2000-5000 chars per chunk)
        if current_body and len(current_body) + len(cleaned) > 5000:
            sections.append((f"ICT Mastery Drill — {current_label}", current_body))
            current_label = label
            current_body = cleaned
        else:
            if not current_label:
                current_label = label
            else:
                current_label = f"{current_label} + {label}"
            current_body = f"{current_body}\n\n{cleaned}" if current_body else cleaned
        i += 2

    if current_body:
        sections.append((f"ICT Mastery Drill — {current_label}", current_body))

    # Post-process: split any chunk > 6000 chars into sub-chunks at paragraph breaks
    final = []
    for label, body in sections:
        if len(body) <= 6000:
            final.append((label, body))
        else:
            # Split at double-newline boundaries
            paragraphs = body.split("\n\n")
            sub_body = ""
            sub_idx = 1
            for para in paragraphs:
                if sub_body and len(sub_body) + len(para) > 5000:
                    final.append((f"{label} (part {sub_idx})", sub_body.strip()))
                    sub_idx += 1
                    sub_body = para
                else:
                    sub_body = f"{sub_body}\n\n{para}" if sub_body else para
            if sub_body.strip():
                if sub_idx > 1:
                    final.append((f"{label} (part {sub_idx})", sub_body.strip()))
                else:
                    final.append((label, sub_body.strip()))

    return final


def _clean_drill_text(text: str) -> str:
    """Remove noise from drill transcript (file views, ctrl chars, etc.)."""
    # Remove *Viewed [...]* lines
    text = re.sub(r"\*Viewed \[.*?\].*?\*", "", text)
    # Remove *Listed directory [...]* lines
    text = re.sub(r"\*Listed directory \[.*?\].*?\*", "", text)
    # Remove *Searched filesystem* etc.
    text = re.sub(
        r"\*(?:Searched filesystem|Grep searched codebase|Edited relevant file|Generated image|Checked command status|User accepted the command.*?)\*",
        "",
        text,
    )
    # Remove ctrl chars
    text = re.sub(r"<ctrl\d+>", "", text)
    # Remove "detachedthought" blocks (internal monologue) — everything from "detachedthought" to the next "### " heading
    text = re.sub(r"detachedthought.*?(?=###|\Z)", "", text, flags=re.DOTALL)
    # Collapse multiple blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def chunk_workflow_file(filepath: Path) -> List[Tuple[str, str]]:
    """Return a single chunk for a small workflow file."""
    text = filepath.read_text().strip()
    name = filepath.stem.replace("-", " ").replace("_", " ").title()
    return [(f"VEX Workflow — {name}", text)]


# ---------------------------------------------------------------------------
# Message formatting
# ---------------------------------------------------------------------------


def format_messages(label: str, content: str, source_file: str) -> List[dict]:
    """Format a chunk as a conversational message pair for Mem0."""
    return [
        {
            "role": "user",
            "content": (
                f"I'm teaching you about ICT trading methodology. "
                f"Here is the section '{label}' from {source_file}. "
                f"Learn and remember all the key concepts, rules, definitions, "
                f"and procedures described below.\n\n{content}"
            ),
        },
        {
            "role": "assistant",
            "content": (
                f"I've studied the '{label}' section from {source_file}. "
                f"I've memorized the key ICT concepts, trading rules, definitions, "
                f"and procedures it contains. I can recall this information when needed."
            ),
        },
    ]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def gather_all_chunks() -> List[Tuple[str, str, str]]:
    """Returns list of (label, content, source_file) tuples."""
    all_chunks: List[Tuple[str, str, str]] = []

    # 1. Master Library
    master = PROJECT_ROOT / "knowledge_base" / "ICT_MASTER_LIBRARY.md"
    if master.exists():
        for label, body in chunk_master_library(master):
            all_chunks.append((label, body, "ICT_MASTER_LIBRARY.md"))

    # 2. Knowledge Sources
    sources = PROJECT_ROOT / "knowledge_base" / "ICT_KNOWLEDGE_SOURCES.md"
    if sources.exists():
        text = sources.read_text().strip()
        all_chunks.append(
            ("ICT Knowledge Sources & Learning Path", text, "ICT_KNOWLEDGE_SOURCES.md")
        )

    # 3. Workflow files
    wf_dir = PROJECT_ROOT / ".agent" / "workflows"
    if wf_dir.exists():
        for wf_file in sorted(wf_dir.glob("*.md")):
            if wf_file.name == "ict-concept-mastery-drill.md":
                for label, body in chunk_mastery_drill(wf_file):
                    all_chunks.append((label, body, wf_file.name))
            else:
                for label, body in chunk_workflow_file(wf_file):
                    all_chunks.append((label, body, wf_file.name))

    return all_chunks


def run_ingest(dry_run: bool = False):
    chunks = gather_all_chunks()
    print(f"\n{'=' * 60}")
    print(f"  Mem0 Ingestion — {len(chunks)} chunks to ingest")
    print(f"  User ID: {USER_ID}")
    print(f"  Delay: {DELAY_SECONDS}s between calls")
    print(f"  Mode: {'DRY RUN' if dry_run else 'LIVE'}")
    print(f"{'=' * 60}\n")

    if not dry_run:
        api_key = os.environ.get("MEM0_API_KEY")
        if not api_key:
            print("ERROR: MEM0_API_KEY not found in environment or .env")
            sys.exit(1)
        client = MemoryClient(api_key=api_key)

    for i, (label, content, source) in enumerate(chunks, 1):
        char_count = len(content)
        print(f"[{i}/{len(chunks)}] {label}")
        print(f"         Source: {source} | {char_count:,} chars")

        if dry_run:
            # Show first 200 chars of content
            preview = content[:200].replace("\n", " ")
            print(f"         Preview: {preview}...")
            print()
            continue

        messages = format_messages(label, content, source)
        try:
            result = client.add(messages, user_id=USER_ID)
            status = result.get("status") if isinstance(result, dict) else str(result)
            print(f"         -> Status: {status}")
        except Exception as e:
            print(f"         -> ERROR: {e}")

        if i < len(chunks):
            print(f"         (waiting {DELAY_SECONDS}s...)")
            time.sleep(DELAY_SECONDS)
        print()

    print(f"{'=' * 60}")
    print(f"  Done! {len(chunks)} chunks {'previewed' if dry_run else 'sent'}.")
    print(f"{'=' * 60}")


def run_verify():
    api_key = os.environ.get("MEM0_API_KEY")
    if not api_key:
        print("ERROR: MEM0_API_KEY not found in environment or .env")
        sys.exit(1)

    client = MemoryClient(api_key=api_key)

    print(f"\n{'=' * 60}")
    print(f"  Verifying Mem0 memories for user: {USER_ID}")
    print(f"{'=' * 60}\n")

    # Get all memories
    try:
        raw = client.get_all(version="v2", filters={"OR": [{"user_id": USER_ID}]})
        # Handle both {'results': [...]} and bare list formats
        if isinstance(raw, dict) and "results" in raw:
            memories = raw["results"]
        elif isinstance(raw, list):
            memories = raw
        else:
            memories = []

        print(f"Total memories stored: {len(memories)}")

        if memories:
            print(f"\nShowing first 10 memories:\n")
            for j, mem in enumerate(memories[:10], 1):
                text = mem.get("memory", str(mem))[:120]
                print(f"  {j}. {text}...")
    except Exception as e:
        print(f"Error fetching memories: {e}")

    # Test search
    print(f"\n--- Search Tests ---\n")
    test_queries = [
        "What is a Fair Value Gap in ICT?",
        "Silver Bullet time window",
        "What are ICT Killzones?",
        "Market Maker Buy Model",
        "VEX chart markup workflow",
    ]
    for query in test_queries:
        try:
            raw = client.search(
                query, version="v2", filters={"OR": [{"user_id": USER_ID}]}
            )
            # Handle both {'results': [...]} and bare list formats
            if isinstance(raw, dict) and "results" in raw:
                results = raw["results"]
            elif isinstance(raw, list):
                results = raw
            else:
                results = []
            hit_count = len(results)
            top_hit = ""
            if hit_count > 0:
                top_hit = results[0].get("memory", "")[:80]
            print(f"  Q: '{query}'")
            print(f"     Hits: {hit_count} | Top: {top_hit}...")
            print()
        except Exception as e:
            print(f"  Q: '{query}' -> ERROR: {e}")
            print()
        time.sleep(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest VEX ICT knowledge into Mem0")
    parser.add_argument(
        "--dry-run", action="store_true", help="Preview chunks without sending"
    )
    parser.add_argument("--verify", action="store_true", help="Verify stored memories")
    args = parser.parse_args()

    if args.verify:
        run_verify()
    else:
        run_ingest(dry_run=args.dry_run)
