"""
ScanSkill — Scans all symbols for market data and killzone status.
Wraps: OANDAFetcher, KillzoneManager, AsianRangeCalculator
"""

import time
from typing import Any, Dict, List
from datetime import datetime
from zoneinfo import ZoneInfo

from ict_agent.skills.base import Skill, SkillResult
from ict_agent.events.event_types import MarketEvent, SystemEvent, EventType

NY_TZ = ZoneInfo("America/New_York")


class ScanSkill(Skill):
    name = "scan"
    description = "Scan symbols for market data, killzone status, and Asian range context"
    version = "1.0.0"

    def execute(self, context: Dict[str, Any]) -> SkillResult:
        """
        Scan all symbols.
        
        Context:
            symbols: List[str] — pairs to scan
            killzone_manager: KillzoneManager instance
            
        Returns:
            SkillResult with market data per symbol and killzone info.
        """
        start = time.time()
        err = self.validate_context(context, ["symbols"])
        if err:
            return SkillResult(success=False, error=err)

        symbols = context["symbols"]
        kz_mgr = context.get("killzone_manager")
        events = []
        scan_data = {}

        now = datetime.now(NY_TZ)
        current_killzone = None
        is_primary = False

        if kz_mgr:
            current_killzone = kz_mgr.get_current_killzone(now)
            is_primary = kz_mgr.is_primary_killzone(now)

        killzone_name = current_killzone.value if current_killzone else "none"

        # Import here to avoid circular imports at module level
        from ict_agent.data.oanda_fetcher import get_current_price

        for symbol in symbols:
            try:
                price = get_current_price(symbol)
                if price:
                    bid = price.get("bid", 0)
                    ask = price.get("ask", 0)
                    spread = round(ask - bid, 6)
                    tradeable = price.get("tradeable", True)

                    scan_data[symbol] = {
                        "bid": bid,
                        "ask": ask,
                        "mid": round((bid + ask) / 2, 6),
                        "spread": spread,
                        "tradeable": tradeable,
                    }

                    events.append(MarketEvent(
                        event_type=EventType.MARKET_SCAN,
                        source="skill:scan",
                        symbol=symbol,
                        bid=bid,
                        ask=ask,
                        spread=spread,
                        killzone=killzone_name,
                        tradeable=tradeable,
                    ))
            except Exception as e:
                events.append(SystemEvent(
                    event_type=EventType.SYSTEM_ERROR,
                    source="skill:scan",
                    message=f"Failed to scan {symbol}: {e}",
                    level="warning",
                    component="scan_skill",
                ))

        elapsed = (time.time() - start) * 1000

        return SkillResult(
            success=len(scan_data) > 0,
            data={
                "prices": scan_data,
                "killzone": killzone_name,
                "is_primary_killzone": is_primary,
                "symbols_scanned": len(scan_data),
                "timestamp": now.isoformat(),
            },
            events=events,
            execution_time_ms=elapsed,
        )
