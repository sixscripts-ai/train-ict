"""
VEX Event Stream
================
Pub/sub event bus connecting all agent components.
Every component publishes events → stream records and dispatches to subscribers.

Inspired by OpenHands EventStream but specialized for trading.
"""

import json
import threading
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
from zoneinfo import ZoneInfo

from ict_agent.events.event_types import VexEvent, EventType, SystemEvent

NY_TZ = ZoneInfo("America/New_York")


class EventStream:
    """
    Central event bus for the VEX agent.
    
    Components publish events → EventStream dispatches to subscribers.
    All events are logged to disk for replay and learning.
    
    Usage:
        stream = EventStream()
        stream.subscribe(EventType.SIGNAL_GENERATED, my_handler)
        stream.publish(SignalEvent(symbol="EUR_USD", ...))
    """

    def __init__(self, log_dir: Optional[Path] = None):
        self._subscribers: Dict[EventType, List[Callable]] = defaultdict(list)
        self._global_subscribers: List[Callable] = []
        self._events: List[VexEvent] = []
        self._event_counter: int = 0
        self._lock = threading.Lock()
        
        # Event log for persistence
        self._log_dir = log_dir or Path(__file__).parent.parent.parent.parent / "data" / "events"
        self._log_dir.mkdir(parents=True, exist_ok=True)
        self._log_file: Optional[Path] = None
        self._init_log_file()

    def _init_log_file(self) -> None:
        """Create a new log file for this session."""
        date_str = datetime.now(NY_TZ).strftime("%Y-%m-%d_%H%M%S")
        self._log_file = self._log_dir / f"events_{date_str}.jsonl"

    # ═══════════════════════════════════════════════════════════════════════════
    # PUB/SUB
    # ═══════════════════════════════════════════════════════════════════════════

    def subscribe(
        self,
        event_type: EventType,
        handler: Callable[[VexEvent], None],
    ) -> None:
        """Subscribe to a specific event type."""
        with self._lock:
            self._subscribers[event_type].append(handler)

    def subscribe_all(self, handler: Callable[[VexEvent], None]) -> None:
        """Subscribe to ALL events (useful for logging, dashboard)."""
        with self._lock:
            self._global_subscribers.append(handler)

    def unsubscribe(
        self,
        event_type: EventType,
        handler: Callable[[VexEvent], None],
    ) -> None:
        """Remove a subscriber."""
        with self._lock:
            if handler in self._subscribers[event_type]:
                self._subscribers[event_type].remove(handler)

    def publish(self, event: VexEvent) -> None:
        """
        Publish an event to the stream.
        
        1. Assigns event ID
        2. Stores in memory
        3. Persists to disk
        4. Dispatches to subscribers
        """
        with self._lock:
            self._event_counter += 1
            event.event_id = self._event_counter
            self._events.append(event)

        # Persist to disk (append JSONL)
        self._persist_event(event)

        # Dispatch to type-specific subscribers
        for handler in self._subscribers.get(event.event_type, []):
            try:
                handler(event)
            except Exception as e:
                self._publish_error(f"Handler error for {event.event_type}: {e}")

        # Dispatch to global subscribers
        for handler in self._global_subscribers:
            try:
                handler(event)
            except Exception as e:
                pass  # Don't recurse on error handlers

    def _publish_error(self, message: str) -> None:
        """Publish a system error event (without recursion)."""
        err = SystemEvent(
            event_type=EventType.SYSTEM_ERROR,
            message=message,
            level="error",
            component="event_stream",
        )
        err.event_id = self._event_counter + 1
        self._events.append(err)
        self._persist_event(err)

    # ═══════════════════════════════════════════════════════════════════════════
    # PERSISTENCE
    # ═══════════════════════════════════════════════════════════════════════════

    def _persist_event(self, event: VexEvent) -> None:
        """Append event to JSONL log file."""
        if self._log_file:
            try:
                with open(self._log_file, "a") as f:
                    f.write(json.dumps(event.to_dict(), default=str) + "\n")
            except Exception:
                pass  # Don't crash the agent on log failure

    # ═══════════════════════════════════════════════════════════════════════════
    # QUERIES
    # ═══════════════════════════════════════════════════════════════════════════

    def get_events(
        self,
        event_type: Optional[EventType] = None,
        source: Optional[str] = None,
        since: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[VexEvent]:
        """Query events from the stream."""
        events = self._events

        if event_type:
            events = [e for e in events if e.event_type == event_type]
        if source:
            events = [e for e in events if e.source == source]
        if since:
            events = [e for e in events if e.timestamp >= since]

        return events[-limit:]

    def get_last_event(self, event_type: EventType) -> Optional[VexEvent]:
        """Get the most recent event of a given type."""
        for event in reversed(self._events):
            if event.event_type == event_type:
                return event
        return None

    @property
    def event_count(self) -> int:
        return len(self._events)

    def get_summary(self) -> Dict[str, int]:
        """Get count of events by type."""
        summary: Dict[str, int] = {}
        for event in self._events:
            key = event.event_type.value
            summary[key] = summary.get(key, 0) + 1
        return summary

    def clear(self) -> None:
        """Clear in-memory events (log file is preserved)."""
        with self._lock:
            self._events.clear()
            self._event_counter = 0
