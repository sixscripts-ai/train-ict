"""Order Block Detection Module

Detects institutional order blocks - the last opposite-colored candle before
a strong displacement move.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional
import pandas as pd
import numpy as np


class OBDirection(Enum):
    BULLISH = 1
    BEARISH = -1


@dataclass
class OrderBlock:
    """Represents an Order Block"""
    index: int
    timestamp: pd.Timestamp
    direction: OBDirection
    open_price: float
    close_price: float
    high: float
    low: float
    body_top: float
    body_bottom: float
    midpoint: float
    volume: float
    mitigated: bool = False
    mitigation_index: Optional[int] = None
    
    @property
    def is_valid(self) -> bool:
        return not self.mitigated
    
    def contains_price(self, price: float) -> bool:
        return self.low <= price <= self.high
    
    def body_contains_price(self, price: float) -> bool:
        return self.body_bottom <= price <= self.body_top


class OrderBlockDetector:
    """
    Detects Order Blocks in OHLCV data.
    
    Order Block Rules:
    - Bullish OB: Last DOWN candle before bullish displacement
    - Bearish OB: Last UP candle before bearish displacement
    - Must precede displacement (strong institutional move)
    - Most reactive when nested within OTE or aligned with FVG
    """
    
    def __init__(
        self,
        min_displacement_pips: float = 10.0,
        pip_size: float = 0.0001,
        lookback: int = 5,
        close_mitigation: bool = False,
    ):
        self.min_displacement_pips = min_displacement_pips
        self.pip_size = pip_size
        self.lookback = lookback
        self.close_mitigation = close_mitigation
        self._order_blocks: list[OrderBlock] = []
    
    def detect(self, ohlc: pd.DataFrame) -> pd.DataFrame:
        """
        Detect all Order Blocks in the given OHLC data.
        
        Args:
            ohlc: DataFrame with columns ['open', 'high', 'low', 'close', 'volume']
        
        Returns:
            DataFrame with Order Block information for each bar
        """
        if len(ohlc) < 3:
            return self._empty_result(ohlc)
        
        result = pd.DataFrame(index=ohlc.index)
        result["ob_direction"] = 0
        result["ob_top"] = np.nan
        result["ob_bottom"] = np.nan
        result["ob_body_top"] = np.nan
        result["ob_body_bottom"] = np.nan
        result["ob_midpoint"] = np.nan
        result["ob_volume"] = np.nan
        result["ob_mitigated"] = False
        
        self._order_blocks = []
        has_volume = "volume" in ohlc.columns
        
        for i in range(1, len(ohlc)):
            current = ohlc.iloc[i]
            is_bullish_candle = current["close"] > current["open"]
            is_bearish_candle = current["close"] < current["open"]
            
            candle_range = current["high"] - current["low"]
            min_displacement = self.min_displacement_pips * self.pip_size
            
            if is_bullish_candle and candle_range >= min_displacement:
                ob_idx = self._find_last_bearish_candle(ohlc, i)
                if ob_idx is not None:
                    self._record_ob(result, ohlc, ob_idx, OBDirection.BULLISH, has_volume)
            
            elif is_bearish_candle and candle_range >= min_displacement:
                ob_idx = self._find_last_bullish_candle(ohlc, i)
                if ob_idx is not None:
                    self._record_ob(result, ohlc, ob_idx, OBDirection.BEARISH, has_volume)
        
        self._check_mitigation(ohlc, result)
        
        return result
    
    def _find_last_bearish_candle(
        self, ohlc: pd.DataFrame, displacement_idx: int
    ) -> Optional[int]:
        """Find the last bearish candle before bullish displacement"""
        start = max(0, displacement_idx - self.lookback)
        
        for i in range(displacement_idx - 1, start - 1, -1):
            candle = ohlc.iloc[i]
            if candle["close"] < candle["open"]:
                return i
        
        return None
    
    def _find_last_bullish_candle(
        self, ohlc: pd.DataFrame, displacement_idx: int
    ) -> Optional[int]:
        """Find the last bullish candle before bearish displacement"""
        start = max(0, displacement_idx - self.lookback)
        
        for i in range(displacement_idx - 1, start - 1, -1):
            candle = ohlc.iloc[i]
            if candle["close"] > candle["open"]:
                return i
        
        return None
    
    def _record_ob(
        self,
        result: pd.DataFrame,
        ohlc: pd.DataFrame,
        index: int,
        direction: OBDirection,
        has_volume: bool,
    ) -> None:
        """Record Order Block in result DataFrame and internal list"""
        candle = ohlc.iloc[index]
        idx = ohlc.index[index]
        
        body_top = max(candle["open"], candle["close"])
        body_bottom = min(candle["open"], candle["close"])
        midpoint = (body_top + body_bottom) / 2
        volume = candle["volume"] if has_volume else 0
        
        result.loc[idx, "ob_direction"] = direction.value
        result.loc[idx, "ob_top"] = candle["high"]
        result.loc[idx, "ob_bottom"] = candle["low"]
        result.loc[idx, "ob_body_top"] = body_top
        result.loc[idx, "ob_body_bottom"] = body_bottom
        result.loc[idx, "ob_midpoint"] = midpoint
        result.loc[idx, "ob_volume"] = volume
        
        ob = OrderBlock(
            index=index,
            timestamp=idx,
            direction=direction,
            open_price=candle["open"],
            close_price=candle["close"],
            high=candle["high"],
            low=candle["low"],
            body_top=body_top,
            body_bottom=body_bottom,
            midpoint=midpoint,
            volume=volume,
        )
        self._order_blocks.append(ob)
    
    def _check_mitigation(self, ohlc: pd.DataFrame, result: pd.DataFrame) -> None:
        """Check if Order Blocks have been mitigated"""
        for ob in self._order_blocks:
            for i in range(ob.index + 1, len(ohlc)):
                candle = ohlc.iloc[i]
                
                if self.close_mitigation:
                    test_price = candle["close"]
                else:
                    test_price = candle["low"] if ob.direction == OBDirection.BULLISH else candle["high"]
                
                if ob.direction == OBDirection.BULLISH:
                    if test_price <= ob.body_bottom:
                        ob.mitigated = True
                        ob.mitigation_index = i
                        result.loc[ob.timestamp, "ob_mitigated"] = True
                        break
                else:
                    if test_price >= ob.body_top:
                        ob.mitigated = True
                        ob.mitigation_index = i
                        result.loc[ob.timestamp, "ob_mitigated"] = True
                        break
    
    def _empty_result(self, ohlc: pd.DataFrame) -> pd.DataFrame:
        """Return empty result DataFrame"""
        result = pd.DataFrame(index=ohlc.index)
        result["ob_direction"] = 0
        result["ob_top"] = np.nan
        result["ob_bottom"] = np.nan
        result["ob_body_top"] = np.nan
        result["ob_body_bottom"] = np.nan
        result["ob_midpoint"] = np.nan
        result["ob_volume"] = np.nan
        result["ob_mitigated"] = False
        return result
    
    def get_active_order_blocks(
        self, direction: Optional[OBDirection] = None
    ) -> list[OrderBlock]:
        """Get all unmitigated Order Blocks"""
        active = [ob for ob in self._order_blocks if not ob.mitigated]
        if direction:
            active = [ob for ob in active if ob.direction == direction]
        return active
    
    def get_nearest_order_block(
        self, price: float, direction: OBDirection
    ) -> Optional[OrderBlock]:
        """Get the nearest unmitigated Order Block to the given price"""
        active = self.get_active_order_blocks(direction)
        if not active:
            return None
        
        if direction == OBDirection.BULLISH:
            below = [ob for ob in active if ob.high < price]
            if below:
                return max(below, key=lambda ob: ob.high)
        else:
            above = [ob for ob in active if ob.low > price]
            if above:
                return min(above, key=lambda ob: ob.low)
        
        return None
