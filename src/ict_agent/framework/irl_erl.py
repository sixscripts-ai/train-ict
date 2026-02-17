"""ICT IRL/ERL Framework - The Decoder Key

This is THE foundational framework for understanding where price is going.

CORE CONCEPT:
Price always moves from one liquidity pool to another.
- IRL (Internal Range Liquidity): FVGs, OBs, breakers inside the range
- ERL (External Range Liquidity): Equal highs/lows, old swing points OUTSIDE the range

THE DECODER KEY:
1. If price is drawn to IRL → It will then seek ERL
2. If price sweeps ERL → It will then seek IRL

PRACTICAL APPLICATION:
- Entry at IRL (FVG, OB) → Target is ERL (old high/low, equal high/low)
- Entry after ERL sweep → Target is IRL (FVG, OB)

This framework determines:
- WHERE to enter (IRL zones)
- WHERE to target (ERL levels)
- WHAT model you're in (Buy Model seeks ERL above, Sell Model seeks ERL below)
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Tuple
import pandas as pd
import numpy as np

from ict_agent.detectors.fvg import FVG, FVGDirection
from ict_agent.detectors.order_block import OrderBlock, OBDirection
from ict_agent.detectors.market_structure import SwingPoint, SwingType


class LiquidityType(Enum):
    # Internal Range Liquidity (inside the range)
    FVG = "fvg"
    ORDER_BLOCK = "order_block"
    BREAKER = "breaker"
    MITIGATION_BLOCK = "mitigation_block"
    
    # External Range Liquidity (outside the range)
    EQUAL_HIGHS = "equal_highs"
    EQUAL_LOWS = "equal_lows"
    OLD_HIGH = "old_high"
    OLD_LOW = "old_low"
    RANGE_HIGH = "range_high"
    RANGE_LOW = "range_low"


class LiquiditySide(Enum):
    BUY_SIDE = "buy_side"   # Above price (highs, equal highs)
    SELL_SIDE = "sell_side"  # Below price (lows, equal lows)


@dataclass
class LiquidityPool:
    """Represents a pool of liquidity at a price level"""
    price: float
    pool_type: LiquidityType
    side: LiquiditySide
    is_internal: bool  # True = IRL, False = ERL
    strength: float  # 0-1 indicating how significant
    timestamp: pd.Timestamp
    index: int
    
    # State tracking
    swept: bool = False
    swept_at: Optional[pd.Timestamp] = None
    mitigated: bool = False
    mitigated_at: Optional[pd.Timestamp] = None
    
    # Reference to source
    source_fvg: Optional[FVG] = None
    source_ob: Optional[OrderBlock] = None
    source_swing: Optional[SwingPoint] = None
    
    @property
    def is_external(self) -> bool:
        return not self.is_internal


@dataclass
class DrawOnLiquidity:
    """Current draw on liquidity (where price is headed)"""
    target_pool: LiquidityPool
    probability: float
    distance_pips: float
    expected_path: List[LiquidityPool]  # IRL pools along the way


@dataclass
class RangeAnalysis:
    """Analysis of current range and its liquidity"""
    range_high: float
    range_low: float
    range_midpoint: float
    
    # Liquidity pools
    buy_side_erl: List[LiquidityPool] = field(default_factory=list)  # ERL above
    sell_side_erl: List[LiquidityPool] = field(default_factory=list)  # ERL below
    internal_liquidity: List[LiquidityPool] = field(default_factory=list)  # IRL in range
    
    # Current draw
    current_draw: Optional[DrawOnLiquidity] = None
    
    @property
    def premium_zone(self) -> Tuple[float, float]:
        """Above equilibrium - look for shorts"""
        return (self.range_midpoint, self.range_high)
    
    @property
    def discount_zone(self) -> Tuple[float, float]:
        """Below equilibrium - look for longs"""
        return (self.range_low, self.range_midpoint)
    
    def is_price_in_premium(self, price: float) -> bool:
        return price > self.range_midpoint
    
    def is_price_in_discount(self, price: float) -> bool:
        return price < self.range_midpoint


class IRLERLFramework:
    """
    The IRL/ERL Framework - The Decoder Key
    
    This framework maps all liquidity and determines:
    1. Where we are in the range (premium/discount)
    2. What liquidity has been taken
    3. What liquidity is the next target
    4. Entry zones (IRL) and targets (ERL)
    """
    
    def __init__(
        self,
        pip_size: float = 0.0001,
        equal_level_threshold: float = 5.0,  # pips tolerance for equal highs/lows
        lookback_periods: int = 100,
    ):
        self.pip_size = pip_size
        self.equal_level_threshold = equal_level_threshold * pip_size
        self.lookback_periods = lookback_periods
        
        self._liquidity_pools: List[LiquidityPool] = []
        self._range_analysis: Optional[RangeAnalysis] = None
    
    def analyze(
        self,
        ohlc: pd.DataFrame,
        swings: List[SwingPoint],
        fvgs: List[FVG] = None,
        order_blocks: List[OrderBlock] = None,
    ) -> RangeAnalysis:
        """
        Complete IRL/ERL analysis of the current price range.
        
        Args:
            ohlc: OHLCV data
            swings: Swing points from MarketStructureAnalyzer
            fvgs: Active FVGs
            order_blocks: Active Order Blocks
        
        Returns:
            RangeAnalysis with all liquidity mapped
        """
        if len(ohlc) < 10:
            return None
        
        # Clear previous pools
        self._liquidity_pools = []
        
        current_price = ohlc['close'].iloc[-1]
        
        # Define the range (using recent swing high/low)
        range_high, range_low = self._define_range(ohlc, swings)
        range_midpoint = (range_high + range_low) / 2
        
        # Map External Range Liquidity (swing highs/lows)
        self._map_external_liquidity(swings, current_price)
        
        # Map Internal Range Liquidity (FVGs, OBs)
        if fvgs:
            self._map_fvg_liquidity(fvgs, current_price, range_high, range_low)
        
        if order_blocks:
            self._map_ob_liquidity(order_blocks, current_price, range_high, range_low)
        
        # Create range analysis
        self._range_analysis = RangeAnalysis(
            range_high=range_high,
            range_low=range_low,
            range_midpoint=range_midpoint,
            buy_side_erl=[p for p in self._liquidity_pools 
                         if p.is_external and p.side == LiquiditySide.BUY_SIDE and not p.swept],
            sell_side_erl=[p for p in self._liquidity_pools
                          if p.is_external and p.side == LiquiditySide.SELL_SIDE and not p.swept],
            internal_liquidity=[p for p in self._liquidity_pools
                               if p.is_internal and not p.mitigated],
        )
        
        # Determine current draw on liquidity
        self._range_analysis.current_draw = self._determine_draw(
            current_price, self._range_analysis
        )
        
        return self._range_analysis
    
    def _define_range(
        self,
        ohlc: pd.DataFrame,
        swings: List[SwingPoint],
    ) -> Tuple[float, float]:
        """Define the current trading range"""
        
        # Use recent swing high and low
        recent_highs = [s for s in swings 
                       if s.swing_type == SwingType.HIGH][-5:]
        recent_lows = [s for s in swings
                      if s.swing_type == SwingType.LOW][-5:]
        
        if recent_highs and recent_lows:
            range_high = max(h.price for h in recent_highs)
            range_low = min(l.price for l in recent_lows)
        else:
            # Fallback to recent candle range
            lookback = min(self.lookback_periods, len(ohlc))
            range_high = ohlc['high'].iloc[-lookback:].max()
            range_low = ohlc['low'].iloc[-lookback:].min()
        
        return range_high, range_low
    
    def _map_external_liquidity(
        self,
        swings: List[SwingPoint],
        current_price: float,
    ) -> None:
        """Map External Range Liquidity from swing points"""
        
        swing_highs = [s for s in swings if s.swing_type == SwingType.HIGH]
        swing_lows = [s for s in swings if s.swing_type == SwingType.LOW]
        
        # Find equal highs (buy-side liquidity)
        equal_high_groups = self._find_equal_levels(swing_highs, is_high=True)
        for group in equal_high_groups:
            level_price = max(s.price for s in group)
            
            self._liquidity_pools.append(LiquidityPool(
                price=level_price,
                pool_type=LiquidityType.EQUAL_HIGHS,
                side=LiquiditySide.BUY_SIDE,
                is_internal=False,
                strength=min(len(group) * 0.25, 1.0),
                timestamp=group[-1].timestamp,
                index=group[-1].index,
                source_swing=group[-1],
            ))
        
        # Find equal lows (sell-side liquidity)
        equal_low_groups = self._find_equal_levels(swing_lows, is_high=False)
        for group in equal_low_groups:
            level_price = min(s.price for s in group)
            
            self._liquidity_pools.append(LiquidityPool(
                price=level_price,
                pool_type=LiquidityType.EQUAL_LOWS,
                side=LiquiditySide.SELL_SIDE,
                is_internal=False,
                strength=min(len(group) * 0.25, 1.0),
                timestamp=group[-1].timestamp,
                index=group[-1].index,
                source_swing=group[-1],
            ))
        
        # Add significant single swing points as old highs/lows
        for swing in swing_highs[-5:]:
            # Skip if already in equal group
            if not any(swing in group for group in equal_high_groups):
                self._liquidity_pools.append(LiquidityPool(
                    price=swing.price,
                    pool_type=LiquidityType.OLD_HIGH,
                    side=LiquiditySide.BUY_SIDE,
                    is_internal=False,
                    strength=0.5,
                    timestamp=swing.timestamp,
                    index=swing.index,
                    source_swing=swing,
                ))
        
        for swing in swing_lows[-5:]:
            if not any(swing in group for group in equal_low_groups):
                self._liquidity_pools.append(LiquidityPool(
                    price=swing.price,
                    pool_type=LiquidityType.OLD_LOW,
                    side=LiquiditySide.SELL_SIDE,
                    is_internal=False,
                    strength=0.5,
                    timestamp=swing.timestamp,
                    index=swing.index,
                    source_swing=swing,
                ))
    
    def _find_equal_levels(
        self,
        swings: List[SwingPoint],
        is_high: bool,
    ) -> List[List[SwingPoint]]:
        """Find groups of swings at equal price levels"""
        
        groups = []
        used_indices = set()
        
        for i, swing in enumerate(swings):
            if i in used_indices:
                continue
            
            group = [swing]
            used_indices.add(i)
            
            for j, other in enumerate(swings):
                if j in used_indices or j == i:
                    continue
                
                if abs(swing.price - other.price) <= self.equal_level_threshold:
                    group.append(other)
                    used_indices.add(j)
            
            if len(group) >= 2:
                groups.append(group)
        
        return groups
    
    def _map_fvg_liquidity(
        self,
        fvgs: List[FVG],
        current_price: float,
        range_high: float,
        range_low: float,
    ) -> None:
        """Map Internal Range Liquidity from FVGs"""
        
        for fvg in fvgs:
            # Skip fully mitigated FVGs
            if fvg.fully_mitigated:
                continue
            
            # Determine if FVG is inside the range
            fvg_mid = (fvg.top + fvg.bottom) / 2
            is_internal = range_low <= fvg_mid <= range_high
            
            # Determine side based on FVG direction and position
            if fvg.direction == FVGDirection.BULLISH:
                side = LiquiditySide.SELL_SIDE  # Bullish FVG is support (sell-side IRL)
            else:
                side = LiquiditySide.BUY_SIDE  # Bearish FVG is resistance (buy-side IRL)
            
            self._liquidity_pools.append(LiquidityPool(
                price=fvg.midpoint if fvg.midpoint else fvg_mid,
                pool_type=LiquidityType.FVG,
                side=side,
                is_internal=is_internal,
                strength=min(abs(fvg.top - fvg.bottom) / (50 * self.pip_size), 1.0),
                timestamp=fvg.timestamp,
                index=fvg.index,
                source_fvg=fvg,
            ))
    
    def _map_ob_liquidity(
        self,
        order_blocks: List[OrderBlock],
        current_price: float,
        range_high: float,
        range_low: float,
    ) -> None:
        """Map Internal Range Liquidity from Order Blocks"""
        
        for ob in order_blocks:
            if ob.mitigated:
                continue
            
            ob_mid = (ob.top + ob.bottom) / 2
            is_internal = range_low <= ob_mid <= range_high
            
            if ob.direction == OBDirection.BULLISH:
                side = LiquiditySide.SELL_SIDE  # Bullish OB is support
            else:
                side = LiquiditySide.BUY_SIDE  # Bearish OB is resistance
            
            self._liquidity_pools.append(LiquidityPool(
                price=ob_mid,
                pool_type=LiquidityType.ORDER_BLOCK,
                side=side,
                is_internal=is_internal,
                strength=0.7 if ob.displacement_pips and ob.displacement_pips > 10 else 0.5,
                timestamp=ob.timestamp,
                index=ob.index,
                source_ob=ob,
            ))
    
    def _determine_draw(
        self,
        current_price: float,
        analysis: RangeAnalysis,
    ) -> Optional[DrawOnLiquidity]:
        """Determine where price is being drawn to"""
        
        # Check if price is in premium or discount
        in_premium = analysis.is_price_in_premium(current_price)
        
        if in_premium:
            # In premium zone → Look to SHORT to sell-side ERL
            target_pools = analysis.sell_side_erl
        else:
            # In discount zone → Look to LONG to buy-side ERL
            target_pools = analysis.buy_side_erl
        
        if not target_pools:
            return None
        
        # Find nearest unswept ERL target
        if in_premium:
            target_pool = max(target_pools, key=lambda p: p.price)
        else:
            target_pool = min(target_pools, key=lambda p: p.price)
        
        # Calculate distance
        distance_pips = abs(target_pool.price - current_price) / self.pip_size
        
        # Find IRL pools along the expected path
        if in_premium:
            path_irl = [p for p in analysis.internal_liquidity 
                       if p.price < current_price and p.price > target_pool.price]
        else:
            path_irl = [p for p in analysis.internal_liquidity
                       if p.price > current_price and p.price < target_pool.price]
        
        return DrawOnLiquidity(
            target_pool=target_pool,
            probability=0.7 if target_pool.strength > 0.5 else 0.5,
            distance_pips=distance_pips,
            expected_path=sorted(path_irl, key=lambda p: abs(p.price - current_price)),
        )
    
    def get_entry_zones(self, direction: str = None) -> List[LiquidityPool]:
        """
        Get IRL zones suitable for entry.
        
        Args:
            direction: "long" or "short" to filter zones
        
        Returns:
            List of IRL pools suitable for entry
        """
        if not self._range_analysis:
            return []
        
        irl_zones = self._range_analysis.internal_liquidity
        
        if direction == "long":
            # For longs, look for bullish IRL (support)
            return [z for z in irl_zones if z.side == LiquiditySide.SELL_SIDE]
        elif direction == "short":
            # For shorts, look for bearish IRL (resistance)
            return [z for z in irl_zones if z.side == LiquiditySide.BUY_SIDE]
        
        return irl_zones
    
    def get_targets(self, direction: str) -> List[LiquidityPool]:
        """
        Get ERL targets for a trade direction.
        
        Args:
            direction: "long" or "short"
        
        Returns:
            List of ERL pools to target
        """
        if not self._range_analysis:
            return []
        
        if direction == "long":
            return sorted(self._range_analysis.buy_side_erl, key=lambda p: p.price)
        else:
            return sorted(self._range_analysis.sell_side_erl, key=lambda p: p.price, reverse=True)
    
    def update_liquidity_state(
        self,
        ohlc: pd.DataFrame,
    ) -> None:
        """Update swept/mitigated state of liquidity pools"""
        
        current_high = ohlc['high'].iloc[-1]
        current_low = ohlc['low'].iloc[-1]
        current_time = ohlc.index[-1]
        
        for pool in self._liquidity_pools:
            if pool.swept:
                continue
            
            # Check if ERL was swept
            if pool.is_external:
                if pool.side == LiquiditySide.BUY_SIDE:
                    if current_high > pool.price:
                        pool.swept = True
                        pool.swept_at = current_time
                else:
                    if current_low < pool.price:
                        pool.swept = True
                        pool.swept_at = current_time
            
            # Check if IRL was mitigated
            else:
                if pool.source_fvg:
                    if pool.source_fvg.fully_mitigated:
                        pool.mitigated = True
                        pool.mitigated_at = current_time
                
                if pool.source_ob:
                    if pool.source_ob.mitigated:
                        pool.mitigated = True
                        pool.mitigated_at = current_time
    
    def format_analysis(self) -> str:
        """Format the current analysis for display"""
        
        if not self._range_analysis:
            return "No analysis available"
        
        ra = self._range_analysis
        
        lines = [
            "=== IRL/ERL ANALYSIS ===",
            f"Range: {ra.range_low:.5f} - {ra.range_high:.5f}",
            f"Equilibrium: {ra.range_midpoint:.5f}",
            "",
            "--- BUY-SIDE ERL (Above) ---",
        ]
        
        for pool in sorted(ra.buy_side_erl, key=lambda p: p.price, reverse=True):
            status = "✓" if pool.swept else "○"
            lines.append(f"  {status} {pool.pool_type.value}: {pool.price:.5f}")
        
        lines.append("")
        lines.append("--- SELL-SIDE ERL (Below) ---")
        
        for pool in sorted(ra.sell_side_erl, key=lambda p: p.price, reverse=True):
            status = "✓" if pool.swept else "○"
            lines.append(f"  {status} {pool.pool_type.value}: {pool.price:.5f}")
        
        lines.append("")
        lines.append("--- INTERNAL RANGE LIQUIDITY ---")
        
        for pool in sorted(ra.internal_liquidity, key=lambda p: p.price, reverse=True):
            status = "✓" if pool.mitigated else "○"
            lines.append(f"  {status} {pool.pool_type.value}: {pool.price:.5f}")
        
        if ra.current_draw:
            lines.extend([
                "",
                "--- CURRENT DRAW ---",
                f"Target: {ra.current_draw.target_pool.pool_type.value} @ {ra.current_draw.target_pool.price:.5f}",
                f"Distance: {ra.current_draw.distance_pips:.1f} pips",
                f"IRL zones on path: {len(ra.current_draw.expected_path)}",
            ])
        
        return "\n".join(lines)
