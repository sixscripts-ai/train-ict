"""Judas Swing / AMD (Accumulation, Manipulation, Distribution) Detector

The Judas Swing is ICT's core intraday model:

1. ACCUMULATION: Asian session (7 PM - 12 AM EST) forms a range
2. MANIPULATION: London/NY sweeps ONE side of Asian range (fake-out)
3. DISTRIBUTION: Price reverses and moves in opposite direction (real move)

Trading Rule: Trade AGAINST the initial sweep direction
- If Asian HIGH is swept first → SELL (bearish Judas)
- If Asian LOW is swept first → BUY (bullish Judas)
"""

from dataclasses import dataclass
from datetime import datetime, time, timedelta
from typing import Optional, Literal
from zoneinfo import ZoneInfo
import pandas as pd

NY_TZ = ZoneInfo("America/New_York")


@dataclass
class AsianRange:
    """Asian session range (7 PM - 12 AM EST)"""
    date: datetime
    high: float
    low: float
    open_price: float
    close_price: float
    
    @property
    def range_pips(self) -> float:
        return abs(self.high - self.low) * 10000
    
    @property
    def midpoint(self) -> float:
        return (self.high + self.low) / 2
    
    @property
    def is_tight(self) -> bool:
        """Tight Asian range (<20 pips) = better Judas setups"""
        return self.range_pips < 20


@dataclass  
class JudasSwing:
    """Detected Judas Swing setup"""
    asian_range: AsianRange
    sweep_direction: Literal['HIGH', 'LOW']  # Which side was swept
    sweep_price: float
    sweep_time: datetime
    trade_direction: Literal['BUY', 'SELL']  # Trade AGAINST the sweep
    target: float  # Opposite side of Asian range
    invalidation: float  # Beyond the sweep
    
    @property
    def is_valid(self) -> bool:
        """Check if setup is still valid"""
        return True  # Add time-based invalidation if needed


class JudasSwingDetector:
    """
    Detects Judas Swing setups based on Asian range sweeps.
    
    ICT AMD Model:
    - Asian range forms the "accumulation" 
    - London/NY sweeps one side (manipulation / Judas move)
    - Trade the reversal (distribution)
    
    CBDR Confluence: Sweep should reach CBDR SD level for validation
    """
    
    # Asian session: 7 PM - 12 AM EST (can extend to 2 AM for wider range)
    ASIAN_START = time(19, 0)  # 7 PM EST
    ASIAN_END = time(0, 0)     # Midnight EST
    
    # Sweep detection window: London/NY session
    SWEEP_WINDOW_START = time(2, 0)   # 2 AM EST (London)
    SWEEP_WINDOW_END = time(11, 0)    # 11 AM EST (end of NY AM)
    
    def __init__(self, sweep_buffer_pips: float = 2.0, pip_size: float = 0.0001):
        """
        Args:
            sweep_buffer_pips: How many pips beyond Asian range = "sweep"
            pip_size: Pip size for the pair
        """
        self.sweep_buffer_pips = sweep_buffer_pips
        self.pip_size = pip_size
        self._current_asian_range: Optional[AsianRange] = None
        self._current_judas: Optional[JudasSwing] = None
        self._cbdr_range: Optional[float] = None  # CBDR range for SD calc
    
    def get_asian_range_from_data(self, df: pd.DataFrame) -> Optional[AsianRange]:
        """
        Calculate Asian range from OHLC data.
        
        Asian session: 7 PM - Midnight EST (previous day for intraday trading)
        """
        if df.empty:
            return None
        
        try:
            # Convert to NY timezone
            df_ny = df.copy()
            if df_ny.index.tz is None:
                df_ny.index = df_ny.index.tz_localize('UTC').tz_convert(NY_TZ)
            else:
                df_ny.index = df_ny.index.tz_convert(NY_TZ)
            
            now = df_ny.index[-1]
            
            # Determine which Asian session to use
            if now.hour < 12:
                # Before noon: use last night's Asian (same calendar day, started previous evening)
                asian_date = now.date()
                asian_start = datetime.combine(asian_date - timedelta(days=1), self.ASIAN_START, tzinfo=NY_TZ)
                asian_end = datetime.combine(asian_date, self.ASIAN_END, tzinfo=NY_TZ)
            else:
                # After noon: use tonight's Asian (starts this evening)
                asian_date = now.date()
                asian_start = datetime.combine(asian_date, self.ASIAN_START, tzinfo=NY_TZ)
                asian_end = datetime.combine(asian_date + timedelta(days=1), self.ASIAN_END, tzinfo=NY_TZ)
            
            # Get Asian session data
            asian_data = df_ny[(df_ny.index >= asian_start) & (df_ny.index <= asian_end)]
            
            if asian_data.empty or len(asian_data) < 3:
                # Fallback: use last 20 bars as proxy for range
                asian_data = df_ny.tail(20)
            
            return AsianRange(
                date=asian_date if 'asian_date' in dir() else now.date(),
                high=asian_data['high'].max(),
                low=asian_data['low'].min(),
                open_price=asian_data['open'].iloc[0],
                close_price=asian_data['close'].iloc[-1],
            )
            
        except Exception as e:
            # Fallback: use recent range
            recent = df.tail(20)
            return AsianRange(
                date=datetime.now(),
                high=recent['high'].max(),
                low=recent['low'].min(),
                open_price=recent['open'].iloc[0],
                close_price=recent['close'].iloc[-1],
            )
    
    def detect_judas_sweep(
        self, 
        df: pd.DataFrame, 
        asian_range: Optional[AsianRange] = None,
        cbdr_high: Optional[float] = None,
        cbdr_low: Optional[float] = None,
        require_sd_confluence: bool = False,
    ) -> Optional[JudasSwing]:
        """
        Detect if price has swept one side of Asian range.
        
        Args:
            df: OHLC data
            asian_range: Pre-calculated Asian range (optional)
            cbdr_high: CBDR high for SD calculation (optional)
            cbdr_low: CBDR low for SD calculation (optional)
            require_sd_confluence: If True, sweep must reach SD level
        
        Returns JudasSwing setup if sweep detected, None otherwise.
        """
        if asian_range is None:
            asian_range = self.get_asian_range_from_data(df)
        
        if asian_range is None:
            return None
        
        self._current_asian_range = asian_range
        
        # Calculate CBDR SD levels if provided
        sd_1_high = None
        sd_1_low = None
        if cbdr_high is not None and cbdr_low is not None:
            cbdr_range = cbdr_high - cbdr_low
            self._cbdr_range = cbdr_range
            sd_1_high = cbdr_high + cbdr_range  # SD+1
            sd_1_low = cbdr_low - cbdr_range     # SD-1
        
        # Get recent price action (last 50 bars)
        recent = df.tail(50)
        current_price = recent['close'].iloc[-1]
        current_time = recent.index[-1]
        
        sweep_buffer = self.sweep_buffer_pips * self.pip_size
        
        # Check for high sweep (price went above Asian high)
        high_sweep = recent['high'].max() > asian_range.high + sweep_buffer
        high_sweep_idx = recent['high'].idxmax() if high_sweep else None
        high_sweep_price = recent.loc[high_sweep_idx, 'high'] if high_sweep else None
        
        # Check for low sweep (price went below Asian low)
        low_sweep = recent['low'].min() < asian_range.low - sweep_buffer
        low_sweep_idx = recent['low'].idxmin() if low_sweep else None
        low_sweep_price = recent.loc[low_sweep_idx, 'low'] if low_sweep else None
        
        # CBDR SD Confluence Check
        if require_sd_confluence and sd_1_high is not None:
            # High sweep must reach at least SD+1
            if high_sweep and high_sweep_price < sd_1_high:
                high_sweep = False  # Sweep didn't reach SD level, invalidate
            # Low sweep must reach at least SD-1
            if low_sweep and low_sweep_price > sd_1_low:
                low_sweep = False  # Sweep didn't reach SD level, invalidate
        
        # Determine which sweep happened FIRST (that's the Judas move)
        if high_sweep and low_sweep:
            # Both swept - use the FIRST one
            if high_sweep_idx < low_sweep_idx:
                sweep_direction = 'HIGH'
                sweep_price = high_sweep_price
                sweep_time = high_sweep_idx
            else:
                sweep_direction = 'LOW'
                sweep_price = low_sweep_price
                sweep_time = low_sweep_idx
        elif high_sweep:
            sweep_direction = 'HIGH'
            sweep_price = high_sweep_price
            sweep_time = high_sweep_idx
        elif low_sweep:
            sweep_direction = 'LOW'
            sweep_price = low_sweep_price
            sweep_time = low_sweep_idx
        else:
            # No sweep yet
            return None
        
        # KEY RULE: Trade AGAINST the sweep
        if sweep_direction == 'HIGH':
            # Asian HIGH was swept → Bearish Judas → SELL
            trade_direction = 'SELL'
            target = asian_range.low  # Target opposite side
            invalidation = sweep_price + (5 * self.pip_size)  # SL above sweep
        else:
            # Asian LOW was swept → Bullish Judas → BUY
            trade_direction = 'BUY'
            target = asian_range.high  # Target opposite side
            invalidation = sweep_price - (5 * self.pip_size)  # SL below sweep
        
        # Validate: Price must have returned into the range (not still extended)
        if trade_direction == 'SELL' and current_price > asian_range.high:
            # Price still above range, wait for it to come back
            return None
        elif trade_direction == 'BUY' and current_price < asian_range.low:
            # Price still below range, wait for it to come back
            return None
        
        judas = JudasSwing(
            asian_range=asian_range,
            sweep_direction=sweep_direction,
            sweep_price=sweep_price,
            sweep_time=sweep_time.to_pydatetime() if hasattr(sweep_time, 'to_pydatetime') else sweep_time,
            trade_direction=trade_direction,
            target=target,
            invalidation=invalidation,
        )
        
        self._current_judas = judas
        return judas
    
    def get_current_setup(self) -> Optional[JudasSwing]:
        """Get most recently detected Judas setup"""
        return self._current_judas
    
    def get_asian_range(self) -> Optional[AsianRange]:
        """Get current Asian range"""
        return self._current_asian_range
