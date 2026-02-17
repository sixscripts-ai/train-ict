"""
VEX Live Dashboard — Rich-powered terminal UI for real-time agent monitoring.

Renders a 4-panel layout:
  ┌─────────────────────┬───────────────────────────┐
  │  MARKET STATE       │  GATE TRACE               │
  │  Prices + killzone  │  Per-symbol gate results   │
  ├─────────────────────┼───────────────────────────┤
  │  POSITIONS          │  CYCLE LOG                │
  │  Open trades + PnL  │  Recent cycle decisions   │
  └─────────────────────┴───────────────────────────┘

Usage:
    dashboard = VexLiveDashboard()
    dashboard.update_cycle(cycle_data)   # called by controller after each step()
    dashboard.render()                   # prints the full layout once
    # OR
    with dashboard.live():               # auto-refreshing live mode
        controller.run(...)
"""

from __future__ import annotations

import io
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

from rich.console import Console, Group
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

NY_TZ = ZoneInfo("America/New_York")

# ── Palette ──────────────────────────────────────────────────────────────────

CYAN = "cyan"
GREEN = "green"
RED = "red"
YELLOW = "yellow"
DIM = "dim"
BOLD = "bold"
HEADER_STYLE = "bold cyan"
BORDER_STYLE = "bright_black"


# ── Data containers ─────────────────────────────────────────────────────────


@dataclass
class MarketQuote:
    symbol: str
    price: float
    direction: str = ""  # "up" / "down" / ""


@dataclass
class Position:
    trade_id: str
    symbol: str
    direction: str
    units: float
    unrealized_pnl: float


@dataclass
class CycleRecord:
    cycle: int
    time: str  # "HH:MM:SS ET"
    killzone: str
    decision: str  # "NO TRADE", "BUY EUR_USD", etc.
    rejection: str = ""
    gate_stopped: str = ""  # gate that rejected, e.g. "G6_PD_ARRAYS"


@dataclass
class DashboardState:
    """Mutable state the controller pushes into."""

    # Header
    cycle_count: int = 0
    agent_state: str = "IDLE"
    killzone: str = "—"
    mode: str = "LIVE"
    balance: float = 0.0

    # Market
    quotes: List[MarketQuote] = field(default_factory=list)

    # Gate trace (latest per symbol)
    gate_traces: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)
    # symbol -> [{gate, passed, summary, details}, ...]
    latest_symbol: str = ""
    latest_decision: str = ""
    latest_rejection: str = ""

    # Positions
    positions: List[Position] = field(default_factory=list)

    # Cycle log (ring buffer, newest first)
    cycle_log: deque = field(default_factory=lambda: deque(maxlen=20))

    # Timing
    last_update: Optional[datetime] = None


# ── Dashboard ────────────────────────────────────────────────────────────────


class VexLiveDashboard:
    """Renders the VEX live TUI using rich."""

    def __init__(self) -> None:
        self.state = DashboardState()
        self.console = Console()
        self._live: Optional[Live] = None

    # ── Public API (called by controller) ────────────────────────────────

    def set_mode(self, dry_run: bool) -> None:
        self.state.mode = "DRY RUN" if dry_run else "LIVE"

    def set_balance(self, balance: float) -> None:
        self.state.balance = balance

    def update_header(
        self,
        cycle: int,
        state: str,
        killzone: str,
    ) -> None:
        self.state.cycle_count = cycle
        self.state.agent_state = state
        self.state.killzone = killzone
        self.state.last_update = datetime.now(NY_TZ)

    def update_quotes(self, quotes: List[MarketQuote]) -> None:
        self.state.quotes = quotes

    def update_gate_trace(
        self,
        symbol: str,
        trace: List[Dict[str, Any]],
        decision: str,
        rejection: str = "",
    ) -> None:
        self.state.gate_traces[symbol] = trace
        self.state.latest_symbol = symbol
        self.state.latest_decision = decision
        self.state.latest_rejection = rejection

    def update_positions(self, positions: List[Position]) -> None:
        self.state.positions = positions

    def log_cycle(self, record: CycleRecord) -> None:
        self.state.cycle_log.appendleft(record)

    # ── Rendering ────────────────────────────────────────────────────────

    def build_layout(self) -> Layout:
        """Construct the full 4-panel Layout."""
        layout = Layout()

        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="body"),
            Layout(name="footer", size=1),
        )

        layout["body"].split_row(
            Layout(name="left", ratio=1),
            Layout(name="right", ratio=2),
        )

        layout["left"].split_column(
            Layout(name="market", ratio=1),
            Layout(name="positions", ratio=1),
        )

        layout["right"].split_column(
            Layout(name="gates", ratio=2),
            Layout(name="log", ratio=1),
        )

        # Populate
        layout["header"].update(self._header_panel())
        layout["market"].update(self._market_panel())
        layout["positions"].update(self._positions_panel())
        layout["gates"].update(self._gates_panel())
        layout["log"].update(self._log_panel())
        layout["footer"].update(self._footer_bar())

        return layout

    def render(self) -> None:
        """Print the dashboard once (non-live mode)."""
        self.console.print(self.build_layout())

    def refresh(self) -> None:
        """Update the live display if active."""
        if self._live:
            self._live.update(self.build_layout())

    def start_live(self) -> Live:
        """Start a Live context for auto-refreshing display."""
        self._live = Live(
            self.build_layout(),
            console=self.console,
            refresh_per_second=1,
            screen=True,
        )
        return self._live

    def stop_live(self) -> None:
        if self._live:
            self._live.stop()
            self._live = None

    # ── Panel builders ───────────────────────────────────────────────────

    def _header_panel(self) -> Panel:
        s = self.state
        now = s.last_update or datetime.now(NY_TZ)
        time_str = now.strftime("%H:%M:%S ET")

        mode_style = RED if s.mode == "LIVE" else YELLOW
        kz_style = GREEN if s.killzone not in ("—", "none", "No Session") else DIM

        header = Text()
        header.append("  VEX ", style="bold white on blue")
        header.append(f"  {s.mode} ", style=f"bold white on {mode_style}")
        header.append(f"  Cycle #{s.cycle_count}  ", style=BOLD)
        header.append(f"{time_str}  ", style=CYAN)
        header.append(f"{s.killzone}  ", style=kz_style)
        header.append(f"[{s.agent_state}]  ", style=DIM)
        if s.balance:
            bal_style = GREEN if s.balance >= 10000 else RED
            header.append(f"${s.balance:,.2f}", style=bal_style)

        return Panel(header, style=BORDER_STYLE, height=3)

    def _market_panel(self) -> Panel:
        table = Table(
            show_header=True,
            header_style=HEADER_STYLE,
            box=None,
            padding=(0, 1),
            expand=True,
        )
        table.add_column("Symbol", style=BOLD)
        table.add_column("Price", justify="right")
        table.add_column("", width=2)

        if self.state.quotes:
            for q in self.state.quotes:
                arrow = ""
                arrow_style = DIM
                if q.direction == "up":
                    arrow = "▲"
                    arrow_style = GREEN
                elif q.direction == "down":
                    arrow = "▼"
                    arrow_style = RED
                # Smart decimal places: 2 for JPY/XAU, 5 for others
                dec = 2 if "JPY" in q.symbol or "XAU" in q.symbol else 5
                table.add_row(
                    q.symbol.replace("_", "/"),
                    f"{q.price:.{dec}f}",
                    Text(arrow, style=arrow_style),
                )
        else:
            table.add_row("—", "—", "")

        return Panel(table, title="Market", border_style=BORDER_STYLE)

    def _positions_panel(self) -> Panel:
        table = Table(
            show_header=True,
            header_style=HEADER_STYLE,
            box=None,
            padding=(0, 1),
            expand=True,
        )
        table.add_column("ID", style=DIM, width=6, no_wrap=True)
        table.add_column("Pair", style=BOLD, no_wrap=True)
        table.add_column("Dir", width=3, no_wrap=True)
        table.add_column("PnL", justify="right", no_wrap=True)

        if self.state.positions:
            for p in self.state.positions:
                pnl_style = GREEN if p.unrealized_pnl >= 0 else RED
                dir_style = GREEN if p.direction == "BUY" else RED
                table.add_row(
                    f"#{p.trade_id[-4:]}",
                    p.symbol.replace("_", "/"),
                    Text(p.direction[:1], style=dir_style),
                    Text(f"${p.unrealized_pnl:+,.0f}", style=pnl_style),
                )
        else:
            table.add_row("—", "No open positions", "", "")

        return Panel(table, title="Positions", border_style=BORDER_STYLE)

    def _gates_panel(self) -> Panel:
        s = self.state
        symbol = s.latest_symbol
        trace = s.gate_traces.get(symbol, [])

        if not trace:
            content = Text("  Waiting for analysis cycle...", style=DIM)
            return Panel(content, title="Gate Trace", border_style=BORDER_STYLE)

        table = Table(
            show_header=False,
            box=None,
            padding=(0, 1),
            expand=True,
        )
        table.add_column("", width=4)  # icon
        table.add_column("Gate", width=14, no_wrap=True)
        table.add_column("Summary", no_wrap=False, overflow="fold")

        # Short display names for gates
        short = {
            "G1_KILLZONE": "G1 KILLZONE",
            "G2_SESSION": "G2 SESSION",
            "G3_BIAS": "G3 BIAS",
            "G4_LIQUIDITY": "G4 LIQUIDITY",
            "G5_SWEEP": "G5 SWEEP",
            "G6_PD_ARRAYS": "G6 PD_ARRAY",
            "G7_CLASSIFY": "G7 CLASSIFY",
            "G7b_DISPLACEMENT": "G7b DISPLACE",
            "G7c_GRAPH": "G7c GRAPH",
            "G8_MODEL": "G8 MODEL",
            "G9_RR_CHECK": "G9 R:R",
        }

        for g in trace:
            passed = g.get("passed", False)
            icon = (
                Text(" + ", style="bold green")
                if passed
                else Text(" X ", style="bold red")
            )
            gate = g.get("gate") or "?"
            label = short.get(gate, gate[:14])
            summary = g.get("summary", "")
            style = "" if passed else "bold red"
            table.add_row(icon, Text(label, style=style), summary)

        # Decision row
        table.add_row("", "", "")
        if "BUY" in s.latest_decision or "SELL" in s.latest_decision:
            dec_text = Text(f">> {s.latest_decision}", style="bold green")
        else:
            rej = f" ({s.latest_rejection})" if s.latest_rejection else ""
            dec_text = Text(f">> {s.latest_decision}{rej}", style="bold red")
        table.add_row("", "", dec_text)

        title = f"Gate Trace — {symbol.replace('_', '/')}"
        return Panel(table, title=title, border_style=BORDER_STYLE)

    def _log_panel(self) -> Panel:
        table = Table(
            show_header=True,
            header_style=HEADER_STYLE,
            box=None,
            padding=(0, 1),
            expand=True,
        )
        table.add_column("#", width=4, style=DIM)
        table.add_column("Time", width=12, no_wrap=True)
        table.add_column("KZ", width=8, no_wrap=True)
        table.add_column("Decision", no_wrap=True)
        table.add_column("Gate", style=DIM, no_wrap=True)

        if self.state.cycle_log:
            for rec in self.state.cycle_log:
                dec_style = (
                    GREEN if "BUY" in rec.decision or "SELL" in rec.decision else DIM
                )
                table.add_row(
                    str(rec.cycle),
                    rec.time,
                    rec.killzone,
                    Text(rec.decision, style=dec_style),
                    rec.gate_stopped or "",
                )
        else:
            table.add_row("—", "—", "—", "No cycles yet", "")

        return Panel(table, title="Cycle Log", border_style=BORDER_STYLE)

    def _footer_bar(self) -> Text:
        t = Text()
        t.append(" Ctrl+C", style="bold")
        t.append(" quit  ", style=DIM)
        t.append("--dashboard", style="bold")
        t.append(" toggle  ", style=DIM)
        t.append("--cycles N", style="bold")
        t.append(" limit  ", style=DIM)
        return t
