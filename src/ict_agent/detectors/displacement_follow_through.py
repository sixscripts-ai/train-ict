"""Displacement Follow-Through Model

ICT Template Trade based on:
1. Prior displacement establishes bias (H4)
2. 4H Fair Value Gap as primary entry zone
3. 15M Order Block + 15M FVG confluence
4. CBDR setup present
5. Asian range liquidity sweep
6. Clear target (CBDR extension / Asian low)
7. Stop above/below last opposing candle

This is the A+ template trade model.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Literal
import pandas as pd


@dataclass
class ConfluenceFactor:
    """A single confluence factor for the trade"""
    name: str
    present: bool
    weight: float = 1.0  # Importance weight
    details: str = ""


@dataclass
class DisplacementFollowThrough:
    """
    Displacement Follow-Through Trade Setup
    
    This is the A+ template trade structure.
    """
    # Core Identification
    symbol: str
    direction: Literal['LONG', 'SHORT']
    setup_time: datetime
    
    # Bias (from prior displacement)
    prior_displacement_direction: Literal['BULLISH', 'BEARISH']
    displacement_time: Optional[datetime] = None
    displacement_candle_body_pips: float = 0.0
    
    # Entry Levels
    h4_fvg_top: float = 0.0  # 4H FVG zone
    h4_fvg_bottom: float = 0.0
    m15_ob_level: float = 0.0  # 15M Order Block
    m15_fvg_top: float = 0.0   # 15M FVG (should be confluent with OB)
    m15_fvg_bottom: float = 0.0
    
    # CBDR Levels
    cbdr_high: float = 0.0
    cbdr_low: float = 0.0
    cbdr_range: float = 0.0
    
    # Asian Range
    asian_high: float = 0.0
    asian_low: float = 0.0
    asian_swept: Literal['HIGH', 'LOW', 'NONE'] = 'NONE'
    sweep_price: float = 0.0
    
    # Trade Levels
    entry_price: float = 0.0
    stop_loss: float = 0.0
    take_profit: float = 0.0  # CBDR extension
    
    # Risk Metrics
    risk_pips: float = 0.0
    reward_pips: float = 0.0
    rr_ratio: float = 0.0
    
    # Confluences
    confluences: List[ConfluenceFactor] = field(default_factory=list)
    
    # State
    triggered: bool = False
    result: Optional[Literal['WIN', 'LOSS', 'BREAKEVEN']] = None
    pnl: float = 0.0
    
    @property
    def confluence_count(self) -> int:
        """Count of present confluences"""
        return sum(1 for c in self.confluences if c.present)
    
    @property
    def confidence_score(self) -> float:
        """
        Calculate confidence based on confluence count.
        A+ trade = 6-7 confluences
        """
        total_weight = sum(c.weight for c in self.confluences if c.present)
        max_weight = sum(c.weight for c in self.confluences)
        return (total_weight / max_weight * 100) if max_weight > 0 else 0
    
    @property
    def is_template_trade(self) -> bool:
        """Is this an A+ template trade? (6+ confluences)"""
        return self.confluence_count >= 6
    
    def calculate_cbdr_extension(self) -> float:
        """Calculate CBDR extension target"""
        if self.direction == 'SHORT':
            # Target is CBDR low - 1 SD (or Asian low if closer)
            sd_target = self.cbdr_low - self.cbdr_range
            return max(sd_target, self.asian_low) if self.asian_low > 0 else sd_target
        else:
            # Target is CBDR high + 1 SD (or Asian high if closer)
            sd_target = self.cbdr_high + self.cbdr_range
            return min(sd_target, self.asian_high) if self.asian_high > 0 else sd_target


class DisplacementFollowThroughDetector:
    """
    Detects Displacement Follow-Through setups.
    
    This is the A+ template trade detector that looks for:
    1. Prior H4 displacement (establishes bias)
    2. Asian range sweep (manipulation)
    3. H4 FVG + M15 OB/FVG confluence (entry zone)
    4. CBDR extension target
    """
    
    def __init__(self, pip_size: float = 0.0001):
        self.pip_size = pip_size
        self._current_setup: Optional[DisplacementFollowThrough] = None
    
    def detect(
        self,
        h4_data: pd.DataFrame,
        m15_data: pd.DataFrame,
        cbdr_high: float,
        cbdr_low: float,
        asian_high: float,
        asian_low: float,
        symbol: str = "EUR_USD"
    ) -> Optional[DisplacementFollowThrough]:
        """
        Detect a Displacement Follow-Through setup.
        
        Args:
            h4_data: H4 OHLC data
            m15_data: M15 OHLC data  
            cbdr_high: CBDR high level
            cbdr_low: CBDR low level
            asian_high: Asian session high
            asian_low: Asian session low
            symbol: Trading pair
        """
        if h4_data.empty or m15_data.empty:
            return None
        
        current_price = m15_data['close'].iloc[-1]
        current_time = m15_data.index[-1]
        
        # =================================================================
        # STEP 1: Check for prior H4 displacement (establishes bias)
        # =================================================================
        displacement = self._find_h4_displacement(h4_data)
        if displacement is None:
            return None
        
        bias = displacement['direction']
        
        # =================================================================
        # STEP 2: Check for Asian range sweep
        # =================================================================
        sweep = self._check_asian_sweep(m15_data, asian_high, asian_low)
        if sweep is None:
            return None
        
        # Validate sweep direction matches bias
        # BEARISH bias = need Asian HIGH swept (price went up first, now coming down)
        # BULLISH bias = need Asian LOW swept (price went down first, now coming up)
        if bias == 'BEARISH' and sweep['side'] != 'HIGH':
            return None
        if bias == 'BULLISH' and sweep['side'] != 'LOW':
            return None
        
        # =================================================================
        # STEP 3: Find H4 FVG in direction of bias
        # =================================================================
        h4_fvg = self._find_h4_fvg(h4_data, bias)
        if h4_fvg is None:
            return None
        
        # =================================================================
        # STEP 4: Find 15M OB + FVG confluence within H4 FVG
        # =================================================================
        m15_confluence = self._find_m15_confluence(
            m15_data, 
            h4_fvg['top'], 
            h4_fvg['bottom'],
            bias
        )
        
        # =================================================================
        # STEP 5: Calculate entry, stop, target
        # =================================================================
        cbdr_range = cbdr_high - cbdr_low if cbdr_high > 0 and cbdr_low > 0 else 0
        
        # Validate CBDR range (should be 5-40 pips for EUR/USD)
        if cbdr_range < 5 * self.pip_size or cbdr_range > 50 * self.pip_size:
            # Invalid CBDR - use Asian range instead
            cbdr_range = asian_high - asian_low if asian_high > 0 and asian_low > 0 else 0
            if cbdr_range == 0:
                return None  # Can't calculate valid targets
        
        if bias == 'BEARISH':
            direction = 'SHORT'
            # Entry at M15 OB/FVG if available, else H4 FVG midpoint
            if m15_confluence:
                entry_price = (m15_confluence['top'] + m15_confluence['bottom']) / 2
            else:
                entry_price = (h4_fvg['top'] + h4_fvg['bottom']) / 2
            
            # STOP PLACEMENT: Above the last up candle before displacement
            # Plus buffer to survive potential 15M zone retest (key insight from template)
            last_opposing_high = self._find_last_opposing_candle(h4_data, 'BEARISH')
            if last_opposing_high > 0:
                stop_loss = last_opposing_high + (5 * self.pip_size)
            else:
                stop_loss = sweep['price'] + (10 * self.pip_size)  # Fallback
            
            # TARGET: Asian low (the real draw on liquidity)
            if asian_low > 0 and asian_low < entry_price:
                take_profit = asian_low
            else:
                take_profit = entry_price - (30 * self.pip_size)
        else:
            direction = 'LONG'
            if m15_confluence:
                entry_price = (m15_confluence['top'] + m15_confluence['bottom']) / 2
            else:
                entry_price = (h4_fvg['top'] + h4_fvg['bottom']) / 2
            
            # Stop below the last down candle before displacement
            last_opposing_low = self._find_last_opposing_candle(h4_data, 'BULLISH')
            if last_opposing_low > 0:
                stop_loss = last_opposing_low - (5 * self.pip_size)
            else:
                stop_loss = sweep['price'] - (10 * self.pip_size)
            
            # Target: Asian high
            if asian_high > 0 and asian_high > entry_price:
                take_profit = asian_high
            else:
                take_profit = entry_price + (30 * self.pip_size)
        
        # Calculate R:R
        risk_pips = abs(entry_price - stop_loss) / self.pip_size
        reward_pips = abs(take_profit - entry_price) / self.pip_size
        
        # CAP stop distance at 20 pips for better R:R
        max_risk_pips = 20
        if risk_pips > max_risk_pips:
            risk_pips = max_risk_pips
            if direction == 'SHORT':
                stop_loss = entry_price + (max_risk_pips * self.pip_size)
            else:
                stop_loss = entry_price - (max_risk_pips * self.pip_size)
        
        # Minimum risk floor: 5 pips
        if risk_pips < 5:
            risk_pips = 5
            if direction == 'SHORT':
                stop_loss = entry_price + (5 * self.pip_size)
            else:
                stop_loss = entry_price - (5 * self.pip_size)
        
        if reward_pips > 50:
            reward_pips = 50
            if direction == 'SHORT':
                take_profit = entry_price - (50 * self.pip_size)
            else:
                take_profit = entry_price + (50 * self.pip_size)
        
        rr_ratio = reward_pips / risk_pips if risk_pips > 0 else 0
        
        # Maximum R:R sanity check
        if rr_ratio > 10:
            return None  # Something is wrong with the calculation
        
        # =================================================================
        # STEP 6: Build confluence list
        # =================================================================
        confluences = [
            ConfluenceFactor(
                name="Prior displacement (establishes bias)",
                present=displacement is not None,
                weight=2.0,
                details=f"H4 {bias} displacement"
            ),
            ConfluenceFactor(
                name="4H Fair Value Gap",
                present=h4_fvg is not None,
                weight=1.5,
                details=f"H4 FVG: {h4_fvg['top']:.5f} - {h4_fvg['bottom']:.5f}" if h4_fvg else ""
            ),
            ConfluenceFactor(
                name="15M Order Block",
                present=m15_confluence is not None and m15_confluence.get('has_ob', False),
                weight=1.0,
            ),
            ConfluenceFactor(
                name="15M Fair Value Gap (confluent with OB)",
                present=m15_confluence is not None and m15_confluence.get('has_fvg', False),
                weight=1.0,
            ),
            ConfluenceFactor(
                name="CBDR Setup",
                present=cbdr_range > 0 and cbdr_range < 50 * self.pip_size,  # Valid CBDR
                weight=1.0,
                details=f"CBDR range: {cbdr_range/self.pip_size:.0f} pips"
            ),
            ConfluenceFactor(
                name="Asian Range Sweep",
                present=sweep is not None,
                weight=1.5,
                details=f"Asian {sweep['side']} swept @ {sweep['price']:.5f}" if sweep else ""
            ),
            ConfluenceFactor(
                name="Target: CBDR extension / Asian level",
                present=take_profit > 0,
                weight=1.0,
                details=f"Target: {take_profit:.5f}"
            ),
        ]
        
        # =================================================================
        # Create the setup
        # =================================================================
        setup = DisplacementFollowThrough(
            symbol=symbol,
            direction=direction,
            setup_time=current_time.to_pydatetime() if hasattr(current_time, 'to_pydatetime') else current_time,
            prior_displacement_direction=bias,
            displacement_time=displacement['time'],
            h4_fvg_top=h4_fvg['top'] if h4_fvg else 0,
            h4_fvg_bottom=h4_fvg['bottom'] if h4_fvg else 0,
            cbdr_high=cbdr_high,
            cbdr_low=cbdr_low,
            cbdr_range=cbdr_range,
            asian_high=asian_high,
            asian_low=asian_low,
            asian_swept=sweep['side'] if sweep else 'NONE',
            sweep_price=sweep['price'] if sweep else 0,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            risk_pips=risk_pips,
            reward_pips=reward_pips,
            rr_ratio=rr_ratio,
            confluences=confluences,
        )
        
        self._current_setup = setup
        return setup
    
    def _find_h4_displacement(self, h4_data: pd.DataFrame) -> Optional[dict]:
        """Find prior H4 displacement candle"""
        if len(h4_data) < 5:
            return None
        
        # Look at last 15 H4 candles for displacement (wider window)
        recent = h4_data.tail(15)
        
        # Calculate ATR for displacement threshold (1.0x = body bigger than average range)
        atr = (recent['high'] - recent['low']).mean()
        displacement_threshold = atr * 1.0  # Relaxed from 1.5x
        
        for i in range(len(recent) - 2, -1, -1):
            candle = recent.iloc[i]
            body = abs(candle['close'] - candle['open'])
            
            if body > displacement_threshold:
                direction = 'BULLISH' if candle['close'] > candle['open'] else 'BEARISH'
                return {
                    'direction': direction,
                    'time': recent.index[i],
                    'body': body,
                }
        
        return None
    
    def _find_last_opposing_candle(self, h4_data: pd.DataFrame, bias: str) -> float:
        """
        Find the last opposing candle before displacement for stop placement.
        
        Template Trade Rule: Stop above last UP candle before DOWN move (or vice versa)
        This ensures the stop survives potential 15M zone retests.
        """
        if len(h4_data) < 5:
            return 0
        
        recent = h4_data.tail(10)
        
        # Find the displacement candle first
        atr = (recent['high'] - recent['low']).mean()
        displacement_threshold = atr * 1.5
        
        displacement_idx = -1
        for i in range(len(recent) - 1, -1, -1):
            candle = recent.iloc[i]
            body = abs(candle['close'] - candle['open'])
            is_expected_direction = (
                (bias == 'BEARISH' and candle['close'] < candle['open']) or
                (bias == 'BULLISH' and candle['close'] > candle['open'])
            )
            if body > displacement_threshold and is_expected_direction:
                displacement_idx = i
                break
        
        if displacement_idx <= 0:
            return 0
        
        # Now find the last OPPOSING candle before displacement
        for i in range(displacement_idx - 1, -1, -1):
            candle = recent.iloc[i]
            
            if bias == 'BEARISH':
                # Looking for last bullish (up) candle before bearish displacement
                if candle['close'] > candle['open']:
                    return candle['high']  # Stop goes above this high
            else:
                # Looking for last bearish (down) candle before bullish displacement
                if candle['close'] < candle['open']:
                    return candle['low']  # Stop goes below this low
        
        return 0
    
    def _check_asian_sweep(
        self, 
        m15_data: pd.DataFrame, 
        asian_high: float, 
        asian_low: float
    ) -> Optional[dict]:
        """Check if Asian range was swept"""
        if asian_high == 0 or asian_low == 0:
            return None
        
        recent = m15_data.tail(30)
        
        high_swept = recent['high'].max() > asian_high + (2 * self.pip_size)
        low_swept = recent['low'].min() < asian_low - (2 * self.pip_size)
        
        if high_swept and not low_swept:
            return {
                'side': 'HIGH',
                'price': recent['high'].max(),
            }
        elif low_swept and not high_swept:
            return {
                'side': 'LOW', 
                'price': recent['low'].min(),
            }
        elif high_swept and low_swept:
            # Both swept - use whichever happened first
            high_idx = recent['high'].idxmax()
            low_idx = recent['low'].idxmin()
            if high_idx < low_idx:
                return {'side': 'HIGH', 'price': recent.loc[high_idx, 'high']}
            else:
                return {'side': 'LOW', 'price': recent.loc[low_idx, 'low']}
        
        return None
    
    def _find_h4_fvg(self, h4_data: pd.DataFrame, bias: str) -> Optional[dict]:
        """Find H4 FVG in direction of bias"""
        if len(h4_data) < 5:
            return None
        
        recent = h4_data.tail(10)
        
        # Look for unmitigated FVGs
        for i in range(2, len(recent)):
            c1 = recent.iloc[i-2]  # First candle
            c2 = recent.iloc[i-1]  # Middle (displacement) candle  
            c3 = recent.iloc[i]    # Third candle
            
            if bias == 'BEARISH':
                # Bearish FVG: gap between C1 low and C3 high
                if c1['low'] > c3['high']:
                    return {
                        'top': c1['low'],
                        'bottom': c3['high'],
                        'time': recent.index[i-1],
                    }
            else:
                # Bullish FVG: gap between C1 high and C3 low
                if c1['high'] < c3['low']:
                    return {
                        'top': c3['low'],
                        'bottom': c1['high'],
                        'time': recent.index[i-1],
                    }
        
        return None
    
    def _find_m15_confluence(
        self,
        m15_data: pd.DataFrame,
        h4_fvg_top: float,
        h4_fvg_bottom: float,
        bias: str
    ) -> Optional[dict]:
        """Find 15M OB + FVG confluence within H4 FVG zone"""
        recent = m15_data.tail(20)
        
        has_ob = False
        has_fvg = False
        ob_level = 0
        fvg_top = 0
        fvg_bottom = 0
        
        # Look for Order Block (last opposing candle before move)
        for i in range(len(recent) - 1, 0, -1):
            candle = recent.iloc[i]
            
            # Check if candle is within H4 FVG zone
            if not (candle['low'] <= h4_fvg_top and candle['high'] >= h4_fvg_bottom):
                continue
            
            # Look for OB (last opposing candle)
            if bias == 'BEARISH' and candle['close'] > candle['open']:
                # Bullish candle before bearish move = bearish OB
                has_ob = True
                ob_level = candle['open']  # Use open as OB level
                break
            elif bias == 'BULLISH' and candle['close'] < candle['open']:
                # Bearish candle before bullish move = bullish OB
                has_ob = True
                ob_level = candle['open']
                break
        
        # Look for FVG within zone
        for i in range(2, len(recent)):
            c1 = recent.iloc[i-2]
            c3 = recent.iloc[i]
            
            if bias == 'BEARISH' and c1['low'] > c3['high']:
                if h4_fvg_bottom <= c3['high'] <= h4_fvg_top:
                    has_fvg = True
                    fvg_top = c1['low']
                    fvg_bottom = c3['high']
                    break
            elif bias == 'BULLISH' and c1['high'] < c3['low']:
                if h4_fvg_bottom <= c1['high'] <= h4_fvg_top:
                    has_fvg = True
                    fvg_top = c3['low']
                    fvg_bottom = c1['high']
                    break
        
        if has_ob or has_fvg:
            return {
                'has_ob': has_ob,
                'has_fvg': has_fvg,
                'ob_level': ob_level,
                'top': fvg_top if has_fvg else (ob_level + 10 * self.pip_size),
                'bottom': fvg_bottom if has_fvg else (ob_level - 10 * self.pip_size),
            }
        
        return None
    
    def get_current_setup(self) -> Optional[DisplacementFollowThrough]:
        """Get the current detected setup"""
        return self._current_setup
