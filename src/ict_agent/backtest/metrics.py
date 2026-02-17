"""Backtest Metrics and Analysis

Comprehensive performance metrics for ICT strategy backtests.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
import pandas as pd
import numpy as np


@dataclass
class Trade:
    """Individual trade record"""
    id: int
    symbol: str
    direction: str
    entry_time: datetime
    exit_time: Optional[datetime]
    entry_price: float
    exit_price: float
    position_size: float
    pnl: float
    exit_reason: str
    model: str
    confluences: int


@dataclass
class BacktestMetrics:
    """Comprehensive backtest performance metrics"""
    symbol: str
    start_date: Optional[datetime]
    end_date: Optional[datetime]
    initial_capital: float
    final_capital: float
    trades: list[Trade]
    equity_curve: pd.DataFrame
    signals: list
    
    def __post_init__(self):
        self._calculate_metrics()
    
    def _calculate_metrics(self) -> None:
        """Calculate all performance metrics"""
        if not self.trades:
            self._set_empty_metrics()
            return
        
        pnls = [t.pnl for t in self.trades]
        wins = [p for p in pnls if p > 0]
        losses = [p for p in pnls if p <= 0]
        
        self.total_trades = len(self.trades)
        self.winning_trades = len(wins)
        self.losing_trades = len(losses)
        self.win_rate = self.winning_trades / self.total_trades if self.total_trades > 0 else 0
        
        self.total_pnl = sum(pnls)
        self.gross_profit = sum(wins) if wins else 0
        self.gross_loss = abs(sum(losses)) if losses else 0
        self.profit_factor = self.gross_profit / self.gross_loss if self.gross_loss > 0 else float("inf")
        
        self.avg_win = np.mean(wins) if wins else 0
        self.avg_loss = abs(np.mean(losses)) if losses else 0
        self.avg_trade = np.mean(pnls) if pnls else 0
        self.largest_win = max(wins) if wins else 0
        self.largest_loss = min(losses) if losses else 0
        
        self.expectancy = (self.win_rate * self.avg_win) - ((1 - self.win_rate) * self.avg_loss)
        
        self.return_pct = ((self.final_capital - self.initial_capital) / self.initial_capital) * 100
        
        if not self.equity_curve.empty and "equity" in self.equity_curve.columns:
            self.max_drawdown, self.max_drawdown_pct = self._calculate_drawdown()
        else:
            self.max_drawdown = 0
            self.max_drawdown_pct = 0
        
        self.sharpe_ratio = self._calculate_sharpe()
        self.sortino_ratio = self._calculate_sortino()
        
        self.model_performance = self._analyze_by_model()
        self.confluence_performance = self._analyze_by_confluence()
        
        self.consecutive_wins, self.consecutive_losses = self._calculate_streaks()
    
    def _set_empty_metrics(self) -> None:
        """Set default values for empty backtest"""
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0
        self.win_rate = 0
        self.total_pnl = 0
        self.gross_profit = 0
        self.gross_loss = 0
        self.profit_factor = 0
        self.avg_win = 0
        self.avg_loss = 0
        self.avg_trade = 0
        self.largest_win = 0
        self.largest_loss = 0
        self.expectancy = 0
        self.return_pct = 0
        self.max_drawdown = 0
        self.max_drawdown_pct = 0
        self.sharpe_ratio = 0
        self.sortino_ratio = 0
        self.model_performance = {}
        self.confluence_performance = {}
        self.consecutive_wins = 0
        self.consecutive_losses = 0
    
    def _calculate_drawdown(self) -> tuple[float, float]:
        """Calculate maximum drawdown"""
        equity = self.equity_curve["equity"]
        peak = equity.expanding().max()
        drawdown = equity - peak
        max_dd = drawdown.min()
        max_dd_pct = (max_dd / peak[drawdown.idxmin()]) * 100 if max_dd < 0 else 0
        return abs(max_dd), abs(max_dd_pct)
    
    def _calculate_sharpe(self, risk_free_rate: float = 0.02) -> float:
        """Calculate Sharpe Ratio"""
        if not self.trades:
            return 0
        
        returns = pd.Series([t.pnl / self.initial_capital for t in self.trades])
        
        if returns.std() == 0:
            return 0
        
        excess_returns = returns.mean() - (risk_free_rate / 252)
        return (excess_returns / returns.std()) * np.sqrt(252)
    
    def _calculate_sortino(self, risk_free_rate: float = 0.02) -> float:
        """Calculate Sortino Ratio (only considers downside volatility)"""
        if not self.trades:
            return 0
        
        returns = pd.Series([t.pnl / self.initial_capital for t in self.trades])
        negative_returns = returns[returns < 0]
        
        if len(negative_returns) == 0 or negative_returns.std() == 0:
            return float("inf") if returns.mean() > 0 else 0
        
        excess_returns = returns.mean() - (risk_free_rate / 252)
        return (excess_returns / negative_returns.std()) * np.sqrt(252)
    
    def _analyze_by_model(self) -> dict:
        """Analyze performance by ICT model"""
        model_stats = {}
        
        models = set(t.model for t in self.trades)
        
        for model in models:
            model_trades = [t for t in self.trades if t.model == model]
            pnls = [t.pnl for t in model_trades]
            wins = [p for p in pnls if p > 0]
            
            model_stats[model] = {
                "trades": len(model_trades),
                "win_rate": len(wins) / len(model_trades) if model_trades else 0,
                "total_pnl": sum(pnls),
                "avg_pnl": np.mean(pnls) if pnls else 0,
            }
        
        return model_stats
    
    def _analyze_by_confluence(self) -> dict:
        """Analyze performance by confluence count"""
        conf_stats = {}
        
        for conf_count in range(1, 12):
            conf_trades = [t for t in self.trades if t.confluences == conf_count]
            if not conf_trades:
                continue
            
            pnls = [t.pnl for t in conf_trades]
            wins = [p for p in pnls if p > 0]
            
            conf_stats[conf_count] = {
                "trades": len(conf_trades),
                "win_rate": len(wins) / len(conf_trades),
                "total_pnl": sum(pnls),
                "avg_pnl": np.mean(pnls),
            }
        
        return conf_stats
    
    def _calculate_streaks(self) -> tuple[int, int]:
        """Calculate maximum consecutive wins and losses"""
        if not self.trades:
            return 0, 0
        
        max_wins = 0
        max_losses = 0
        current_wins = 0
        current_losses = 0
        
        for trade in self.trades:
            if trade.pnl > 0:
                current_wins += 1
                current_losses = 0
                max_wins = max(max_wins, current_wins)
            else:
                current_losses += 1
                current_wins = 0
                max_losses = max(max_losses, current_losses)
        
        return max_wins, max_losses
    
    def summary(self) -> str:
        """Generate text summary of backtest results"""
        lines = [
            "=" * 60,
            f"BACKTEST RESULTS: {self.symbol}",
            "=" * 60,
            f"Period: {self.start_date} to {self.end_date}",
            "",
            "--- CAPITAL ---",
            f"Initial Capital: ${self.initial_capital:,.2f}",
            f"Final Capital:   ${self.final_capital:,.2f}",
            f"Total Return:    {self.return_pct:+.2f}%",
            f"Total P&L:       ${self.total_pnl:+,.2f}",
            "",
            "--- TRADES ---",
            f"Total Trades:    {self.total_trades}",
            f"Winning Trades:  {self.winning_trades} ({self.win_rate*100:.1f}%)",
            f"Losing Trades:   {self.losing_trades}",
            f"Avg Trade P&L:   ${self.avg_trade:+,.2f}",
            "",
            "--- RISK METRICS ---",
            f"Profit Factor:   {self.profit_factor:.2f}",
            f"Expectancy:      ${self.expectancy:+,.2f}",
            f"Max Drawdown:    ${self.max_drawdown:,.2f} ({self.max_drawdown_pct:.1f}%)",
            f"Sharpe Ratio:    {self.sharpe_ratio:.2f}",
            f"Sortino Ratio:   {self.sortino_ratio:.2f}",
            "",
            "--- PERFORMANCE BY MODEL ---",
        ]
        
        for model, stats in self.model_performance.items():
            lines.append(
                f"  {model}: {stats['trades']} trades, "
                f"{stats['win_rate']*100:.1f}% WR, "
                f"${stats['total_pnl']:+,.2f}"
            )
        
        lines.extend([
            "",
            "--- STREAKS ---",
            f"Max Consecutive Wins:   {self.consecutive_wins}",
            f"Max Consecutive Losses: {self.consecutive_losses}",
            "=" * 60,
        ])
        
        return "\n".join(lines)
    
    def to_dict(self) -> dict:
        """Export metrics as dictionary"""
        return {
            "symbol": self.symbol,
            "start_date": str(self.start_date),
            "end_date": str(self.end_date),
            "initial_capital": self.initial_capital,
            "final_capital": self.final_capital,
            "total_pnl": self.total_pnl,
            "return_pct": self.return_pct,
            "total_trades": self.total_trades,
            "winning_trades": self.winning_trades,
            "losing_trades": self.losing_trades,
            "win_rate": self.win_rate,
            "profit_factor": self.profit_factor,
            "expectancy": self.expectancy,
            "avg_trade": self.avg_trade,
            "avg_win": self.avg_win,
            "avg_loss": self.avg_loss,
            "largest_win": self.largest_win,
            "largest_loss": self.largest_loss,
            "max_drawdown": self.max_drawdown,
            "max_drawdown_pct": self.max_drawdown_pct,
            "sharpe_ratio": self.sharpe_ratio,
            "sortino_ratio": self.sortino_ratio,
            "consecutive_wins": self.consecutive_wins,
            "consecutive_losses": self.consecutive_losses,
            "model_performance": self.model_performance,
            "confluence_performance": self.confluence_performance,
        }
