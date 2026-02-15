"""
ShortTermMemory — Session-scoped working memory.

Tracks everything about the current trading session:
  - Scanned symbols and their latest prices
  - Signals generated and rejected (with reasons)
  - Trades placed and their current P&L
  - Killzone transitions
  - Recent events (sliding window)

Resets on each boot. Lives entirely in RAM.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo
from collections import deque

NY_TZ = ZoneInfo("America/New_York")


@dataclass
class SignalMemory:
    """A remembered signal — accepted or rejected."""
    symbol: str
    direction: str
    model: str
    confidence: float
    rr_ratio: float
    accepted: bool
    rejection_reason: Optional[str] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(NY_TZ))
    entry_price: float = 0.0
    stop_loss: float = 0.0
    take_profit: float = 0.0


@dataclass
class TradeMemory:
    """A remembered trade — open or closed."""
    trade_id: str
    symbol: str
    direction: str
    model: str
    entry_price: float
    stop_loss: float
    take_profit: float
    units: int
    opened_at: datetime = field(default_factory=lambda: datetime.now(NY_TZ))
    closed_at: Optional[datetime] = None
    close_price: Optional[float] = None
    pnl: float = 0.0
    status: str = "open"  # open, closed, cancelled


class ShortTermMemory:
    """
    Session-scoped working memory. Resets on boot.
    
    Provides quick lookups for the controller:
      - What have we scanned this cycle?
      - What signals have we seen today?
      - How many trades have we placed?
      - What was the last rejection reason for X symbol?
    """

    def __init__(self, max_events: int = 500):
        self.session_start = datetime.now(NY_TZ)
        self.cycle_count = 0
        
        # Latest prices per symbol
        self.prices: Dict[str, Dict[str, float]] = {}
        
        # Signals seen this session
        self.signals: List[SignalMemory] = []
        
        # Trades placed this session
        self.trades: List[TradeMemory] = []
        
        # Recent events (sliding window)
        self.recent_events: deque = deque(maxlen=max_events)
        
        # Killzone history
        self.killzone_transitions: List[Dict[str, Any]] = []
        self._current_killzone: Optional[str] = None
        
        # Analysis cache (avoid re-analyzing same symbol in same cycle)
        self._analysis_cache: Dict[str, Dict[str, Any]] = {}
        self._cache_cycle: int = 0
        
        # Rejection tracking (for pattern detection)
        self.rejection_counts: Dict[str, int] = {}
        self.rejection_reasons: Dict[str, List[str]] = {}

    def update_price(self, symbol: str, bid: float, ask: float, spread: float) -> None:
        """Update latest price for a symbol."""
        self.prices[symbol] = {
            "bid": bid,
            "ask": ask,
            "spread": spread,
            "mid": (bid + ask) / 2,
            "updated_at": datetime.now(NY_TZ).isoformat(),
        }

    def record_signal(self, signal: SignalMemory) -> None:
        """Record a signal (accepted or rejected)."""
        self.signals.append(signal)
        if not signal.accepted:
            self.rejection_counts[signal.symbol] = self.rejection_counts.get(signal.symbol, 0) + 1
            if signal.symbol not in self.rejection_reasons:
                self.rejection_reasons[signal.symbol] = []
            if signal.rejection_reason:
                self.rejection_reasons[signal.symbol].append(signal.rejection_reason)

    def record_trade(self, trade: TradeMemory) -> None:
        """Record a new trade."""
        self.trades.append(trade)

    def close_trade(self, trade_id: str, close_price: float, pnl: float) -> None:
        """Mark a trade as closed."""
        for trade in self.trades:
            if trade.trade_id == trade_id:
                trade.status = "closed"
                trade.closed_at = datetime.now(NY_TZ)
                trade.close_price = close_price
                trade.pnl = pnl
                break

    def record_event(self, event: Any) -> None:
        """Add an event to the sliding window."""
        self.recent_events.append(event)

    def update_killzone(self, killzone: Optional[str]) -> None:
        """Track killzone transitions."""
        if killzone != self._current_killzone:
            self.killzone_transitions.append({
                "from": self._current_killzone,
                "to": killzone,
                "at": datetime.now(NY_TZ).isoformat(),
            })
            self._current_killzone = killzone

    def cache_analysis(self, symbol: str, result: Dict[str, Any], cycle: int) -> None:
        """Cache analysis result for current cycle."""
        if cycle != self._cache_cycle:
            self._analysis_cache.clear()
            self._cache_cycle = cycle
        self._analysis_cache[symbol] = result

    def get_cached_analysis(self, symbol: str, cycle: int) -> Optional[Dict[str, Any]]:
        """Get cached analysis if still valid for current cycle."""
        if cycle == self._cache_cycle:
            return self._analysis_cache.get(symbol)
        return None

    # ─── Queries ──────────────────────────────────────────────────────────

    @property
    def open_trades(self) -> List[TradeMemory]:
        return [t for t in self.trades if t.status == "open"]

    @property
    def closed_trades(self) -> List[TradeMemory]:
        return [t for t in self.trades if t.status == "closed"]

    @property
    def trades_today(self) -> int:
        return len(self.trades)

    @property
    def accepted_signals(self) -> List[SignalMemory]:
        return [s for s in self.signals if s.accepted]

    @property
    def rejected_signals(self) -> List[SignalMemory]:
        return [s for s in self.signals if not s.accepted]

    @property
    def session_pnl(self) -> float:
        return sum(t.pnl for t in self.closed_trades)

    @property
    def win_rate(self) -> float:
        closed = self.closed_trades
        if not closed:
            return 0.0
        wins = sum(1 for t in closed if t.pnl > 0)
        return wins / len(closed)

    def get_symbol_rejections(self, symbol: str) -> List[str]:
        """Get rejection reasons for a symbol this session."""
        return self.rejection_reasons.get(symbol, [])

    def get_last_signal(self, symbol: Optional[str] = None) -> Optional[SignalMemory]:
        """Get the most recent signal, optionally filtered by symbol."""
        for signal in reversed(self.signals):
            if symbol is None or signal.symbol == symbol:
                return signal
        return None

    def to_context(self) -> Dict[str, Any]:
        """Export session state as context dict for analysis enrichment."""
        return {
            "session_start": self.session_start.isoformat(),
            "cycle_count": self.cycle_count,
            "trades_today": self.trades_today,
            "open_trades": len(self.open_trades),
            "session_pnl": self.session_pnl,
            "win_rate": self.win_rate,
            "total_signals": len(self.signals),
            "accepted_signals": len(self.accepted_signals),
            "rejected_signals": len(self.rejected_signals),
            "current_killzone": self._current_killzone,
            "killzone_transitions": len(self.killzone_transitions),
            "symbols_scanned": list(self.prices.keys()),
            "top_rejections": {
                k: v for k, v in sorted(
                    self.rejection_counts.items(), key=lambda x: -x[1]
                )[:5]
            },
        }

    def __repr__(self) -> str:
        return (
            f"ShortTermMemory(trades={self.trades_today}, "
            f"signals={len(self.signals)}, "
            f"pnl=${self.session_pnl:.2f}, "
            f"killzone={self._current_killzone})"
        )
