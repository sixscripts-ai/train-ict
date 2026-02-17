"""Backtesting Engine

Core backtesting functionality for ICT trading strategies.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Callable
import pandas as pd
import numpy as np
from loguru import logger

from ict_agent.engine.signal_generator import TradeSignal, SignalType
from ict_agent.engine.agent import ICTTradingAgent, AgentConfig
from ict_agent.backtest.metrics import BacktestMetrics, Trade


@dataclass
class BacktestConfig:
    """Configuration for backtesting"""
    initial_capital: float = 10000.0
    risk_per_trade: float = 0.01
    commission_pips: float = 0.5
    slippage_pips: float = 0.5
    pip_size: float = 0.0001
    pip_value: float = 10.0
    max_trades_per_day: int = 3
    require_confirmation_candle: bool = True


@dataclass
class BacktestState:
    """Current state during backtest"""
    capital: float
    equity: float
    open_trades: list = field(default_factory=list)
    closed_trades: list = field(default_factory=list)
    signals: list = field(default_factory=list)
    daily_trade_count: dict = field(default_factory=dict)
    current_date: Optional[datetime] = None


class BacktestEngine:
    """
    Backtesting engine for ICT trading strategies.
    
    Features:
    - Realistic execution simulation (slippage, commission)
    - Position sizing based on risk
    - Multi-target management
    - Performance metrics calculation
    """
    
    def __init__(
        self,
        config: Optional[BacktestConfig] = None,
        agent_config: Optional[AgentConfig] = None,
    ):
        self.config = config or BacktestConfig()
        self.agent_config = agent_config or AgentConfig()
        self.agent = ICTTradingAgent(config=self.agent_config)
        
        self.state = BacktestState(
            capital=self.config.initial_capital,
            equity=self.config.initial_capital,
        )
    
    def run(
        self,
        symbol: str,
        htf_data: pd.DataFrame,
        itf_data: pd.DataFrame,
        ltf_data: pd.DataFrame,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> BacktestMetrics:
        """
        Run backtest on historical data.
        
        Args:
            symbol: Trading symbol
            htf_data: Higher timeframe data (Daily/4H)
            itf_data: Intermediate timeframe data (1H)
            ltf_data: Lower timeframe data (15M/5M) - main trading timeframe
            start_date: Backtest start date
            end_date: Backtest end date
        
        Returns:
            BacktestMetrics with full performance analysis
        """
        self._reset_state()
        
        if start_date:
            ltf_data = ltf_data[ltf_data.index >= start_date]
        if end_date:
            ltf_data = ltf_data[ltf_data.index <= end_date]
        
        lookback = 100
        equity_curve = []
        
        logger.info(f"Starting backtest: {symbol} | {len(ltf_data)} bars")

        if ltf_data.empty:
            logger.warning(f"No LTF data available for backtest: {symbol}")
            return self._calculate_metrics(equity_curve, symbol)
        
        for i in range(lookback, len(ltf_data)):
            current_bar = ltf_data.iloc[i]
            current_time = ltf_data.index[i]
            current_date = current_time.date()
            
            if self.state.current_date != current_date:
                self.state.current_date = current_date
                self.state.daily_trade_count[current_date] = 0
            
            self._check_exits(current_bar, current_time)
            
            self._update_equity(current_bar)
            equity_curve.append({
                "timestamp": current_time,
                "equity": self.state.equity,
                "open_trades": len(self.state.open_trades),
            })
            
            if self.state.daily_trade_count.get(current_date, 0) >= self.config.max_trades_per_day:
                continue
            
            ltf_window = ltf_data.iloc[i - lookback : i + 1]
            itf_window = itf_data[itf_data.index <= current_time].tail(200)
            htf_window = htf_data[htf_data.index <= current_time].tail(100)
            
            if len(htf_window) < 20 or len(itf_window) < 20:
                continue
            
            signal = self.agent.analyze(symbol, htf_window, itf_window, ltf_window)
            
            if signal:
                self.state.signals.append(signal)
                self._execute_signal(signal, current_bar, current_time)
        
        self._close_all_trades(ltf_data.iloc[-1], ltf_data.index[-1])
        
        return self._calculate_metrics(equity_curve, symbol)
    
    def _reset_state(self) -> None:
        """Reset backtest state"""
        self.state = BacktestState(
            capital=self.config.initial_capital,
            equity=self.config.initial_capital,
        )
        self.agent = ICTTradingAgent(config=self.agent_config)
    
    def _execute_signal(
        self,
        signal: TradeSignal,
        current_bar: pd.Series,
        current_time: datetime,
    ) -> None:
        """Execute a trade signal"""
        entry_price = signal.entry_price
        
        if signal.signal_type == SignalType.LONG:
            entry_price += self.config.slippage_pips * self.config.pip_size
        else:
            entry_price -= self.config.slippage_pips * self.config.pip_size
        
        risk_amount = self.state.capital * self.config.risk_per_trade
        pip_risk = abs(entry_price - signal.stop_loss) / self.config.pip_size
        
        if pip_risk == 0:
            return
        
        position_size = risk_amount / (pip_risk * self.config.pip_value)
        position_size = round(position_size, 2)
        
        if position_size < 0.01:
            return
        
        trade = {
            "id": len(self.state.closed_trades) + len(self.state.open_trades) + 1,
            "symbol": signal.symbol,
            "direction": signal.signal_type,
            "entry_time": current_time,
            "entry_price": entry_price,
            "stop_loss": signal.stop_loss,
            "target_1": signal.target_1,
            "target_2": signal.target_2,
            "position_size": position_size,
            "model": signal.model.value,
            "confluences": signal.confluences.count,
            "confidence": signal.confidence,
            "t1_hit": False,
            "pnl": 0.0,
        }
        
        self.state.open_trades.append(trade)
        self.state.daily_trade_count[self.state.current_date] = \
            self.state.daily_trade_count.get(self.state.current_date, 0) + 1
        
        logger.debug(
            f"ENTRY: {signal.symbol} {signal.signal_type.value} @ {entry_price:.5f} | "
            f"Size: {position_size} | Model: {signal.model.value}"
        )
    
    def _check_exits(self, current_bar: pd.Series, current_time: datetime) -> None:
        """Check and execute exits for open trades"""
        trades_to_close = []
        
        for trade in self.state.open_trades:
            exit_price = None
            exit_reason = None
            
            if trade["direction"] == SignalType.LONG:
                if current_bar["low"] <= trade["stop_loss"]:
                    exit_price = trade["stop_loss"] - (self.config.slippage_pips * self.config.pip_size)
                    exit_reason = "stop_loss"
                
                elif not trade["t1_hit"] and current_bar["high"] >= trade["target_1"]:
                    trade["t1_hit"] = True
                    partial_pnl = self._calculate_pnl(
                        trade["entry_price"],
                        trade["target_1"],
                        trade["position_size"] * 0.5,
                        trade["direction"],
                    )
                    trade["pnl"] += partial_pnl
                    trade["position_size"] *= 0.5
                    trade["stop_loss"] = trade["entry_price"]
                    logger.debug(f"T1 HIT: Trade {trade['id']} | Partial: {partial_pnl:.2f}")
                
                elif trade["t1_hit"] and trade["target_2"] and current_bar["high"] >= trade["target_2"]:
                    exit_price = trade["target_2"]
                    exit_reason = "target_2"
            
            else:
                if current_bar["high"] >= trade["stop_loss"]:
                    exit_price = trade["stop_loss"] + (self.config.slippage_pips * self.config.pip_size)
                    exit_reason = "stop_loss"
                
                elif not trade["t1_hit"] and current_bar["low"] <= trade["target_1"]:
                    trade["t1_hit"] = True
                    partial_pnl = self._calculate_pnl(
                        trade["entry_price"],
                        trade["target_1"],
                        trade["position_size"] * 0.5,
                        trade["direction"],
                    )
                    trade["pnl"] += partial_pnl
                    trade["position_size"] *= 0.5
                    trade["stop_loss"] = trade["entry_price"]
                    logger.debug(f"T1 HIT: Trade {trade['id']} | Partial: {partial_pnl:.2f}")
                
                elif trade["t1_hit"] and trade["target_2"] and current_bar["low"] <= trade["target_2"]:
                    exit_price = trade["target_2"]
                    exit_reason = "target_2"
            
            if exit_price:
                final_pnl = self._calculate_pnl(
                    trade["entry_price"] if not trade["t1_hit"] else trade["stop_loss"],
                    exit_price,
                    trade["position_size"],
                    trade["direction"],
                )
                trade["pnl"] += final_pnl
                trade["exit_time"] = current_time
                trade["exit_price"] = exit_price
                trade["exit_reason"] = exit_reason
                
                self.state.capital += trade["pnl"]
                trades_to_close.append(trade)
                
                logger.debug(
                    f"EXIT: Trade {trade['id']} | {exit_reason} @ {exit_price:.5f} | "
                    f"PnL: {trade['pnl']:.2f}"
                )
        
        for trade in trades_to_close:
            self.state.open_trades.remove(trade)
            self.state.closed_trades.append(trade)
    
    def _calculate_pnl(
        self,
        entry: float,
        exit: float,
        size: float,
        direction: SignalType,
    ) -> float:
        """Calculate P&L for a trade"""
        if direction == SignalType.LONG:
            pips = (exit - entry) / self.config.pip_size
        else:
            pips = (entry - exit) / self.config.pip_size
        
        pips -= self.config.commission_pips
        
        return pips * size * self.config.pip_value
    
    def _update_equity(self, current_bar: pd.Series) -> None:
        """Update equity based on open positions"""
        unrealized = 0.0
        
        for trade in self.state.open_trades:
            current_price = current_bar["close"]
            
            if trade["direction"] == SignalType.LONG:
                pips = (current_price - trade["entry_price"]) / self.config.pip_size
            else:
                pips = (trade["entry_price"] - current_price) / self.config.pip_size
            
            unrealized += pips * trade["position_size"] * self.config.pip_value
        
        self.state.equity = self.state.capital + unrealized
    
    def _close_all_trades(self, final_bar: pd.Series, final_time: datetime) -> None:
        """Close all remaining open trades at end of backtest"""
        for trade in self.state.open_trades[:]:
            exit_price = final_bar["close"]
            
            final_pnl = self._calculate_pnl(
                trade["entry_price"],
                exit_price,
                trade["position_size"],
                trade["direction"],
            )
            trade["pnl"] = final_pnl
            trade["exit_time"] = final_time
            trade["exit_price"] = exit_price
            trade["exit_reason"] = "end_of_test"
            
            self.state.capital += trade["pnl"]
            self.state.open_trades.remove(trade)
            self.state.closed_trades.append(trade)
    
    def _calculate_metrics(
        self,
        equity_curve: list[dict],
        symbol: str,
    ) -> BacktestMetrics:
        """Calculate comprehensive backtest metrics"""
        trades = [
            Trade(
                id=t["id"],
                symbol=t["symbol"],
                direction=t["direction"].value,
                entry_time=t["entry_time"],
                exit_time=t.get("exit_time"),
                entry_price=t["entry_price"],
                exit_price=t.get("exit_price", 0),
                position_size=t.get("position_size", 0),
                pnl=t["pnl"],
                exit_reason=t.get("exit_reason", ""),
                model=t["model"],
                confluences=t["confluences"],
            )
            for t in self.state.closed_trades
        ]
        
        equity_df = pd.DataFrame(equity_curve)
        if not equity_df.empty:
            equity_df.set_index("timestamp", inplace=True)
        
        return BacktestMetrics(
            symbol=symbol,
            start_date=equity_df.index[0] if not equity_df.empty else None,
            end_date=equity_df.index[-1] if not equity_df.empty else None,
            initial_capital=self.config.initial_capital,
            final_capital=self.state.capital,
            trades=trades,
            equity_curve=equity_df,
            signals=self.state.signals,
        )
