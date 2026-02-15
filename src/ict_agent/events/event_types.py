"""
VEX Event Types
===============
Every action in the agent produces a typed event.
Events are the single source of truth — auditable, replayable, learnable.

Inspired by OpenHands events/action + events/observation pattern.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from enum import Enum
from zoneinfo import ZoneInfo

NY_TZ = ZoneInfo("America/New_York")


class EventType(Enum):
    """All possible event types in the VEX system."""
    # System
    SYSTEM_START = "system_start"
    SYSTEM_STOP = "system_stop"
    SYSTEM_ERROR = "system_error"
    SYSTEM_HEARTBEAT = "system_heartbeat"

    # Market observation
    MARKET_DATA = "market_data"
    MARKET_SCAN = "market_scan"
    KILLZONE_ENTER = "killzone_enter"
    KILLZONE_EXIT = "killzone_exit"
    NEWS_CHECK = "news_check"

    # Analysis / signal
    SIGNAL_GENERATED = "signal_generated"
    SIGNAL_REJECTED = "signal_rejected"
    BIAS_UPDATE = "bias_update"
    CONFLUENCE_CHECK = "confluence_check"

    # Trade execution
    TRADE_ENTRY = "trade_entry"
    TRADE_EXIT = "trade_exit"
    TRADE_MODIFY = "trade_modify"
    TRADE_REJECTED = "trade_rejected"
    ORDER_PLACED = "order_placed"
    ORDER_FILLED = "order_filled"
    ORDER_CANCELLED = "order_cancelled"

    # Risk
    RISK_CHECK = "risk_check"
    RISK_BREACH = "risk_breach"
    RISK_SHUTDOWN = "risk_shutdown"
    DRAWDOWN_UPDATE = "drawdown_update"

    # Learning
    LESSON_LEARNED = "lesson_learned"
    PATTERN_UPDATE = "pattern_update"
    INSIGHT_GENERATED = "insight_generated"
    MEMORY_UPDATE = "memory_update"

    # Journal
    JOURNAL_ENTRY = "journal_entry"
    SESSION_SUMMARY = "session_summary"


@dataclass
class VexEvent:
    """Base event — every event in the system inherits from this."""
    event_type: EventType
    timestamp: datetime = field(default_factory=lambda: datetime.now(NY_TZ))
    source: str = "vex"  # "vex", "controller", "skill:scan", etc.
    data: Dict[str, Any] = field(default_factory=dict)
    event_id: int = 0  # Auto-assigned by EventStream

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.event_type.value,
            "timestamp": self.timestamp.isoformat(),
            "source": self.source,
            "data": self.data,
            "event_id": self.event_id,
        }

    def __repr__(self) -> str:
        return f"<{self.event_type.value} #{self.event_id} @ {self.timestamp.strftime('%H:%M:%S')}>"


# ═══════════════════════════════════════════════════════════════════════════════
# DOMAIN-SPECIFIC EVENT CLASSES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class MarketEvent(VexEvent):
    """Market data observation event."""
    symbol: str = ""
    timeframe: str = ""
    bid: float = 0.0
    ask: float = 0.0
    spread: float = 0.0
    killzone: str = ""
    tradeable: bool = True

    def __post_init__(self):
        if not self.event_type:
            self.event_type = EventType.MARKET_DATA
        self.data.update({
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "bid": self.bid,
            "ask": self.ask,
            "killzone": self.killzone,
        })


@dataclass
class SignalEvent(VexEvent):
    """Signal generated or rejected."""
    symbol: str = ""
    direction: str = ""  # "BUY" or "SELL"
    model: str = ""
    trade_type: str = ""  # "irl_to_erl" or "erl_to_irl"
    entry_price: float = 0.0
    stop_loss: float = 0.0
    take_profit: float = 0.0
    confidence: float = 0.0
    rr_ratio: float = 0.0
    confluences: List[str] = field(default_factory=list)
    rejection_reason: str = ""

    def __post_init__(self):
        if not self.event_type:
            self.event_type = EventType.SIGNAL_GENERATED
        self.data.update({
            "symbol": self.symbol,
            "direction": self.direction,
            "model": self.model,
            "entry_price": self.entry_price,
            "stop_loss": self.stop_loss,
            "take_profit": self.take_profit,
            "confidence": self.confidence,
            "rr_ratio": self.rr_ratio,
            "confluences": self.confluences,
        })


@dataclass
class TradeEvent(VexEvent):
    """Trade execution event — entry, exit, modify."""
    trade_id: str = ""
    symbol: str = ""
    direction: str = ""
    units: int = 0
    entry_price: float = 0.0
    exit_price: float = 0.0
    stop_loss: float = 0.0
    take_profit: float = 0.0
    pnl: float = 0.0
    pnl_pips: float = 0.0
    model: str = ""
    risk_amount: float = 0.0
    outcome: str = ""  # "win", "loss", "breakeven", ""

    def __post_init__(self):
        if not self.event_type:
            self.event_type = EventType.TRADE_ENTRY
        self.data.update({
            "trade_id": self.trade_id,
            "symbol": self.symbol,
            "direction": self.direction,
            "units": self.units,
            "entry_price": self.entry_price,
            "pnl": self.pnl,
            "model": self.model,
        })


@dataclass
class LearningEvent(VexEvent):
    """Learning system event — lessons, patterns, insights."""
    trade_id: str = ""
    symbol: str = ""
    model: str = ""
    lesson: str = ""
    category: str = ""  # "entry", "exit", "risk", "psychology", "timing"
    pattern_name: str = ""
    win_rate: float = 0.0
    insight: str = ""
    importance: float = 1.0

    def __post_init__(self):
        if not self.event_type:
            self.event_type = EventType.LESSON_LEARNED
        self.data.update({
            "trade_id": self.trade_id,
            "lesson": self.lesson,
            "category": self.category,
            "pattern_name": self.pattern_name,
        })


@dataclass
class RiskEvent(VexEvent):
    """Risk management event."""
    balance: float = 0.0
    drawdown: float = 0.0
    trades_today: int = 0
    risk_amount: float = 0.0
    can_trade: bool = True
    reason: str = ""

    def __post_init__(self):
        if not self.event_type:
            self.event_type = EventType.RISK_CHECK
        self.data.update({
            "balance": self.balance,
            "drawdown": self.drawdown,
            "can_trade": self.can_trade,
            "reason": self.reason,
        })


@dataclass
class SystemEvent(VexEvent):
    """System-level event."""
    message: str = ""
    level: str = "info"  # "info", "warning", "error", "critical"
    component: str = ""

    def __post_init__(self):
        if not self.event_type:
            self.event_type = EventType.SYSTEM_HEARTBEAT
        self.data.update({
            "message": self.message,
            "level": self.level,
            "component": self.component,
        })
