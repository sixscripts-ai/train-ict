"""
News Event Filter Module

Filters trades around high-impact economic news events.
ICT Rule: No trading within 15 minutes before/after high-impact news.

Data Sources:
1. ForexFactory calendar (scraped)
2. Local cache (data/news_calendar.json)
3. Manual overrides

Usage:
    from ict_agent.engine.news_filter import NewsFilter
    
    nf = NewsFilter()
    
    # Check if it's safe to trade
    if nf.is_safe_to_trade("EUR_USD"):
        # proceed with trade
    
    # Get upcoming events
    events = nf.get_upcoming_events(hours=4)
    
    # Get events affecting a pair
    events = nf.get_events_for_pair("EUR_USD", hours=2)
"""

import json
import os
import re
import requests
from dataclasses import dataclass, asdict, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import List, Optional, Dict, Tuple
from zoneinfo import ZoneInfo

NY_TZ = ZoneInfo("America/New_York")
UTC_TZ = ZoneInfo("UTC")


class Impact(Enum):
    """News event impact level"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    HOLIDAY = "holiday"


# Currency → pairs it affects
CURRENCY_TO_PAIRS = {
    "USD": ["EUR_USD", "GBP_USD", "USD_JPY", "USD_CAD", "USD_CHF", "AUD_USD", "NZD_USD", "XAU_USD"],
    "EUR": ["EUR_USD", "EUR_GBP", "EUR_JPY", "EUR_CHF", "EUR_AUD"],
    "GBP": ["GBP_USD", "EUR_GBP", "GBP_JPY", "GBP_CHF", "GBP_AUD"],
    "JPY": ["USD_JPY", "EUR_JPY", "GBP_JPY", "AUD_JPY"],
    "CAD": ["USD_CAD", "CAD_JPY"],
    "CHF": ["USD_CHF", "EUR_CHF", "GBP_CHF"],
    "AUD": ["AUD_USD", "EUR_AUD", "GBP_AUD", "AUD_JPY"],
    "NZD": ["NZD_USD", "NZD_JPY"],
}

# Events that ALWAYS warrant avoidance (regardless of impact tag)
CRITICAL_EVENTS = {
    "Non-Farm Payrolls",
    "Non-Farm Employment Change",
    "NFP",
    "FOMC Statement",
    "FOMC Press Conference",
    "Federal Funds Rate",
    "Interest Rate Decision",
    "CPI",
    "Consumer Price Index",
    "Core CPI",
    "GDP",
    "Gross Domestic Product",
    "ECB Press Conference",
    "ECB Interest Rate",
    "BOE Interest Rate",
    "BOJ Interest Rate",
    "Unemployment Rate",
    "Retail Sales",
    "PMI",  # Manufacturing/Services PMI
    "ISM Manufacturing",
    "ISM Services",
    "PPI",
    "Core PCE",
    "PCE Price Index",
    "Jackson Hole",
}


@dataclass
class NewsEvent:
    """A single economic news event"""
    timestamp: datetime
    currency: str
    event_name: str
    impact: Impact
    forecast: str = ""
    previous: str = ""
    actual: str = ""
    
    @property
    def affects_pairs(self) -> List[str]:
        """Which currency pairs this event affects"""
        return CURRENCY_TO_PAIRS.get(self.currency, [])
    
    @property
    def is_critical(self) -> bool:
        """Is this a must-avoid event regardless of impact?"""
        name_upper = self.event_name.upper()
        return any(ce.upper() in name_upper for ce in CRITICAL_EVENTS)
    
    def minutes_until(self) -> float:
        """Minutes until this event (negative = already passed)"""
        now = datetime.now(NY_TZ)
        delta = self.timestamp - now
        return delta.total_seconds() / 60
    
    def __str__(self):
        mins = self.minutes_until()
        direction = "in" if mins > 0 else "ago"
        mins = abs(mins)
        if mins < 60:
            time_str = f"{mins:.0f}min {direction}"
        else:
            time_str = f"{mins/60:.1f}hr {direction}"
        
        return (
            f"[{self.impact.value.upper():6s}] {self.currency} "
            f"{self.event_name} @ {self.timestamp.strftime('%H:%M')} EST "
            f"({time_str})"
        )


class NewsFilter:
    """
    Filters trades around high-impact economic news events.
    
    ICT Rule: Avoid trading within the exclusion window around
    high-impact news (default: 15 min before, 15 min after).
    """
    
    def __init__(
        self,
        cache_dir: Path = None,
        exclusion_minutes_before: int = 15,
        exclusion_minutes_after: int = 15,
        critical_exclusion_minutes_before: int = 30,
        critical_exclusion_minutes_after: int = 30,
    ):
        self.cache_dir = cache_dir or Path(__file__).parent.parent.parent.parent / "data"
        self.cache_file = self.cache_dir / "news_calendar.json"
        
        self.exclusion_before = timedelta(minutes=exclusion_minutes_before)
        self.exclusion_after = timedelta(minutes=exclusion_minutes_after)
        self.critical_exclusion_before = timedelta(minutes=critical_exclusion_minutes_before)
        self.critical_exclusion_after = timedelta(minutes=critical_exclusion_minutes_after)
        
        # In-memory event cache
        self.events: List[NewsEvent] = []
        
        # Load cached events
        self._load_cache()
    
    # ═══════════════════════════════════════════════════════════════════
    # PUBLIC API
    # ═══════════════════════════════════════════════════════════════════
    
    def is_safe_to_trade(self, pair: str, at_time: datetime = None) -> Tuple[bool, Optional[NewsEvent]]:
        """
        Check if it's safe to trade a pair right now (or at a given time).
        
        Returns:
            (True, None) — safe to trade
            (False, event) — blocked by this event
        """
        now = at_time or datetime.now(NY_TZ)
        pair = pair.upper().replace("/", "_")
        
        for event in self.events:
            # Does this event affect our pair?
            if pair not in event.affects_pairs:
                continue
            
            # Only filter HIGH impact + critical events
            if event.impact not in (Impact.HIGH, Impact.HOLIDAY) and not event.is_critical:
                continue
            
            # Calculate exclusion window
            if event.is_critical:
                window_start = event.timestamp - self.critical_exclusion_before
                window_end = event.timestamp + self.critical_exclusion_after
            else:
                window_start = event.timestamp - self.exclusion_before
                window_end = event.timestamp + self.exclusion_after
            
            if window_start <= now <= window_end:
                return False, event
        
        return True, None
    
    def get_upcoming_events(
        self,
        hours: float = 4,
        impact_filter: Optional[Impact] = None,
    ) -> List[NewsEvent]:
        """Get all events in the next N hours"""
        now = datetime.now(NY_TZ)
        cutoff = now + timedelta(hours=hours)
        
        results = []
        for event in self.events:
            if now <= event.timestamp <= cutoff:
                if impact_filter and event.impact != impact_filter:
                    continue
                results.append(event)
        
        return sorted(results, key=lambda e: e.timestamp)
    
    def get_events_for_pair(
        self,
        pair: str,
        hours: float = 4,
    ) -> List[NewsEvent]:
        """Get upcoming events that affect a specific pair"""
        pair = pair.upper().replace("/", "_")
        events = self.get_upcoming_events(hours=hours)
        return [e for e in events if pair in e.affects_pairs]
    
    def get_next_danger(self, pair: str) -> Optional[NewsEvent]:
        """Get the next high-impact event for a pair"""
        events = self.get_events_for_pair(pair, hours=24)
        high = [e for e in events if e.impact == Impact.HIGH or e.is_critical]
        return high[0] if high else None
    
    def add_event(self, event: NewsEvent):
        """Manually add an event (for live updates or manual overrides)"""
        self.events.append(event)
        self.events.sort(key=lambda e: e.timestamp)
    
    def update_calendar(self) -> int:
        """
        Fetch latest calendar from ForexFactory.
        Returns number of events loaded.
        """
        events = self._fetch_forex_factory()
        if events:
            self.events = events
            self._save_cache()
            return len(events)
        return 0
    
    def print_daily_brief(self, pair: str = None):
        """Print today's news brief"""
        now = datetime.now(NY_TZ)
        today_events = [e for e in self.events if e.timestamp.date() == now.date()]
        
        if not today_events:
            print("📰 No economic events today")
            return
        
        print(f"📰 Economic Calendar — {now.strftime('%A, %B %d, %Y')}")
        print(f"   {len(today_events)} events today")
        print()
        
        for event in sorted(today_events, key=lambda e: e.timestamp):
            # Highlight if it affects our pair
            marker = ""
            if pair:
                pair_upper = pair.upper().replace("/", "_")
                if pair_upper in event.affects_pairs:
                    marker = " ⚠️  AFFECTS YOUR PAIR"
            
            icon = {"high": "🔴", "medium": "🟡", "low": "🟢", "holiday": "📅"}.get(
                event.impact.value, "⚪"
            )
            
            passed = " (PASSED)" if event.minutes_until() < 0 else ""
            print(f"  {icon} {event.timestamp.strftime('%H:%M')} {event.currency} — {event.event_name}{marker}{passed}")
    
    # ═══════════════════════════════════════════════════════════════════
    # DATA FETCHING
    # ═══════════════════════════════════════════════════════════════════
    
    def _fetch_forex_factory(self) -> List[NewsEvent]:
        """
        Fetch this week's calendar from ForexFactory.
        Uses their calendar page and parses the data.
        """
        try:
            # ForexFactory calendar URL for this week
            now = datetime.now(NY_TZ)
            url = f"https://nfs.faireconomy.media/ff_calendar_thisweek.json"
            
            resp = requests.get(url, timeout=10, headers={
                "User-Agent": "VEX-Trading-Agent/1.0"
            })
            
            if resp.status_code != 200:
                print(f"⚠️  ForexFactory returned {resp.status_code}")
                return []
            
            data = resp.json()
            events = []
            
            for item in data:
                try:
                    # Parse the date
                    date_str = item.get("date", "")
                    if not date_str:
                        continue
                    
                    # Parse timestamp
                    dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                    dt = dt.astimezone(NY_TZ)
                    
                    # Parse impact
                    impact_str = item.get("impact", "").lower()
                    if "high" in impact_str:
                        impact = Impact.HIGH
                    elif "medium" in impact_str:
                        impact = Impact.MEDIUM
                    elif "holiday" in impact_str:
                        impact = Impact.HOLIDAY
                    else:
                        impact = Impact.LOW
                    
                    event = NewsEvent(
                        timestamp=dt,
                        currency=item.get("country", "USD").upper(),
                        event_name=item.get("title", "Unknown Event"),
                        impact=impact,
                        forecast=str(item.get("forecast", "")),
                        previous=str(item.get("previous", "")),
                        actual=str(item.get("actual", "")),
                    )
                    events.append(event)
                    
                except (ValueError, KeyError) as e:
                    continue
            
            print(f"📡 Fetched {len(events)} events from ForexFactory")
            return events
            
        except requests.exceptions.RequestException as e:
            print(f"⚠️  Failed to fetch ForexFactory: {e}")
            return []
        except Exception as e:
            print(f"⚠️  Error parsing ForexFactory data: {e}")
            return []
    
    # ═══════════════════════════════════════════════════════════════════
    # CACHE
    # ═══════════════════════════════════════════════════════════════════
    
    def _load_cache(self):
        """Load cached calendar events"""
        if not self.cache_file.exists():
            return
        
        try:
            with open(self.cache_file) as f:
                data = json.load(f)
            
            self.events = []
            for item in data.get("events", []):
                self.events.append(NewsEvent(
                    timestamp=datetime.fromisoformat(item["timestamp"]),
                    currency=item["currency"],
                    event_name=item["event_name"],
                    impact=Impact(item["impact"]),
                    forecast=item.get("forecast", ""),
                    previous=item.get("previous", ""),
                    actual=item.get("actual", ""),
                ))
            
            cache_age = datetime.now(NY_TZ) - datetime.fromisoformat(data.get("fetched_at", "2000-01-01T00:00:00-05:00"))
            if cache_age > timedelta(hours=12):
                print(f"📰 Cache is {cache_age.total_seconds()/3600:.0f}h old — consider running update_calendar()")
                
        except (json.JSONDecodeError, KeyError) as e:
            print(f"⚠️  Failed to load news cache: {e}")
            self.events = []
    
    def _save_cache(self):
        """Save events to cache file"""
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        data = {
            "fetched_at": datetime.now(NY_TZ).isoformat(),
            "event_count": len(self.events),
            "events": [
                {
                    "timestamp": e.timestamp.isoformat(),
                    "currency": e.currency,
                    "event_name": e.event_name,
                    "impact": e.impact.value,
                    "forecast": e.forecast,
                    "previous": e.previous,
                    "actual": e.actual,
                }
                for e in self.events
            ]
        }
        
        with open(self.cache_file, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"💾 Cached {len(self.events)} events to {self.cache_file}")
