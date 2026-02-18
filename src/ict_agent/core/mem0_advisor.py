"""
VEX Mem0 Advisor
================
Bridges the Mem0 persistent-memory API into VEX's analysis pipeline.

Queries VEX's stored ICT knowledge (ingested via scripts/ingest_mem0.py)
for contextual insights that enrich the trade setup with ICT theory,
historical rules, and model-specific guidance.

Design philosophy:
  - Lazy-loaded: the Mem0 client is only initialised on first use.
  - Graceful fallback: if the API key is missing or the service is
    unreachable, analysis continues unimpeded (passthrough).
  - Deterministic: results are based entirely on stored knowledge
    (no LLM generation at query time — Mem0 search only).

Usage inside VexCoreEngine:
    from ict_agent.core.mem0_advisor import Mem0Advisor

    advisor = Mem0Advisor()            # lazy — nothing happens yet
    result  = advisor.consult(
        model="model_11",
        bias="bullish",
        session="ny_am",
        killzone="ny_am",
        patterns=["fvg", "displacement", "liquidity_sweep"],
        trade_type="irl_to_erl",
    )
    # result.insights      -> list[str]   (contextual ICT knowledge)
    # result.warnings      -> list[str]   (ICT rules that may conflict)
    # result.available      -> bool
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

USER_ID = "six-scripts"

# Maximum number of Mem0 search queries per consult() call.
# Keeps API usage predictable and latency bounded.
_MAX_QUERIES = 3


# ── Result dataclass ─────────────────────────────────────────────────────────


@dataclass
class Mem0Insight:
    """Result from a Mem0 knowledge consultation, ready for VEX consumption."""

    # Drop-in data for VEX confluences / display
    insights: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    # Metadata
    available: bool = True
    query_count: int = 0
    memory_hits: int = 0


# ── Advisor class ────────────────────────────────────────────────────────────


class Mem0Advisor:
    """Queries VEX's Mem0 knowledge store for contextual ICT insights.

    Initialisation is intentionally lazy — the MemoryClient is only
    created the first time ``consult()`` is called.  This keeps VEX's
    boot time unaffected if the API key is absent or Mem0 is down.
    """

    def __init__(self):
        self._client = None
        self._loaded = False
        self._available = False

    # ── Lazy loading ─────────────────────────────────────────────────────

    def _ensure_loaded(self) -> bool:
        """Lazy-load the Mem0 client on first use."""
        if self._loaded:
            return self._available

        try:
            # Try loading .env if not already in environment
            api_key = os.environ.get("MEM0_API_KEY")
            if not api_key:
                env_path = Path(__file__).resolve().parent.parent.parent.parent / ".env"
                if env_path.exists():
                    for line in env_path.read_text().splitlines():
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            key, _, val = line.partition("=")
                            os.environ.setdefault(key.strip(), val.strip())
                api_key = os.environ.get("MEM0_API_KEY")

            if not api_key:
                logger.warning("Mem0Advisor: MEM0_API_KEY not found — disabled")
                self._loaded = True
                self._available = False
                return False

            from mem0 import MemoryClient

            self._client = MemoryClient(api_key=api_key)

            # Quick connectivity check — fetch a single memory
            test = self._client.get_all(
                version="v2",
                filters={"OR": [{"user_id": USER_ID}]},
                page=1,
                page_size=1,
            )
            count = len(test.get("results", []))
            self._loaded = True
            self._available = True
            logger.info("Mem0Advisor loaded — connected (%d+ memories)", count)

        except Exception as exc:
            logger.warning("Mem0Advisor unavailable: %s", exc)
            self._loaded = True
            self._available = False

        return self._available

    # ── Public API ───────────────────────────────────────────────────────

    def consult(
        self,
        *,
        model: str = "",
        bias: str = "",
        session: str = "",
        killzone: str = "",
        patterns: Optional[List[str]] = None,
        trade_type: str = "",
        displacement: bool = False,
        sweep_occurred: bool = False,
    ) -> Mem0Insight:
        """Query Mem0 for ICT knowledge relevant to the current analysis.

        Constructs up to ``_MAX_QUERIES`` targeted search queries from the
        analysis context, deduplicates results, and returns structured
        insights that VEX can merge into the trade setup confluences.

        If Mem0 is unavailable, returns an empty ``Mem0Insight`` with
        ``available=False`` so the engine continues unimpeded.
        """
        if not self._ensure_loaded():
            return Mem0Insight(available=False)

        patterns = patterns or []
        queries = self._build_queries(
            model=model,
            bias=bias,
            session=session,
            killzone=killzone,
            patterns=patterns,
            trade_type=trade_type,
            displacement=displacement,
            sweep_occurred=sweep_occurred,
        )

        all_memories: Dict[str, str] = {}  # id → memory text (dedup)
        query_count = 0

        for query in queries[:_MAX_QUERIES]:
            try:
                result = self._client.search(
                    query,
                    version="v2",
                    filters={"OR": [{"user_id": USER_ID}]},
                    limit=5,
                )
                for mem in result.get("results", []):
                    mid = mem.get("id", "")
                    text = mem.get("memory", "")
                    if mid and text and mid not in all_memories:
                        all_memories[mid] = text
                query_count += 1
            except Exception as exc:
                logger.debug("Mem0 search error for '%s': %s", query, exc)

        if not all_memories:
            return Mem0Insight(
                available=True,
                query_count=query_count,
                memory_hits=0,
            )

        # ── Classify memories into insights vs warnings ──────────────────
        insights: List[str] = []
        warnings: List[str] = []

        # Keywords that suggest caution / conditions
        caution_keywords = (
            "avoid",
            "don't",
            "do not",
            "never",
            "warning",
            "caution",
            "invalidat",
            "red flag",
            "no-go",
            "fails",
            "trap",
            "against",
            "counter",
            "mistake",
            "wrong",
        )

        for text in all_memories.values():
            text_lower = text.lower()
            if any(kw in text_lower for kw in caution_keywords):
                warnings.append(text)
            else:
                insights.append(text)

        return Mem0Insight(
            insights=insights,
            warnings=warnings,
            available=True,
            query_count=query_count,
            memory_hits=len(all_memories),
        )

    # ── Query construction ───────────────────────────────────────────────

    def _build_queries(
        self,
        *,
        model: str,
        bias: str,
        session: str,
        killzone: str,
        patterns: List[str],
        trade_type: str,
        displacement: bool,
        sweep_occurred: bool,
    ) -> List[str]:
        """Build targeted search queries from analysis context.

        Strategy:
          Q1 — Model + trade-type specific query (most targeted)
          Q2 — Session / killzone rules
          Q3 — Pattern confluence rules (FVG, OB, sweep, etc.)
        """
        queries: List[str] = []

        # ── Q1: Model + trade type ───────────────────────────────────────
        model_names = {
            "model_11": "Model 11 Silver Bullet",
            "model_12": "Model 12 Unicorn",
            "turtle_soup": "Turtle Soup liquidity sweep fade",
            "standard": "ICT standard IRL to ERL",
        }
        model_label = model_names.get(model, model)

        if model and trade_type:
            trade_label = (
                "IRL to ERL Type A"
                if "irl_to_erl" in trade_type
                else "ERL to IRL Type B Turtle Soup"
            )
            queries.append(f"ICT {model_label} entry rules for {trade_label} trade")
        elif model:
            queries.append(f"ICT {model_label} entry rules and conditions")

        # ── Q2: Session / killzone ───────────────────────────────────────
        session_label = session or killzone
        if session_label:
            session_names = {
                "ny_am": "New York AM session",
                "ny_pm": "New York PM session",
                "london": "London session",
                "asia": "Asian session",
            }
            friendly = session_names.get(session_label, session_label)
            queries.append(
                f"ICT rules for trading during {friendly} killzone with {bias} bias"
            )

        # ── Q3: Pattern confluence ───────────────────────────────────────
        parts = []
        if "fvg" in patterns:
            parts.append("Fair Value Gap")
        if "order_block" in patterns or "ob" in patterns:
            parts.append("Order Block")
        if "displacement" in patterns or displacement:
            parts.append("displacement")
        if "liquidity_sweep" in patterns or sweep_occurred:
            parts.append("liquidity sweep")
        if "breaker_block" in patterns:
            parts.append("Breaker Block")

        if parts:
            combo = ", ".join(parts)
            queries.append(f"ICT confluence requirements when {combo} are present")

        # Fallback if nothing specific
        if not queries:
            queries.append("ICT entry rules and confluence requirements")

        return queries

    # ── Convenience ──────────────────────────────────────────────────────

    def summary(self, result: Mem0Insight) -> str:
        """Human-readable summary for VEX controller logs."""
        if not result.available:
            return "Mem0Advisor: unavailable — passthrough"
        if not result.insights and not result.warnings:
            return f"Mem0Advisor: {result.query_count} queries, 0 relevant hits"
        return (
            f"Mem0Advisor: {result.memory_hits} memories "
            f"({len(result.insights)} insights, {len(result.warnings)} warnings)"
        )
