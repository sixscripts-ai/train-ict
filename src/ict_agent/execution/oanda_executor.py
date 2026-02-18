"""
OANDA Trade Executor

Handles all trade execution via OANDA REST API:
- Place market orders
- Place limit/stop orders
- Set stop-loss and take-profit
- Modify existing orders
- Close positions
- Get account info and positions

This is the execution layer for the autonomous trader.
"""

import os
import json
import requests
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Tuple
from enum import Enum
from datetime import datetime
from zoneinfo import ZoneInfo


NY_TZ = ZoneInfo("America/New_York")


class OrderType(Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"
    MARKET_IF_TOUCHED = "MARKET_IF_TOUCHED"


class OrderSide(Enum):
    BUY = "BUY"
    SELL = "SELL"


class TimeInForce(Enum):
    GTC = "GTC"  # Good Till Cancelled
    GTD = "GTD"  # Good Till Date
    GFD = "GFD"  # Good For Day
    FOK = "FOK"  # Fill Or Kill
    IOC = "IOC"  # Immediate Or Cancel


@dataclass
class OrderResult:
    """Result of an order attempt"""
    success: bool
    order_id: Optional[str] = None
    trade_id: Optional[str] = None
    fill_price: Optional[float] = None
    units: Optional[int] = None
    message: str = ""
    raw_response: Optional[dict] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(NY_TZ))


@dataclass
class Position:
    """Current position info"""
    instrument: str
    units: int  # Positive = long, Negative = short
    average_price: float
    unrealized_pnl: float
    margin_used: float
    
    @property
    def side(self) -> str:
        return "LONG" if self.units > 0 else "SHORT"
    
    @property
    def size(self) -> int:
        return abs(self.units)


@dataclass
class AccountInfo:
    """Account summary"""
    account_id: str
    balance: float
    unrealized_pnl: float
    nav: float  # Net Asset Value
    margin_used: float
    margin_available: float
    open_trade_count: int
    open_position_count: int
    currency: str


class OANDAExecutor:
    """
    OANDA Trade Execution Engine
    
    Handles all order placement and position management via OANDA REST API.
    """
    
    def __init__(
        self,
        api_key: str = None,
        account_id: str = None,
        environment: str = "practice"  # "practice" or "live"
    ):
        """
        Initialize executor.
        
        Args:
            api_key: OANDA API key (from env if not provided)
            account_id: OANDA account ID (from env if not provided)
            environment: "practice" for demo, "live" for real
        """
        self.api_key = api_key or os.getenv("OANDA_API_KEY")
        self.account_id = account_id or os.getenv("OANDA_ACCOUNT_ID")
        self.environment = environment
        
        if not self.api_key:
            raise ValueError("OANDA API key required. Set OANDA_API_KEY env var.")
        
        # Set base URL based on environment
        if self.environment.lower() == "live":
            self.base_url = "https://api-fxtrade.oanda.com"
        else:
            self.base_url = "https://api-fxpractice.oanda.com"
        
        # Setup session
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept-Datetime-Format": "RFC3339",
        })
        
        # Cache account info
        self._account_info: Optional[AccountInfo] = None
    
    def _get_instrument(self, symbol: str) -> str:
        """Convert symbol format (EURUSD -> EUR_USD)"""
        symbol = symbol.upper().replace("/", "").replace("_", "")
        if len(symbol) == 6:
            return f"{symbol[:3]}_{symbol[3:]}"
        return symbol
    
    # ═══════════════════════════════════════════════════════════════════════════
    # ACCOUNT METHODS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def get_account_info(self, force_refresh: bool = False) -> Optional[AccountInfo]:
        """Get account summary"""
        if self._account_info and not force_refresh:
            return self._account_info
        
        try:
            url = f"{self.base_url}/v3/accounts/{self.account_id}/summary"
            response = self.session.get(url)
            response.raise_for_status()
            
            data = response.json().get("account", {})
            
            self._account_info = AccountInfo(
                account_id=data.get("id", ""),
                balance=float(data.get("balance", 0)),
                unrealized_pnl=float(data.get("unrealizedPL", 0)),
                nav=float(data.get("NAV", 0)),
                margin_used=float(data.get("marginUsed", 0)),
                margin_available=float(data.get("marginAvailable", 0)),
                open_trade_count=int(data.get("openTradeCount", 0)),
                open_position_count=int(data.get("openPositionCount", 0)),
                currency=data.get("currency", "USD"),
            )
            
            return self._account_info
            
        except Exception as e:
            print(f"Error getting account info: {e}")
            return None
    
    def get_balance(self) -> float:
        """Get current account balance"""
        info = self.get_account_info(force_refresh=True)
        return info.balance if info else 0.0
    
    def get_nav(self) -> float:
        """Get Net Asset Value (balance + unrealized P&L)"""
        info = self.get_account_info(force_refresh=True)
        return info.nav if info else 0.0
    
    def get_margin_available(self) -> float:
        """Get available margin"""
        info = self.get_account_info(force_refresh=True)
        return info.margin_available if info else 0.0
    
    # ═══════════════════════════════════════════════════════════════════════════
    # POSITION METHODS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def get_positions(self) -> List[Position]:
        """Get all open positions"""
        try:
            url = f"{self.base_url}/v3/accounts/{self.account_id}/openPositions"
            response = self.session.get(url)
            response.raise_for_status()
            
            positions = []
            for pos in response.json().get("positions", []):
                # Combine long and short
                long_units = int(pos.get("long", {}).get("units", 0))
                short_units = int(pos.get("short", {}).get("units", 0))
                units = long_units + short_units  # short is negative
                
                if units == 0:
                    continue
                
                if units > 0:
                    avg_price = float(pos.get("long", {}).get("averagePrice", 0))
                    unrealized = float(pos.get("long", {}).get("unrealizedPL", 0))
                else:
                    avg_price = float(pos.get("short", {}).get("averagePrice", 0))
                    unrealized = float(pos.get("short", {}).get("unrealizedPL", 0))
                
                positions.append(Position(
                    instrument=pos.get("instrument", ""),
                    units=units,
                    average_price=avg_price,
                    unrealized_pnl=unrealized,
                    margin_used=float(pos.get("marginUsed", 0)),
                ))
            
            return positions
            
        except Exception as e:
            print(f"Error getting positions: {e}")
            return []
    
    def get_position(self, symbol: str) -> Optional[Position]:
        """Get position for a specific instrument"""
        instrument = self._get_instrument(symbol)
        positions = self.get_positions()
        
        for pos in positions:
            if pos.instrument == instrument:
                return pos
        
        return None
    
    def get_open_trades(self) -> List[dict]:
        """Get all open trades with full details"""
        try:
            url = f"{self.base_url}/v3/accounts/{self.account_id}/openTrades"
            response = self.session.get(url)
            response.raise_for_status()
            
            return response.json().get("trades", [])
            
        except Exception as e:
            print(f"Error getting trades: {e}")
            return []
    
    # ═══════════════════════════════════════════════════════════════════════════
    # ORDER METHODS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def place_market_order(
        self,
        symbol: str,
        units: int,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        trailing_stop_pips: Optional[float] = None,
    ) -> OrderResult:
        """
        Place a market order.
        
        Args:
            symbol: Trading pair (e.g., "EURUSD")
            units: Number of units (positive = buy, negative = sell)
            stop_loss: Stop loss price
            take_profit: Take profit price
            trailing_stop_pips: Trailing stop distance in pips
        
        Returns:
            OrderResult with execution details
        """
        instrument = self._get_instrument(symbol)
        
        order_data = {
            "order": {
                "type": "MARKET",
                "instrument": instrument,
                "units": str(units),
                "timeInForce": "FOK",
                "positionFill": "DEFAULT",
            }
        }
        
        # Add stop loss
        if stop_loss:
            order_data["order"]["stopLossOnFill"] = {
                "price": f"{stop_loss:.5f}"
            }
        
        # Add take profit
        if take_profit:
            order_data["order"]["takeProfitOnFill"] = {
                "price": f"{take_profit:.5f}"
            }
        
        # Add trailing stop
        if trailing_stop_pips:
            order_data["order"]["trailingStopLossOnFill"] = {
                "distance": f"{trailing_stop_pips * 0.0001:.5f}"
            }
        
        return self._execute_order(order_data)
    
    def place_limit_order(
        self,
        symbol: str,
        units: int,
        price: float,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        time_in_force: TimeInForce = TimeInForce.GTC,
    ) -> OrderResult:
        """
        Place a limit order.
        
        Args:
            symbol: Trading pair
            units: Number of units (positive = buy, negative = sell)
            price: Limit price
            stop_loss: Stop loss price
            take_profit: Take profit price
            time_in_force: Order duration
        
        Returns:
            OrderResult
        """
        instrument = self._get_instrument(symbol)
        
        order_data = {
            "order": {
                "type": "LIMIT",
                "instrument": instrument,
                "units": str(units),
                "price": f"{price:.5f}",
                "timeInForce": time_in_force.value,
                "positionFill": "DEFAULT",
            }
        }
        
        if stop_loss:
            order_data["order"]["stopLossOnFill"] = {"price": f"{stop_loss:.5f}"}
        
        if take_profit:
            order_data["order"]["takeProfitOnFill"] = {"price": f"{take_profit:.5f}"}
        
        return self._execute_order(order_data)
    
    def place_stop_order(
        self,
        symbol: str,
        units: int,
        price: float,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        time_in_force: TimeInForce = TimeInForce.GTC,
    ) -> OrderResult:
        """
        Place a stop order (entry on breakout).
        """
        instrument = self._get_instrument(symbol)
        
        order_data = {
            "order": {
                "type": "STOP",
                "instrument": instrument,
                "units": str(units),
                "price": f"{price:.5f}",
                "timeInForce": time_in_force.value,
                "positionFill": "DEFAULT",
            }
        }
        
        if stop_loss:
            order_data["order"]["stopLossOnFill"] = {"price": f"{stop_loss:.5f}"}
        
        if take_profit:
            order_data["order"]["takeProfitOnFill"] = {"price": f"{take_profit:.5f}"}
        
        return self._execute_order(order_data)
    
    def _execute_order(self, order_data: dict) -> OrderResult:
        """Execute an order via API"""
        try:
            url = f"{self.base_url}/v3/accounts/{self.account_id}/orders"
            response = self.session.post(url, json=order_data)
            
            result = response.json()
            
            if response.status_code in [200, 201]:
                # Check for fill
                if "orderFillTransaction" in result:
                    fill = result["orderFillTransaction"]
                    return OrderResult(
                        success=True,
                        order_id=fill.get("orderID"),
                        trade_id=fill.get("tradeOpened", {}).get("tradeID"),
                        fill_price=float(fill.get("price", 0)),
                        units=int(fill.get("units", 0)),
                        message="Order filled",
                        raw_response=result,
                    )
                
                # Pending order created
                elif "orderCreateTransaction" in result:
                    create = result["orderCreateTransaction"]
                    return OrderResult(
                        success=True,
                        order_id=create.get("id"),
                        message="Order created (pending)",
                        raw_response=result,
                    )
                
                return OrderResult(
                    success=True,
                    message="Order processed",
                    raw_response=result,
                )
            
            else:
                error_msg = result.get("errorMessage", str(result))
                return OrderResult(
                    success=False,
                    message=f"Order failed: {error_msg}",
                    raw_response=result,
                )
                
        except Exception as e:
            return OrderResult(
                success=False,
                message=f"Execution error: {str(e)}",
            )
    
    # ═══════════════════════════════════════════════════════════════════════════
    # MODIFY / CLOSE METHODS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def modify_trade_sl_tp(
        self,
        trade_id: str,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
    ) -> OrderResult:
        """Modify stop loss and/or take profit on an existing trade"""
        try:
            url = f"{self.base_url}/v3/accounts/{self.account_id}/trades/{trade_id}/orders"
            
            order_data = {}
            
            if stop_loss:
                order_data["stopLoss"] = {"price": f"{stop_loss:.5f}"}
            
            if take_profit:
                order_data["takeProfit"] = {"price": f"{take_profit:.5f}"}
            
            response = self.session.put(url, json=order_data)
            result = response.json()
            
            if response.status_code == 200:
                return OrderResult(
                    success=True,
                    trade_id=trade_id,
                    message="Trade modified",
                    raw_response=result,
                )
            else:
                return OrderResult(
                    success=False,
                    message=f"Modify failed: {result}",
                    raw_response=result,
                )
                
        except Exception as e:
            return OrderResult(success=False, message=str(e))
    
    def close_trade(self, trade_id: str, units: Optional[int] = None) -> OrderResult:
        """
        Close a trade (fully or partially).
        
        Args:
            trade_id: Trade ID to close
            units: Number of units to close (None = close all)
        """
        try:
            url = f"{self.base_url}/v3/accounts/{self.account_id}/trades/{trade_id}/close"
            
            data = {}
            if units:
                data["units"] = str(abs(units))
            
            response = self.session.put(url, json=data)
            result = response.json()
            
            if response.status_code == 200:
                close_info = result.get("orderFillTransaction", {})
                return OrderResult(
                    success=True,
                    trade_id=trade_id,
                    fill_price=float(close_info.get("price", 0)),
                    units=int(close_info.get("units", 0)),
                    message="Trade closed",
                    raw_response=result,
                )
            else:
                return OrderResult(
                    success=False,
                    message=f"Close failed: {result}",
                    raw_response=result,
                )
                
        except Exception as e:
            return OrderResult(success=False, message=str(e))
    
    def close_position(self, symbol: str) -> OrderResult:
        """Close all of a position for a symbol"""
        instrument = self._get_instrument(symbol)
        
        try:
            url = f"{self.base_url}/v3/accounts/{self.account_id}/positions/{instrument}/close"
            
            # Get current position to know direction
            position = self.get_position(symbol)
            if not position:
                return OrderResult(success=False, message="No position to close")
            
            # Close all units
            if position.units > 0:
                data = {"longUnits": "ALL"}
            else:
                data = {"shortUnits": "ALL"}
            
            response = self.session.put(url, json=data)
            result = response.json()
            
            if response.status_code == 200:
                return OrderResult(
                    success=True,
                    message=f"Position {instrument} closed",
                    raw_response=result,
                )
            else:
                return OrderResult(
                    success=False,
                    message=f"Close failed: {result}",
                    raw_response=result,
                )
                
        except Exception as e:
            return OrderResult(success=False, message=str(e))
    
    def cancel_order(self, order_id: str) -> OrderResult:
        """Cancel a pending order"""
        try:
            url = f"{self.base_url}/v3/accounts/{self.account_id}/orders/{order_id}/cancel"
            response = self.session.put(url)
            result = response.json()
            
            if response.status_code == 200:
                return OrderResult(
                    success=True,
                    order_id=order_id,
                    message="Order cancelled",
                    raw_response=result,
                )
            else:
                return OrderResult(
                    success=False,
                    message=f"Cancel failed: {result}",
                    raw_response=result,
                )
                
        except Exception as e:
            return OrderResult(success=False, message=str(e))
    
    def close_all_positions(self) -> List[OrderResult]:
        """Emergency: close all open positions"""
        results = []
        positions = self.get_positions()
        
        for pos in positions:
            result = self.close_position(pos.instrument)
            results.append(result)
        
        return results
    
    # ═══════════════════════════════════════════════════════════════════════════
    # UTILITY METHODS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def calculate_units(
        self,
        symbol: str,
        risk_amount: float,
        stop_loss_pips: float,
    ) -> int:
        """
        Calculate position size based on risk amount and stop loss.
        
        Args:
            symbol: Trading pair
            risk_amount: Amount to risk in account currency
            stop_loss_pips: Stop loss distance in pips
        
        Returns:
            Number of units to trade
        """
        # For most pairs, 1 pip = 0.0001
        # For JPY pairs, 1 pip = 0.01
        pip_value = 0.01 if "JPY" in symbol.upper() else 0.0001
        
        # Value per pip per unit
        # For standard lots (100,000 units), 1 pip = $10 for major pairs
        # So for 1 unit, 1 pip = $0.0001 for EURUSD
        
        # Calculate units
        # risk_amount = units * pip_value * stop_loss_pips
        # units = risk_amount / (pip_value * stop_loss_pips)
        
        if stop_loss_pips <= 0:
            return 0
        
        units = risk_amount / (pip_value * stop_loss_pips)
        
        # Round to nearest 1000 (mini lot)
        units = int(units / 1000) * 1000
        
        return max(units, 1000)  # Minimum 1 micro lot
    
    def get_pip_value(self, symbol: str) -> float:
        """Get pip value for a symbol"""
        return 0.01 if "JPY" in symbol.upper() else 0.0001


# Convenience function
def get_executor(environment: str = "practice") -> OANDAExecutor:
    """Get an executor instance"""
    return OANDAExecutor(environment=environment)


# Test
if __name__ == "__main__":
    print("Testing OANDA Executor...")
    
    executor = OANDAExecutor(environment="live")  # Using live for now since practice wasn't working
    
    # Get account info
    info = executor.get_account_info()
    if info:
        print(f"\nAccount: {info.account_id}")
        print(f"Balance: ${info.balance:,.2f}")
        print(f"NAV: ${info.nav:,.2f}")
        print(f"Margin Available: ${info.margin_available:,.2f}")
        print(f"Open Trades: {info.open_trade_count}")
    
    # Get positions
    positions = executor.get_positions()
    print(f"\nOpen Positions: {len(positions)}")
    for pos in positions:
        print(f"  {pos.instrument}: {pos.side} {pos.size} @ {pos.average_price:.5f} (PnL: ${pos.unrealized_pnl:.2f})")
