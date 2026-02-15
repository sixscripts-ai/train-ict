"""
LongTermMemory — Persistent memory backed by JSON files.

Stores and retrieves:
  - Trade history with outcomes
  - Learned patterns (what works, what doesn't)
  - Golden rules from user teachings
  - Pair-specific notes and session preferences
  - Model performance stats

Integrates with existing data/learning/ and data/vex_memory/ directories.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

NY_TZ = ZoneInfo("America/New_York")


class LongTermMemory:
    """
    Persistent memory layer — reads/writes to data/ directory.
    
    File structure:
      data/learning/trade_lessons.json     — Post-trade lessons
      data/learning/pattern_stats.json     — Pattern win rates
      data/learning/confluence_stats.json  — Confluence effectiveness
      data/learning/insights.json          — Extracted insights
      data/learning/user_teachings.json    — Ashton's direct teachings
      data/learning/vex_memory.json        — Golden rules, pair/model notes
      data/learning/learned_concepts.json  — ICT concept mastery tracking
    """

    def __init__(self, data_dir: Optional[Path] = None):
        if data_dir is None:
            # Search common locations
            candidates = [
                Path.cwd() / "data" / "learning",
                Path(__file__).parent.parent.parent.parent / "data" / "learning",
                Path.home() / "Documents" / "train-ict" / "data" / "learning",
            ]
            for candidate in candidates:
                if candidate.exists():
                    data_dir = candidate
                    break
            if data_dir is None:
                data_dir = Path.cwd() / "data" / "learning"
                data_dir.mkdir(parents=True, exist_ok=True)

        self.data_dir = data_dir
        self.vex_memory_dir = data_dir.parent / "vex_memory"
        
        # Load all memory stores
        self._trade_lessons = self._load("trade_lessons.json", [])
        self._pattern_stats = self._load("pattern_stats.json", {})
        self._confluence_stats = self._load("confluence_stats.json", {})
        self._insights = self._load("insights.json", {})
        self._user_teachings = self._load("user_teachings.json", {})
        self._vex_memory = self._load("vex_memory.json", {})
        self._learned_concepts = self._load("learned_concepts.json", {})

    def _load(self, filename: str, default: Any) -> Any:
        """Load a JSON file, return default if missing or corrupt."""
        path = self.data_dir / filename
        if path.exists():
            try:
                with open(path) as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return default
        return default

    def _save(self, filename: str, data: Any) -> None:
        """Save data to a JSON file."""
        path = self.data_dir / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(data, f, indent=2, default=str)

    # ─── Trade Lessons ────────────────────────────────────────────────────

    def record_trade_lesson(
        self,
        symbol: str,
        model: str,
        direction: str,
        outcome: str,  # "win", "loss", "breakeven"
        pnl: float,
        lesson: str,
        setup_details: Optional[Dict] = None,
    ) -> None:
        """Record a lesson from a completed trade."""
        entry = {
            "timestamp": datetime.now(NY_TZ).isoformat(),
            "symbol": symbol,
            "model": model,
            "direction": direction,
            "outcome": outcome,
            "pnl": pnl,
            "lesson": lesson,
            "setup_details": setup_details or {},
        }
        self._trade_lessons.append(entry)
        self._save("trade_lessons.json", self._trade_lessons)

    def get_lessons_for_symbol(self, symbol: str, limit: int = 10) -> List[Dict]:
        """Get recent lessons for a specific symbol."""
        return [
            l for l in reversed(self._trade_lessons)
            if l.get("symbol") == symbol
        ][:limit]

    def get_lessons_for_model(self, model: str, limit: int = 10) -> List[Dict]:
        """Get recent lessons for a specific model."""
        return [
            l for l in reversed(self._trade_lessons)
            if l.get("model") == model
        ][:limit]

    # ─── Pattern Stats ────────────────────────────────────────────────────

    def update_pattern_stats(self, pattern: str, won: bool, pnl: float) -> None:
        """Update win/loss stats for a pattern."""
        if pattern not in self._pattern_stats:
            self._pattern_stats[pattern] = {
                "wins": 0, "losses": 0, "total_pnl": 0.0,
                "avg_win": 0.0, "avg_loss": 0.0,
            }
        stats = self._pattern_stats[pattern]
        if won:
            stats["wins"] += 1
            n = stats["wins"]
            stats["avg_win"] = stats["avg_win"] * (n - 1) / n + pnl / n
        else:
            stats["losses"] += 1
            n = stats["losses"]
            stats["avg_loss"] = stats["avg_loss"] * (n - 1) / n + pnl / n
        stats["total_pnl"] += pnl
        self._save("pattern_stats.json", self._pattern_stats)

    def get_pattern_win_rate(self, pattern: str) -> Optional[float]:
        """Get win rate for a specific pattern."""
        stats = self._pattern_stats.get(pattern)
        if stats:
            total = stats["wins"] + stats["losses"]
            return stats["wins"] / total if total > 0 else None
        return None

    # ─── Golden Rules ─────────────────────────────────────────────────────

    @property
    def golden_rules(self) -> List[Dict]:
        """Get Ashton's golden rules."""
        return self._vex_memory.get("golden_rules", [])

    def get_pair_memory(self, symbol: str) -> Dict:
        """Get pair-specific memory (best sessions, notes, warnings)."""
        return self._vex_memory.get("pair_specific", {}).get(symbol, {})

    def get_model_memory(self, model: str) -> Dict:
        """Get model-specific memory (notes, key confluences)."""
        return self._vex_memory.get("model_specific", {}).get(model, {})

    # ─── Insights ─────────────────────────────────────────────────────────

    def record_insight(self, category: str, insight: str, evidence: Optional[str] = None) -> None:
        """Record an extracted insight."""
        if category not in self._insights:
            self._insights[category] = []
        self._insights[category].append({
            "insight": insight,
            "evidence": evidence,
            "timestamp": datetime.now(NY_TZ).isoformat(),
        })
        self._save("insights.json", self._insights)

    def get_insights(self, category: Optional[str] = None) -> Dict:
        """Get insights, optionally filtered by category."""
        if category:
            return {category: self._insights.get(category, [])}
        return self._insights

    # ─── User Teachings ───────────────────────────────────────────────────

    @property
    def teachings(self) -> Dict:
        """Get all user teachings."""
        return self._user_teachings

    # ─── Comprehensive Recall ─────────────────────────────────────────────

    def recall_for_setup(self, symbol: str, model: str, session: str) -> Dict[str, Any]:
        """
        Comprehensive memory recall for a trading setup.
        Returns everything relevant to help decide on this trade.
        """
        pair_mem = self.get_pair_memory(symbol)
        model_mem = self.get_model_memory(model)
        lessons = self.get_lessons_for_symbol(symbol, limit=5)
        model_lessons = self.get_lessons_for_model(model, limit=5)
        pattern_wr = self.get_pattern_win_rate(f"{symbol}_{model}")
        
        # Check if this session is a preferred session for this pair
        best_sessions = pair_mem.get("best_sessions", [])
        session_match = session.lower() in [s.lower() for s in best_sessions]
        
        # Check for warnings
        warnings = pair_mem.get("warnings", [])
        
        # Get relevant golden rules
        relevant_rules = []
        for rule in self.golden_rules:
            key = rule.get("key", "")
            value = rule.get("value", "")
            # Include rules relevant to the symbol or model
            if (symbol.lower().replace("_", "") in value.lower() or
                model.lower() in key.lower() or
                "quality" in key.lower() or
                "first_loss" in key.lower()):
                relevant_rules.append(value)

        return {
            "pair_notes": pair_mem.get("notes", ""),
            "pair_win_rate": pair_mem.get("win_rate"),
            "pair_warnings": warnings,
            "session_match": session_match,
            "best_sessions": best_sessions,
            "model_notes": model_mem.get("notes", ""),
            "model_confluences": model_mem.get("key_confluences", []),
            "pattern_win_rate": pattern_wr,
            "recent_lessons": lessons,
            "model_lessons": model_lessons,
            "relevant_rules": relevant_rules,
            "teaching_count": sum(len(v) if isinstance(v, list) else 1 for v in self._user_teachings.values()),
        }

    def summary(self) -> Dict[str, Any]:
        """Memory system summary."""
        return {
            "trade_lessons": len(self._trade_lessons),
            "patterns_tracked": len(self._pattern_stats),
            "insight_categories": len(self._insights),
            "golden_rules": len(self.golden_rules),
            "pairs_with_memory": list(self._vex_memory.get("pair_specific", {}).keys()),
            "models_with_memory": list(self._vex_memory.get("model_specific", {}).keys()),
            "concepts_learned": len(self._learned_concepts),
        }

    def __repr__(self) -> str:
        s = self.summary()
        return (
            f"LongTermMemory(lessons={s['trade_lessons']}, "
            f"patterns={s['patterns_tracked']}, "
            f"rules={s['golden_rules']}, "
            f"pairs={s['pairs_with_memory']})"
        )
