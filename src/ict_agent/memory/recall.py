"""
KnowledgeRecall — Contextual knowledge retrieval for trading decisions.

Inspired by OpenHands' microagent trigger system. Instead of keyword matching,
uses trading context (symbol, model, session, market conditions) to retrieve
relevant knowledge from:
  - VEX memory (golden rules, pair notes)
  - ICT patterns (buy/sell models, concepts)
  - Trade history (what worked before in similar conditions)
  - User teachings (Ashton's explicit instructions)

The recall system enriches analysis context before trade decisions.
"""

import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

NY_TZ = ZoneInfo("America/New_York")


class KnowledgeRecall:
    """
    Contextual knowledge retrieval — like OpenHands microagents but for trading.
    
    Triggered by analysis context, returns relevant knowledge to improve decisions.
    """

    def __init__(self, vex_memory_dir: Optional[Path] = None):
        if vex_memory_dir is None:
            candidates = [
                Path.cwd() / "data" / "vex_memory",
                Path(__file__).parent.parent.parent.parent / "data" / "vex_memory",
                Path.home() / "Documents" / "train-ict" / "data" / "vex_memory",
            ]
            for candidate in candidates:
                if candidate.exists():
                    vex_memory_dir = candidate
                    break

        self.vex_memory_dir = vex_memory_dir
        self._knowledge_cache: Dict[str, str] = {}
        self._load_knowledge_files()

    def _load_knowledge_files(self) -> None:
        """Load all markdown knowledge files from vex_memory."""
        if not self.vex_memory_dir or not self.vex_memory_dir.exists():
            return

        for f in self.vex_memory_dir.rglob("*.md"):
            try:
                self._knowledge_cache[f.stem] = f.read_text()
            except IOError:
                pass

        # Also load from ict_patterns subdirectory
        patterns_dir = self.vex_memory_dir / "ict_patterns"
        if patterns_dir.exists():
            for f in patterns_dir.rglob("*.md"):
                try:
                    self._knowledge_cache[f"pattern_{f.stem}"] = f.read_text()
                except IOError:
                    pass

    def recall(
        self,
        symbol: Optional[str] = None,
        model: Optional[str] = None,
        session: Optional[str] = None,
        bias: Optional[str] = None,
        trade_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Recall relevant knowledge for a trading context.
        
        Returns a structured dict with:
          - trading_rules: Applicable VEX trading rules
          - model_knowledge: ICT buy/sell model details
          - pair_philosophy: Ashton's notes on this pair
          - annotation_standards: How to grade setups
          - relevant_patterns: ICT pattern descriptions
          - warnings: Any cautions from memory
        """
        result: Dict[str, Any] = {
            "trading_rules": [],
            "model_knowledge": "",
            "pair_philosophy": "",
            "annotation_standards": "",
            "relevant_patterns": [],
            "warnings": [],
        }

        # 1. Trading rules (always relevant)
        rules_content = self._knowledge_cache.get("vex_trading_rules", "")
        if rules_content:
            result["trading_rules"] = self._extract_rules(rules_content)

        # 2. Model knowledge (buy/sell model details)
        models_content = self._knowledge_cache.get("ict_buy_sell_models", "")
        if models_content and model:
            result["model_knowledge"] = self._extract_model_section(models_content, model)

        # 3. Pair philosophy
        philosophy = self._knowledge_cache.get("ashton_trading_philosophy", "")
        if philosophy and symbol:
            pair_clean = symbol.replace("_", "/")
            result["pair_philosophy"] = self._extract_relevant_section(philosophy, pair_clean)

        # 4. Trading profile (risk management, psychology)
        profile = self._knowledge_cache.get("ashton_trading_profile", "")
        if profile:
            result["trader_profile"] = self._extract_relevant_section(
                profile, session or "general"
            )

        # 5. Annotation standards (setup grading)
        annotations = self._knowledge_cache.get("vex_annotation_standards", "")
        if annotations:
            result["annotation_standards"] = annotations[:500]  # First 500 chars as summary

        # 6. Pattern-specific knowledge
        if model:
            model_lower = model.lower()
            for key, content in self._knowledge_cache.items():
                if key.startswith("pattern_") and model_lower in content.lower():
                    result["relevant_patterns"].append({
                        "name": key.replace("pattern_", ""),
                        "excerpt": content[:300],
                    })

        # 7. Session-specific warnings
        if session:
            if "asian" in session.lower():
                result["warnings"].append("Asian session: Lower volatility, wider spreads. Be cautious with entries.")
            if "london" in session.lower() and symbol and "GBP" in symbol:
                result["warnings"].append("GBP in London: High volatility. Don't chase. Wait for proper displacement.")

        return result

    def _extract_rules(self, content: str) -> List[str]:
        """Extract individual rules from trading rules markdown."""
        rules = []
        for line in content.split("\n"):
            line = line.strip()
            if line.startswith("-") or line.startswith("*") or line.startswith("•"):
                rule = line.lstrip("-*• ").strip()
                if rule:
                    rules.append(rule)
        return rules

    def _extract_model_section(self, content: str, model: str) -> str:
        """Extract the section about a specific model from buy/sell models doc."""
        model_lower = model.lower()
        lines = content.split("\n")
        capturing = False
        captured = []

        for line in lines:
            if model_lower in line.lower() and ("#" in line or "**" in line):
                capturing = True
                captured.append(line)
                continue
            if capturing:
                if line.startswith("#") and model_lower not in line.lower():
                    break  # New section
                captured.append(line)

        return "\n".join(captured) if captured else ""

    def _extract_relevant_section(self, content: str, keyword: str) -> str:
        """Extract paragraphs containing a keyword."""
        paragraphs = content.split("\n\n")
        relevant = [p for p in paragraphs if keyword.lower() in p.lower()]
        return "\n\n".join(relevant[:3])  # Max 3 paragraphs

    @property
    def knowledge_files_loaded(self) -> int:
        return len(self._knowledge_cache)

    def list_knowledge(self) -> List[str]:
        """List all loaded knowledge file names."""
        return list(self._knowledge_cache.keys())

    def __repr__(self) -> str:
        return f"KnowledgeRecall(files={self.knowledge_files_loaded})"
