"""
PerformanceTracker — Tracks real-time trading performance metrics.

Monitors:
  - Win rate (overall + per symbol + per model)
  - P&L (realized + unrealized)
  - Drawdown (current + max)
  - Consecutive wins/losses
  - Risk-adjusted returns (Sharpe-like)
  - Session performance comparison

Exposes all metrics via status() for the controller dashboard.
"""

from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

NY_TZ = ZoneInfo("America/New_York")


@dataclass
class TradeRecord:
    """A completed trade for performance tracking."""
    trade_id: str
    symbol: str
    model: str
    direction: str
    entry_price: float
    exit_price: float
    pnl_pips: float
    pnl_usd: float
    rr_achieved: float
    outcome: str  # "win", "loss", "breakeven"
    killzone: str
    opened_at: datetime
    closed_at: datetime
    duration_minutes: float = 0.0


class PerformanceTracker:
    """
    Tracks and computes trading performance metrics in real-time.
    
    Usage:
        tracker = PerformanceTracker(starting_balance=10000)
        tracker.record_trade(...)
        print(tracker.status())
    """

    def __init__(self, starting_balance: float = 10000.0):
        self.starting_balance = starting_balance
        self.current_balance = starting_balance
        self.trades: List[TradeRecord] = []
        self._peak_balance = starting_balance
        self._max_drawdown_usd = 0.0
        self._max_drawdown_pct = 0.0
        self._consecutive_wins = 0
        self._consecutive_losses = 0
        self._max_consecutive_wins = 0
        self._max_consecutive_losses = 0
        self._daily_pnl: Dict[str, float] = {}
        self._symbol_stats: Dict[str, Dict] = {}
        self._model_stats: Dict[str, Dict] = {}
        self._session_stats: Dict[str, Dict] = {}

    def record_trade(
        self,
        trade_id: str,
        symbol: str,
        model: str,
        direction: str,
        entry_price: float,
        exit_price: float,
        pnl_pips: float,
        pnl_usd: float,
        rr_achieved: float,
        killzone: str = "",
        opened_at: Optional[datetime] = None,
        closed_at: Optional[datetime] = None,
    ) -> None:
        """Record a completed trade and update all metrics."""
        now = datetime.now(NY_TZ)
        opened = opened_at or now
        closed = closed_at or now
        
        outcome = "win" if pnl_usd > 0 else ("breakeven" if pnl_usd == 0 else "loss")
        duration = (closed - opened).total_seconds() / 60

        record = TradeRecord(
            trade_id=trade_id,
            symbol=symbol,
            model=model,
            direction=direction,
            entry_price=entry_price,
            exit_price=exit_price,
            pnl_pips=pnl_pips,
            pnl_usd=pnl_usd,
            rr_achieved=rr_achieved,
            outcome=outcome,
            killzone=killzone,
            opened_at=opened,
            closed_at=closed,
            duration_minutes=duration,
        )
        self.trades.append(record)

        # Update balance
        self.current_balance += pnl_usd

        # Update peak and drawdown
        if self.current_balance > self._peak_balance:
            self._peak_balance = self.current_balance
        dd_usd = self._peak_balance - self.current_balance
        dd_pct = dd_usd / self._peak_balance * 100 if self._peak_balance > 0 else 0
        if dd_usd > self._max_drawdown_usd:
            self._max_drawdown_usd = dd_usd
        if dd_pct > self._max_drawdown_pct:
            self._max_drawdown_pct = dd_pct

        # Update streaks
        if outcome == "win":
            self._consecutive_wins += 1
            self._consecutive_losses = 0
            self._max_consecutive_wins = max(self._max_consecutive_wins, self._consecutive_wins)
        elif outcome == "loss":
            self._consecutive_losses += 1
            self._consecutive_wins = 0
            self._max_consecutive_losses = max(self._max_consecutive_losses, self._consecutive_losses)

        # Update daily P&L
        day_key = closed.strftime("%Y-%m-%d")
        self._daily_pnl[day_key] = self._daily_pnl.get(day_key, 0) + pnl_usd

        # Update per-symbol stats
        self._update_bucket(self._symbol_stats, symbol, pnl_usd, pnl_pips, rr_achieved, outcome)
        
        # Update per-model stats
        self._update_bucket(self._model_stats, model, pnl_usd, pnl_pips, rr_achieved, outcome)
        
        # Update per-session stats
        if killzone:
            self._update_bucket(self._session_stats, killzone, pnl_usd, pnl_pips, rr_achieved, outcome)

    def _update_bucket(
        self, bucket: Dict, key: str, pnl_usd: float, pnl_pips: float,
        rr: float, outcome: str
    ) -> None:
        """Update a stats bucket (symbol/model/session)."""
        if key not in bucket:
            bucket[key] = {
                "total": 0, "wins": 0, "losses": 0,
                "pnl_usd": 0.0, "pnl_pips": 0.0,
                "avg_rr": 0.0, "best_trade": 0.0, "worst_trade": 0.0,
            }
        s = bucket[key]
        s["total"] += 1
        s["pnl_usd"] += pnl_usd
        s["pnl_pips"] += pnl_pips
        if outcome == "win":
            s["wins"] += 1
        elif outcome == "loss":
            s["losses"] += 1
        # Running average R:R
        n = s["total"]
        s["avg_rr"] = s["avg_rr"] * (n - 1) / n + rr / n
        s["best_trade"] = max(s["best_trade"], pnl_usd)
        s["worst_trade"] = min(s["worst_trade"], pnl_usd)

    # ─── Queries ──────────────────────────────────────────────────────────

    @property
    def total_trades(self) -> int:
        return len(self.trades)

    @property
    def wins(self) -> int:
        return sum(1 for t in self.trades if t.outcome == "win")

    @property
    def losses(self) -> int:
        return sum(1 for t in self.trades if t.outcome == "loss")

    @property
    def win_rate(self) -> float:
        return self.wins / self.total_trades if self.total_trades > 0 else 0.0

    @property
    def total_pnl_usd(self) -> float:
        return sum(t.pnl_usd for t in self.trades)

    @property
    def total_pnl_pips(self) -> float:
        return sum(t.pnl_pips for t in self.trades)

    @property
    def avg_rr(self) -> float:
        if not self.trades:
            return 0.0
        return sum(t.rr_achieved for t in self.trades) / len(self.trades)

    @property
    def profit_factor(self) -> float:
        gross_profit = sum(t.pnl_usd for t in self.trades if t.pnl_usd > 0)
        gross_loss = abs(sum(t.pnl_usd for t in self.trades if t.pnl_usd < 0))
        return gross_profit / gross_loss if gross_loss > 0 else (0.0 if gross_profit == 0 else 999.99)

    @property
    def current_drawdown_usd(self) -> float:
        return self._peak_balance - self.current_balance

    @property
    def current_drawdown_pct(self) -> float:
        return (self.current_drawdown_usd / self._peak_balance * 100
                if self._peak_balance > 0 else 0)

    def today_pnl(self) -> float:
        today = datetime.now(NY_TZ).strftime("%Y-%m-%d")
        return self._daily_pnl.get(today, 0.0)

    def today_trades(self) -> int:
        today = datetime.now(NY_TZ).date()
        return sum(1 for t in self.trades if t.closed_at.date() == today)

    def get_symbol_stats(self, symbol: str) -> Dict:
        stats = self._symbol_stats.get(symbol, {})
        if stats:
            total = stats["total"]
            stats["win_rate"] = stats["wins"] / total if total > 0 else 0
        return stats

    def get_model_stats(self, model: str) -> Dict:
        stats = self._model_stats.get(model, {})
        if stats:
            total = stats["total"]
            stats["win_rate"] = stats["wins"] / total if total > 0 else 0
        return stats

    # ─── Dashboard ────────────────────────────────────────────────────────

    def status(self) -> Dict[str, Any]:
        """Full performance status for dashboard."""
        return {
            "total_trades": self.total_trades,
            "win_rate": round(self.win_rate * 100, 1),
            "wins": self.wins,
            "losses": self.losses,
            "total_pnl_usd": round(self.total_pnl_usd, 2),
            "total_pnl_pips": round(self.total_pnl_pips, 1),
            "avg_rr": round(self.avg_rr, 2),
            "profit_factor": round(self.profit_factor, 2),
            "current_balance": round(self.current_balance, 2),
            "starting_balance": round(self.starting_balance, 2),
            "return_pct": round(
                (self.current_balance - self.starting_balance) / self.starting_balance * 100, 2
            ),
            "drawdown": {
                "current_usd": round(self.current_drawdown_usd, 2),
                "current_pct": round(self.current_drawdown_pct, 2),
                "max_usd": round(self._max_drawdown_usd, 2),
                "max_pct": round(self._max_drawdown_pct, 2),
            },
            "streaks": {
                "current_wins": self._consecutive_wins,
                "current_losses": self._consecutive_losses,
                "max_wins": self._max_consecutive_wins,
                "max_losses": self._max_consecutive_losses,
            },
            "today": {
                "pnl": round(self.today_pnl(), 2),
                "trades": self.today_trades(),
            },
            "by_symbol": {
                k: {**v, "win_rate": round(v["wins"] / v["total"] * 100, 1) if v["total"] > 0 else 0}
                for k, v in self._symbol_stats.items()
            },
            "by_model": {
                k: {**v, "win_rate": round(v["wins"] / v["total"] * 100, 1) if v["total"] > 0 else 0}
                for k, v in self._model_stats.items()
            },
            "by_session": {
                k: {**v, "win_rate": round(v["wins"] / v["total"] * 100, 1) if v["total"] > 0 else 0}
                for k, v in self._session_stats.items()
            },
        }

    def print_summary(self) -> None:
        """Print a formatted performance summary."""
        s = self.status()
        print("\n" + "═" * 50)
        print("📊 PERFORMANCE SUMMARY")
        print("═" * 50)
        print(f"  Trades: {s['total_trades']} | Win Rate: {s['win_rate']}%")
        print(f"  P&L: ${s['total_pnl_usd']:+.2f} ({s['total_pnl_pips']:+.1f} pips)")
        print(f"  Avg R:R: {s['avg_rr']} | Profit Factor: {s['profit_factor']}")
        print(f"  Balance: ${s['current_balance']:,.2f} ({s['return_pct']:+.1f}%)")
        dd = s["drawdown"]
        print(f"  Drawdown: ${dd['current_usd']:.2f} ({dd['current_pct']:.1f}%) | Max: ${dd['max_usd']:.2f} ({dd['max_pct']:.1f}%)")
        streaks = s["streaks"]
        print(f"  Streaks: W{streaks['current_wins']} L{streaks['current_losses']} | Best: W{streaks['max_wins']} Worst: L{streaks['max_losses']}")
        
        if s["by_symbol"]:
            print("\n  By Symbol:")
            for sym, stats in s["by_symbol"].items():
                print(f"    {sym}: {stats['total']} trades | {stats['win_rate']}% WR | ${stats['pnl_usd']:+.2f}")
        
        if s["by_model"]:
            print("\n  By Model:")
            for model, stats in s["by_model"].items():
                print(f"    {model}: {stats['total']} trades | {stats['win_rate']}% WR | ${stats['pnl_usd']:+.2f}")
        
        print("═" * 50)

    def __repr__(self) -> str:
        return (
            f"PerformanceTracker(trades={self.total_trades}, "
            f"wr={self.win_rate*100:.0f}%, "
            f"pnl=${self.total_pnl_usd:+.2f}, "
            f"dd=${self.current_drawdown_usd:.2f})"
        )
