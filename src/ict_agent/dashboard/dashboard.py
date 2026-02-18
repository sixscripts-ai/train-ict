"""
VEX Performance Dashboard - HTML trading analytics dashboard.

Generates:
- Equity curve visualization
- Win rate by pair, session, day, setup
- Calendar heatmap
- Key performance metrics
- Psychology insights
"""

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
from collections import defaultdict
import webbrowser

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

MEMORY_DIR = PROJECT_ROOT / "data" / "memory"
JOURNAL_DIR = PROJECT_ROOT / "journal" / "ashton"
DASHBOARD_DIR = PROJECT_ROOT / "hub"
TRADES_DB = JOURNAL_DIR / "trades_database.json"


class PerformanceDashboard:
    """
    Generates an HTML performance dashboard.
    """
    
    def __init__(self):
        self.trades = self._load_trades()
        self.profile = self._load_json("trading_profile.json")
        self.milestones = self._load_json("milestones.json")
    
    def _load_trades(self) -> List[Dict]:
        """Load trades from database."""
        if TRADES_DB.exists():
            with open(TRADES_DB) as f:
                data = json.load(f)
                return data.get("trades", [])
        return []
    
    def _load_json(self, filename: str) -> Dict:
        """Load JSON from memory."""
        path = MEMORY_DIR / filename
        if path.exists():
            with open(path) as f:
                return json.load(f)
        return {}
    
    def calculate_stats(self) -> Dict:
        """Calculate all performance statistics."""
        stats = {
            "total_trades": 0,
            "wins": 0,
            "losses": 0,
            "breakeven": 0,
            "win_rate": 0,
            "total_pnl": 0,
            "avg_win": 0,
            "avg_loss": 0,
            "profit_factor": 0,
            "largest_win": 0,
            "largest_loss": 0,
            "avg_rr": 0,
            "expectancy": 0,
            "by_pair": {},
            "by_session": {},
            "by_day": {},
            "by_setup": {},
            "equity_curve": [],
            "calendar": {},
            "streaks": {"current_win": 0, "current_loss": 0, "max_win": 0, "max_loss": 0}
        }
        
        if not self.trades:
            return stats
        
        # Filter closed trades
        closed_trades = [t for t in self.trades if t.get("status") == "closed"]
        
        if not closed_trades:
            return stats
        
        wins = []
        losses = []
        equity = 10000  # Starting balance
        equity_curve = [(0, equity)]
        
        # Group by categories
        by_pair = defaultdict(lambda: {"wins": 0, "losses": 0, "pnl": 0})
        by_session = defaultdict(lambda: {"wins": 0, "losses": 0, "pnl": 0})
        by_day = defaultdict(lambda: {"wins": 0, "losses": 0, "pnl": 0})
        by_setup = defaultdict(lambda: {"wins": 0, "losses": 0, "pnl": 0})
        calendar = defaultdict(lambda: {"trades": 0, "pnl": 0, "result": "neutral"})
        
        # Streak tracking
        current_streak = 0
        max_win_streak = 0
        max_loss_streak = 0
        
        for i, trade in enumerate(closed_trades):
            pre_trade = trade.get("pre_trade", {})
            result = trade.get("result", "")
            pnl = trade.get("pnl_dollars", 0)
            pair = pre_trade.get("pair", "UNKNOWN")
            session = pre_trade.get("killzone", "UNKNOWN")
            setup_grade = pre_trade.get("setup_grade", "UNKNOWN")
            
            # Get date and day of week
            created = trade.get("created_at", "")
            if created:
                try:
                    dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
                    day_name = dt.strftime("%A")
                    date_str = dt.strftime("%Y-%m-%d")
                except:
                    day_name = "UNKNOWN"
                    date_str = "UNKNOWN"
            else:
                day_name = "UNKNOWN"
                date_str = "UNKNOWN"
            
            # Update totals
            stats["total_trades"] += 1
            stats["total_pnl"] += pnl
            equity += pnl
            equity_curve.append((i + 1, equity))
            
            # Update calendar
            calendar[date_str]["trades"] += 1
            calendar[date_str]["pnl"] += pnl
            
            if result == "WIN":
                stats["wins"] += 1
                wins.append(pnl)
                by_pair[pair]["wins"] += 1
                by_session[session]["wins"] += 1
                by_day[day_name]["wins"] += 1
                by_setup[setup_grade]["wins"] += 1
                calendar[date_str]["result"] = "win" if calendar[date_str]["pnl"] > 0 else "loss"
                
                # Streak
                if current_streak >= 0:
                    current_streak += 1
                else:
                    current_streak = 1
                max_win_streak = max(max_win_streak, current_streak)
                
            elif result == "LOSS":
                stats["losses"] += 1
                losses.append(pnl)
                by_pair[pair]["losses"] += 1
                by_session[session]["losses"] += 1
                by_day[day_name]["losses"] += 1
                by_setup[setup_grade]["losses"] += 1
                calendar[date_str]["result"] = "loss" if calendar[date_str]["pnl"] < 0 else "win"
                
                # Streak
                if current_streak <= 0:
                    current_streak -= 1
                else:
                    current_streak = -1
                max_loss_streak = max(max_loss_streak, abs(current_streak))
                
            else:
                stats["breakeven"] += 1
            
            # Update category PnL
            by_pair[pair]["pnl"] += pnl
            by_session[session]["pnl"] += pnl
            by_day[day_name]["pnl"] += pnl
            by_setup[setup_grade]["pnl"] += pnl
        
        # Calculate derived stats
        total_decided = stats["wins"] + stats["losses"]
        if total_decided > 0:
            stats["win_rate"] = round(stats["wins"] / total_decided * 100, 1)
        
        if wins:
            stats["avg_win"] = round(sum(wins) / len(wins), 2)
            stats["largest_win"] = round(max(wins), 2)
        
        if losses:
            stats["avg_loss"] = round(sum(losses) / len(losses), 2)
            stats["largest_loss"] = round(min(losses), 2)
        
        # Profit factor
        gross_profit = sum(wins) if wins else 0
        gross_loss = abs(sum(losses)) if losses else 0
        if gross_loss > 0:
            stats["profit_factor"] = round(gross_profit / gross_loss, 2)
        
        # Expectancy
        if total_decided > 0:
            win_rate = stats["wins"] / total_decided
            avg_win = stats["avg_win"] if wins else 0
            avg_loss = abs(stats["avg_loss"]) if losses else 0
            stats["expectancy"] = round((win_rate * avg_win) - ((1 - win_rate) * avg_loss), 2)
        
        # Calculate win rates by category
        def calc_win_rate(d):
            total = d["wins"] + d["losses"]
            return round(d["wins"] / total * 100, 1) if total > 0 else 0
        
        stats["by_pair"] = {k: {**v, "win_rate": calc_win_rate(v)} for k, v in by_pair.items()}
        stats["by_session"] = {k: {**v, "win_rate": calc_win_rate(v)} for k, v in by_session.items()}
        stats["by_day"] = {k: {**v, "win_rate": calc_win_rate(v)} for k, v in by_day.items()}
        stats["by_setup"] = {k: {**v, "win_rate": calc_win_rate(v)} for k, v in by_setup.items()}
        stats["equity_curve"] = equity_curve
        stats["calendar"] = dict(calendar)
        stats["streaks"] = {
            "current_win": current_streak if current_streak > 0 else 0,
            "current_loss": abs(current_streak) if current_streak < 0 else 0,
            "max_win": max_win_streak,
            "max_loss": max_loss_streak
        }
        stats["total_pnl"] = round(stats["total_pnl"], 2)
        
        return stats
    
    def generate_html(self, stats: Dict) -> str:
        """Generate HTML dashboard."""
        
        # Generate equity curve data for chart
        equity_data = stats.get("equity_curve", [(0, 10000)])
        equity_labels = [str(e[0]) for e in equity_data]
        equity_values = [e[1] for e in equity_data]
        
        # Generate calendar data
        calendar = stats.get("calendar", {})
        calendar_html = self._generate_calendar_html(calendar)
        
        # Generate category tables
        pair_rows = self._generate_category_rows(stats.get("by_pair", {}))
        session_rows = self._generate_category_rows(stats.get("by_session", {}))
        day_rows = self._generate_category_rows(stats.get("by_day", {}))
        setup_rows = self._generate_category_rows(stats.get("by_setup", {}))
        
        # Generate recent insights
        recent_insights_rows = self._generate_insights_rows(self.trades)
        
        html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>VEX Performance Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #0a0a0a 0%, #1a1a2e 100%);
            color: #ffffff;
            min-height: 100vh;
            padding: 20px;
        }}
        
        .dashboard {{
            max-width: 1400px;
            margin: 0 auto;
        }}
        
        .header {{
            text-align: center;
            padding: 30px 0;
            border-bottom: 1px solid #333;
            margin-bottom: 30px;
        }}
        
        .header h1 {{
            font-size: 2.5rem;
            background: linear-gradient(90deg, #00ff88, #00aaff);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 10px;
        }}
        
        .header .subtitle {{
            color: #888;
            font-size: 1rem;
        }}
        
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        
        .stat-card {{
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 12px;
            padding: 20px;
            text-align: center;
        }}
        
        .stat-card .value {{
            font-size: 2rem;
            font-weight: bold;
            margin-bottom: 5px;
        }}
        
        .stat-card .label {{
            color: #888;
            font-size: 0.9rem;
            text-transform: uppercase;
        }}
        
        .stat-card.positive .value {{ color: #00ff88; }}
        .stat-card.negative .value {{ color: #ff3366; }}
        .stat-card.neutral .value {{ color: #00aaff; }}
        
        .section {{
            background: rgba(255, 255, 255, 0.03);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 30px;
        }}
        
        .section h2 {{
            font-size: 1.3rem;
            margin-bottom: 20px;
            color: #00aaff;
        }}
        
        .chart-container {{
            position: relative;
            height: 300px;
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
        }}
        
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        }}
        
        th {{
            color: #888;
            font-weight: 500;
            text-transform: uppercase;
            font-size: 0.8rem;
        }}
        
        .win-rate {{
            font-weight: bold;
        }}
        
        .win-rate.high {{ color: #00ff88; }}
        .win-rate.medium {{ color: #ffaa00; }}
        .win-rate.low {{ color: #ff3366; }}
        
        .pnl.positive {{ color: #00ff88; }}
        .pnl.negative {{ color: #ff3366; }}
        
        .calendar {{
            display: grid;
            grid-template-columns: repeat(7, 1fr);
            gap: 5px;
        }}
        
        .calendar-day {{
            aspect-ratio: 1;
            display: flex;
            align-items: center;
            justify-content: center;
            border-radius: 6px;
            font-size: 0.8rem;
            background: rgba(255, 255, 255, 0.05);
        }}
        
        .calendar-day.win {{ background: rgba(0, 255, 136, 0.3); }}
        .calendar-day.loss {{ background: rgba(255, 51, 102, 0.3); }}
        .calendar-day.neutral {{ background: rgba(255, 255, 255, 0.05); }}
        
        .calendar-header {{
            font-weight: bold;
            color: #888;
        }}
        
        .grid-2 {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
            gap: 20px;
        }}
        
        .milestones {{
            list-style: none;
        }}
        
        .milestones li {{
            padding: 10px 0;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        }}
        
        .milestones li:last-child {{
            border-bottom: none;
        }}
        
        .badge {{
            display: inline-block;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 0.8rem;
            margin-right: 10px;
        }}
        
        .badge.achieved {{ background: #00ff88; color: #000; }}
        .badge.progress {{ background: #ffaa00; color: #000; }}
        
        .footer {{
            text-align: center;
            padding: 20px;
            color: #666;
            font-size: 0.9rem;
        }}
    </style>
</head>
<body>
    <div class="dashboard">
        <div class="header">
            <h1>📊 VEX Performance Dashboard</h1>
            <p class="subtitle">Last updated: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}</p>
        </div>
        
        <!-- Key Stats -->
        <div class="stats-grid">
            <div class="stat-card {'positive' if stats['total_pnl'] >= 0 else 'negative'}">
                <div class="value">${stats['total_pnl']:,.2f}</div>
                <div class="label">Total P&L</div>
            </div>
            <div class="stat-card neutral">
                <div class="value">{stats['win_rate']}%</div>
                <div class="label">Win Rate</div>
            </div>
            <div class="stat-card neutral">
                <div class="value">{stats['total_trades']}</div>
                <div class="label">Total Trades</div>
            </div>
            <div class="stat-card {'positive' if stats['profit_factor'] >= 1.5 else 'negative' if stats['profit_factor'] < 1 else 'neutral'}">
                <div class="value">{stats['profit_factor']}</div>
                <div class="label">Profit Factor</div>
            </div>
            <div class="stat-card positive">
                <div class="value">${stats['avg_win']}</div>
                <div class="label">Avg Win</div>
            </div>
            <div class="stat-card negative">
                <div class="value">${stats['avg_loss']}</div>
                <div class="label">Avg Loss</div>
            </div>
            <div class="stat-card {'positive' if stats['expectancy'] > 0 else 'negative'}">
                <div class="value">${stats['expectancy']}</div>
                <div class="label">Expectancy</div>
            </div>
            <div class="stat-card neutral">
                <div class="value">{stats['wins']}/{stats['losses']}</div>
                <div class="label">Wins/Losses</div>
            </div>
        </div>
        
        <!-- Equity Curve -->
        <div class="section">
            <h2>📈 Equity Curve</h2>
            <div class="chart-container">
                <canvas id="equityChart"></canvas>
            </div>
        </div>
        
        <!-- Performance by Category -->
        <div class="grid-2">
            <div class="section">
                <h2>💱 By Pair</h2>
                <table>
                    <tr><th>Pair</th><th>Win Rate</th><th>W/L</th><th>P&L</th></tr>
                    {pair_rows}
                </table>
            </div>
            
            <div class="section">
                <h2>⏰ By Session</h2>
                <table>
                    <tr><th>Session</th><th>Win Rate</th><th>W/L</th><th>P&L</th></tr>
                    {session_rows}
                </table>
            </div>
            
            <div class="section">
                <h2>📅 By Day</h2>
                <table>
                    <tr><th>Day</th><th>Win Rate</th><th>W/L</th><th>P&L</th></tr>
                    {day_rows}
                </table>
            </div>
            
            <div class="section">
                <h2>⭐ By Setup Grade</h2>
                <table>
                    <tr><th>Grade</th><th>Win Rate</th><th>W/L</th><th>P&L</th></tr>
                    {setup_rows}
                </table>
            </div>
        </div>
        
        <!-- Calendar Heatmap -->
        <div class="section">
            <h2>📆 Trading Calendar</h2>
            {calendar_html}
        </div>

        <!-- Recent Trade Insights -->
        <div class="section">
            <h2>🧠 Recent AI Insights</h2>
            <table>
                <tr><th>Date</th><th>Pair</th><th>Result</th><th>AI Confluences & Reasoning</th></tr>
                {recent_insights_rows}
            </table>
        </div>
        
        <!-- Streaks & Milestones -->
        <div class="grid-2">
            <div class="section">
                <h2>🔥 Streaks</h2>
                <div class="stats-grid" style="margin-bottom: 0;">
                    <div class="stat-card positive">
                        <div class="value">{stats['streaks']['current_win']}</div>
                        <div class="label">Current Win Streak</div>
                    </div>
                    <div class="stat-card negative">
                        <div class="value">{stats['streaks']['current_loss']}</div>
                        <div class="label">Current Loss Streak</div>
                    </div>
                    <div class="stat-card positive">
                        <div class="value">{stats['streaks']['max_win']}</div>
                        <div class="label">Max Win Streak</div>
                    </div>
                    <div class="stat-card negative">
                        <div class="value">{stats['streaks']['max_loss']}</div>
                        <div class="label">Max Loss Streak</div>
                    </div>
                </div>
            </div>
            
            <div class="section">
                <h2>🏆 Milestones</h2>
                <ul class="milestones">
                    {self._generate_milestones_html()}
                </ul>
            </div>
        </div>
        
        <div class="footer">
            <p>VEX Trading System • Built with 💚 for ICT traders</p>
        </div>
    </div>
    
    <script>
        // Equity Curve Chart
        const ctx = document.getElementById('equityChart').getContext('2d');
        new Chart(ctx, {{
            type: 'line',
            data: {{
                labels: {equity_labels},
                datasets: [{{
                    label: 'Account Balance',
                    data: {equity_values},
                    borderColor: '#00ff88',
                    backgroundColor: 'rgba(0, 255, 136, 0.1)',
                    fill: true,
                    tension: 0.3,
                    pointRadius: 0
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    legend: {{ display: false }}
                }},
                scales: {{
                    x: {{
                        grid: {{ color: 'rgba(255, 255, 255, 0.1)' }},
                        ticks: {{ color: '#888' }}
                    }},
                    y: {{
                        grid: {{ color: 'rgba(255, 255, 255, 0.1)' }},
                        ticks: {{ 
                            color: '#888',
                            callback: function(value) {{ return '$' + value.toLocaleString(); }}
                        }}
                    }}
                }}
            }}
        }});
    </script>
</body>
</html>'''
        
        return html
    
    def _generate_category_rows(self, data: Dict) -> str:
        """Generate table rows for category data."""
        rows = []
        
        # Sort by win rate
        sorted_data = sorted(data.items(), key=lambda x: x[1].get("win_rate", 0), reverse=True)
        
        for name, stats in sorted_data:
            if name == "UNKNOWN" or not name:
                continue
                
            win_rate = stats.get("win_rate", 0)
            wins = stats.get("wins", 0)
            losses = stats.get("losses", 0)
            pnl = stats.get("pnl", 0)
            
            wr_class = "high" if win_rate >= 60 else "medium" if win_rate >= 50 else "low"
            pnl_class = "positive" if pnl >= 0 else "negative"
            
            rows.append(f'''<tr>
                <td>{name}</td>
                <td class="win-rate {wr_class}">{win_rate}%</td>
                <td>{wins}/{losses}</td>
                <td class="pnl {pnl_class}">${pnl:,.2f}</td>
            </tr>''')
        
        return "\n".join(rows) if rows else "<tr><td colspan='4'>No data yet</td></tr>"
    
    def _generate_insights_rows(self, trades: List[Dict]) -> str:
        """Generate rows for recent AI insights."""
        if not trades:
            return "<tr><td colspan='4'>No trades recorded yet.</td></tr>"
            
        # Sort by date descending
        sorted_trades = sorted(trades, key=lambda x: x.get("created_at", ""), reverse=True)
        recent = sorted_trades[:5]
        
        rows = []
        for trade in recent:
            # Extract basic info
            created = trade.get("created_at", "")
            try:
                dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
                date_str = dt.strftime("%Y-%m-%d %H:%M")
            except:
                date_str = "Unknown"
                
            pair = trade.get("pre_trade", {}).get("pair", "UNKNOWN")
            result = trade.get("result", "OPEN")
            
            # Extract AI reasoning
            # Check various locations for reasoning data
            confluences = trade.get("confluences", [])
            if not confluences and "pre_trade" in trade:
                confluences = trade["pre_trade"].get("confluences", [])
                
            # Formatting result
            res_class = "neutral"
            if result == "WIN":
                res_class = "positive"
            elif result == "LOSS":
                res_class = "negative"
                
            # Format confluences
            if confluences:
                reasoning_html = "<ul style='padding-left: 20px; font-size: 0.9rem; color: #ccc;'>"
                for c in confluences[:3]: # Show top 3
                    reasoning_html += f"<li>{c}</li>"
                if len(confluences) > 3:
                     reasoning_html += f"<li>... and {len(confluences)-3} more</li>"
                reasoning_html += "</ul>"
            else:
                reasoning_html = "<i>No reasoning logged</i>"

            rows.append(f'''<tr>
                <td style="white-space: nowrap;">{date_str}</td>
                <td>{pair}</td>
                <td class="pnl {res_class}">{result}</td>
                <td>{reasoning_html}</td>
            </tr>''')
            
        return "\n".join(rows)

    
    def _generate_calendar_html(self, calendar: Dict) -> str:
        """Generate calendar heatmap HTML."""
        if not calendar:
            return "<p>No trading data yet</p>"
        
        # Get current month
        now = datetime.now()
        first_day = now.replace(day=1)
        
        # Days of week header
        days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        html = '<div class="calendar">'
        
        for day in days:
            html += f'<div class="calendar-day calendar-header">{day}</div>'
        
        # Add empty cells for days before first of month
        first_weekday = first_day.weekday()
        for _ in range(first_weekday):
            html += '<div class="calendar-day"></div>'
        
        # Add days of month
        days_in_month = 31  # Simplified
        for day in range(1, days_in_month + 1):
            try:
                date_str = now.replace(day=day).strftime("%Y-%m-%d")
                day_data = calendar.get(date_str, {})
                result = day_data.get("result", "neutral")
                pnl = day_data.get("pnl", 0)
                trades = day_data.get("trades", 0)
                
                if result == "win":
                    day_class = "win"
                elif result == "loss":
                    day_class = "loss"
                else:
                    day_class = "neutral"
                
                title = f"{trades} trades, ${pnl:.2f}" if trades > 0 else "No trades"
                html += f'<div class="calendar-day {day_class}" title="{title}">{day}</div>'
            except:
                break
        
        html += '</div>'
        return html
    
    def _generate_milestones_html(self) -> str:
        """Generate milestones list HTML."""
        achieved = self.milestones.get("achieved", [])
        in_progress = self.milestones.get("in_progress", [])
        
        html = []
        
        for m in achieved[-5:]:
            html.append(f'''<li>
                <span class="badge achieved">✓</span>
                {m.get('milestone', 'Unknown')} - {m.get('date', '')}
            </li>''')
        
        for m in in_progress[:3]:
            progress = m.get("progress", 0)
            target = m.get("target", 1)
            pct = int(progress / target * 100) if target > 0 else 0
            html.append(f'''<li>
                <span class="badge progress">{pct}%</span>
                {m.get('milestone', 'Unknown')}
            </li>''')
        
        return "\n".join(html) if html else "<li>No milestones yet</li>"
    
    def generate_and_open(self) -> str:
        """Generate dashboard and open in browser."""
        print("\n  📊 Calculating statistics...")
        stats = self.calculate_stats()
        
        print("  🎨 Generating dashboard...")
        html = self.generate_html(stats)
        
        # Save to file
        DASHBOARD_DIR.mkdir(parents=True, exist_ok=True)
        filepath = DASHBOARD_DIR / "dashboard.html"
        
        with open(filepath, "w") as f:
            f.write(html)
        
        print(f"  ✅ Dashboard saved: {filepath}")
        
        # Open in browser
        print("  🌐 Opening in browser...")
        webbrowser.open(f"file://{filepath}")
        
        return str(filepath)
    
    def print_summary(self):
        """Print quick stats summary to terminal."""
        stats = self.calculate_stats()
        
        print("\n" + "═" * 60)
        print("  PERFORMANCE SUMMARY")
        print("═" * 60)
        
        print(f"\n  📊 OVERALL:")
        print(f"     Total Trades: {stats['total_trades']}")
        print(f"     Win Rate: {stats['win_rate']}%")
        print(f"     Total P&L: ${stats['total_pnl']:,.2f}")
        print(f"     Profit Factor: {stats['profit_factor']}")
        print(f"     Expectancy: ${stats['expectancy']} per trade")
        
        print(f"\n  💰 WINS & LOSSES:")
        print(f"     Wins: {stats['wins']} | Losses: {stats['losses']} | BE: {stats['breakeven']}")
        print(f"     Avg Win: ${stats['avg_win']} | Avg Loss: ${stats['avg_loss']}")
        print(f"     Largest Win: ${stats['largest_win']} | Largest Loss: ${stats['largest_loss']}")
        
        print(f"\n  🔥 STREAKS:")
        print(f"     Current: {'🟢 ' + str(stats['streaks']['current_win']) + ' wins' if stats['streaks']['current_win'] > 0 else '🔴 ' + str(stats['streaks']['current_loss']) + ' losses'}")
        print(f"     Max Win Streak: {stats['streaks']['max_win']}")
        print(f"     Max Loss Streak: {stats['streaks']['max_loss']}")
        
        # Best performers
        if stats['by_pair']:
            best_pair = max(stats['by_pair'].items(), key=lambda x: x[1].get('win_rate', 0))
            print(f"\n  🏆 BEST PAIR: {best_pair[0]} ({best_pair[1]['win_rate']}% win rate)")
        
        if stats['by_session']:
            best_session = max(stats['by_session'].items(), key=lambda x: x[1].get('win_rate', 0))
            print(f"  🏆 BEST SESSION: {best_session[0]} ({best_session[1]['win_rate']}% win rate)")
        
        print("\n" + "═" * 60)


def main():
    """CLI entry point."""
    import sys
    
    dashboard = PerformanceDashboard()
    
    if len(sys.argv) > 1 and sys.argv[1] == "open":
        dashboard.generate_and_open()
    else:
        dashboard.print_summary()
        print("\n  💡 Run 'python vex.py dashboard open' to view full HTML dashboard")


if __name__ == "__main__":
    main()
