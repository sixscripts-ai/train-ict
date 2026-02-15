"""
NewsSkill — Checks news calendar before trading.
Wraps: NewsFilter (ForexFactory integration)
"""

import time
from typing import Any, Dict
from datetime import datetime
from zoneinfo import ZoneInfo

from ict_agent.skills.base import Skill, SkillResult
from ict_agent.events.event_types import VexEvent, EventType

NY_TZ = ZoneInfo("America/New_York")


class NewsSkill(Skill):
    name = "news"
    description = "Check economic news calendar — gate trades around high-impact events"
    version = "1.0.0"

    def execute(self, context: Dict[str, Any]) -> SkillResult:
        """
        Check if it's safe to trade a symbol (no high-impact news).
        
        Context:
            symbol: str — pair to check
            news_filter: NewsFilter instance (optional, will create if missing)
            
        Returns:
            SkillResult with safety status and upcoming events.
        """
        start = time.time()
        err = self.validate_context(context, ["symbol"])
        if err:
            return SkillResult(success=False, error=err)

        symbol = context["symbol"]
        news_filter = context.get("news_filter")
        events = []

        try:
            # Create NewsFilter if not provided
            if news_filter is None:
                from ict_agent.engine.news_filter import NewsFilter
                news_filter = NewsFilter()

            # Update calendar if stale
            news_filter.update_calendar()

            # Check safety
            safe = news_filter.is_safe_to_trade(symbol)
            next_danger = news_filter.get_next_danger(symbol)

            danger_info = None
            if next_danger:
                danger_info = {
                    "title": next_danger.get("title", ""),
                    "currency": next_danger.get("currency", ""),
                    "impact": next_danger.get("impact", ""),
                    "time": str(next_danger.get("time", "")),
                    "minutes_away": next_danger.get("minutes_away", 0),
                }

            events.append(VexEvent(
                event_type=EventType.NEWS_CHECK,
                source="skill:news",
                data={
                    "symbol": symbol,
                    "safe_to_trade": safe,
                    "next_danger": danger_info,
                },
            ))

            return SkillResult(
                success=True,
                data={
                    "symbol": symbol,
                    "safe_to_trade": safe,
                    "next_danger": danger_info,
                    "calendar_size": len(news_filter.events) if hasattr(news_filter, "events") else 0,
                },
                events=events,
                execution_time_ms=(time.time() - start) * 1000,
            )

        except Exception as e:
            # If news check fails, default to SAFE (don't block trading on news API failure)
            return SkillResult(
                success=True,
                data={
                    "symbol": symbol,
                    "safe_to_trade": True,
                    "error": str(e),
                    "fallback": True,
                },
                execution_time_ms=(time.time() - start) * 1000,
            )
