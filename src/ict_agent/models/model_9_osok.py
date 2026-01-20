"""
ICT Model 9: One Shot One Kill Weekly Trading Model

A weekly range expansion model designed to capture 50-75 pips per week
by identifying the weekly high/low formation, typically on Mon-Wed.

Core Concepts:
- External Range Liquidity (ERL): Liquidity outside dealing range (double tops/bottoms)
- Internal Range Liquidity (IRL): FVGs, voids, order blocks inside dealing range
- Key Rule: IRL entries run to ERL targets (and vice versa for Turtle Soup)

Weekly Protocol:
1. Determine weekly bias from Monthly/Weekly charts
2. Mon-Wed: Look for weekly high (bearish) or low (bullish) to form
3. Enter at IRL (OB/FVG) targeting ERL (swing highs/lows)
4. Target: 50-75 pips, one trade per week
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Literal, Tuple
from enum import Enum


class WeeklyBias(Enum):
    """Weekly directional bias"""
    BULLISH = "bullish"   # Looking for lows to buy
    BEARISH = "bearish"   # Looking for highs to sell
    NEUTRAL = "neutral"   # No clear bias


class LiquidityType(Enum):
    """Type of liquidity pool"""
    INTERNAL = "internal"   # IRL - FVGs, OBs, voids (entry zones)
    EXTERNAL = "external"   # ERL - Swing highs/lows (target zones)


class DayOfWeek(Enum):
    """Day classification for OSOK"""
    MONDAY = 0
    TUESDAY = 1
    WEDNESDAY = 2
    THURSDAY = 3
    FRIDAY = 4
    WEEKEND = 5


@dataclass
class LiquidityPool:
    """A liquidity pool (internal or external)"""
    type: LiquidityType
    direction: Literal["buy_side", "sell_side"]  # Buy side = above, Sell side = below
    price: float
    description: str
    strength: int = 1  # 1-3, higher = stronger
    
    @property
    def is_target(self) -> bool:
        """External liquidity is typically a target"""
        return self.type == LiquidityType.EXTERNAL
    
    @property
    def is_entry(self) -> bool:
        """Internal liquidity is typically an entry zone"""
        return self.type == LiquidityType.INTERNAL


@dataclass
class WeeklySetup:
    """One Shot One Kill weekly setup"""
    week_start: str              # Monday's date
    bias: WeeklyBias
    
    # Liquidity analysis
    erl_targets: List[LiquidityPool] = field(default_factory=list)
    irl_entries: List[LiquidityPool] = field(default_factory=list)
    
    # Weekly range
    weekly_high: Optional[float] = None
    weekly_low: Optional[float] = None
    weekly_open: Optional[float] = None
    
    # Trade tracking
    entry_price: Optional[float] = None
    entry_day: Optional[DayOfWeek] = None
    target_price: Optional[float] = None
    stop_price: Optional[float] = None
    
    # Outcome
    high_of_week_day: Optional[DayOfWeek] = None
    low_of_week_day: Optional[DayOfWeek] = None
    pip_target: float = 50.0  # Default 50-75 pip target
    
    def get_primary_target(self) -> Optional[LiquidityPool]:
        """Get the primary ERL target based on bias"""
        if not self.erl_targets:
            return None
        
        if self.bias == WeeklyBias.BULLISH:
            # Bullish = target buy side liquidity (highs)
            buy_side = [t for t in self.erl_targets if t.direction == "buy_side"]
            return max(buy_side, key=lambda x: x.strength) if buy_side else None
        else:
            # Bearish = target sell side liquidity (lows)
            sell_side = [t for t in self.erl_targets if t.direction == "sell_side"]
            return max(sell_side, key=lambda x: x.strength) if sell_side else None
    
    def get_primary_entry(self) -> Optional[LiquidityPool]:
        """Get the primary IRL entry zone based on bias"""
        if not self.irl_entries:
            return None
        
        if self.bias == WeeklyBias.BULLISH:
            # Bullish = enter at sell side IRL (discounts)
            sell_side = [e for e in self.irl_entries if e.direction == "sell_side"]
            return max(sell_side, key=lambda x: x.strength) if sell_side else None
        else:
            # Bearish = enter at buy side IRL (premiums)
            buy_side = [e for e in self.irl_entries if e.direction == "buy_side"]
            return max(buy_side, key=lambda x: x.strength) if buy_side else None


@dataclass
class OSOKSignal:
    """One Shot One Kill trade signal"""
    setup: WeeklySetup
    signal_type: Literal["entry", "target_hit", "stop_hit", "weekly_level_formed"]
    price: float
    timestamp: datetime
    day: DayOfWeek
    notes: str = ""
    confidence: float = 0.0  # 0-1


class Model9Detector:
    """
    ICT Model 9: One Shot One Kill
    
    Weekly range expansion model for 50-75 pip captures.
    
    Key Principles:
    1. IRL to ERL: Enter at internal range liquidity, target external range liquidity
    2. Mon-Wed Focus: Weekly high/low typically forms Mon-Wed
    3. Single Trade: One high-probability trade per week
    4. Backup Protocol: If OSOK fails, drop to Model 8 (25 pips) or scalping
    """
    
    # Target pip ranges
    MIN_TARGET = 50
    MAX_TARGET = 75
    BACKUP_TARGET = 25  # Model 8 backup
    
    # Day weights (higher = more likely for weekly high/low)
    DAY_WEIGHTS = {
        DayOfWeek.MONDAY: 0.7,
        DayOfWeek.TUESDAY: 1.0,    # Highest probability
        DayOfWeek.WEDNESDAY: 0.9,
        DayOfWeek.THURSDAY: 0.4,
        DayOfWeek.FRIDAY: 0.2,
    }
    
    def __init__(self, pip_value: float = 0.0001):
        """
        Initialize Model 9 detector.
        
        Args:
            pip_value: Pip value for the pair
        """
        self.pip_value = pip_value
        self.active_setup: Optional[WeeklySetup] = None
        self.signals: List[OSOKSignal] = []
    
    def analyze_weekly_bias(
        self,
        monthly_data: List[Dict],
        weekly_data: List[Dict],
        daily_data: List[Dict]
    ) -> WeeklyBias:
        """
        Determine weekly bias from higher timeframe analysis.
        
        Args:
            monthly_data: Monthly candles for macro direction
            weekly_data: Weekly candles for range expansion direction
            daily_data: Daily candles for entry timing
        
        Returns:
            WeeklyBias enum
        """
        # Simple bias determination (can be enhanced)
        if not weekly_data or len(weekly_data) < 2:
            return WeeklyBias.NEUTRAL
        
        last_weekly = weekly_data[-1]
        prev_weekly = weekly_data[-2]
        
        # Check weekly momentum
        weekly_bullish = last_weekly['close'] > prev_weekly['close']
        weekly_higher_low = last_weekly['low'] > prev_weekly['low']
        weekly_higher_high = last_weekly['high'] > prev_weekly['high']
        
        # Monthly context
        monthly_bullish = False
        if monthly_data and len(monthly_data) >= 1:
            last_monthly = monthly_data[-1]
            monthly_bullish = last_monthly['close'] > last_monthly['open']
        
        # Determine bias
        if weekly_bullish and weekly_higher_low:
            return WeeklyBias.BULLISH
        elif not weekly_bullish and not weekly_higher_high:
            return WeeklyBias.BEARISH
        else:
            return WeeklyBias.NEUTRAL
    
    def identify_liquidity_pools(
        self,
        daily_data: List[Dict],
        weekly_data: List[Dict]
    ) -> Tuple[List[LiquidityPool], List[LiquidityPool]]:
        """
        Identify external (targets) and internal (entries) liquidity pools.
        
        Returns:
            Tuple of (ERL targets, IRL entries)
        """
        erl_targets = []
        irl_entries = []
        
        if not daily_data or len(daily_data) < 5:
            return erl_targets, irl_entries
        
        # External Range Liquidity - Swing highs/lows
        highs = [c['high'] for c in daily_data[-20:]]
        lows = [c['low'] for c in daily_data[-20:]]
        
        # Find significant swing highs (buy side liquidity)
        for i in range(2, len(highs) - 2):
            if highs[i] > highs[i-1] and highs[i] > highs[i-2] and \
               highs[i] > highs[i+1] and highs[i] > highs[i+2]:
                erl_targets.append(LiquidityPool(
                    type=LiquidityType.EXTERNAL,
                    direction="buy_side",
                    price=highs[i],
                    description="Swing High - Buy Side Liquidity",
                    strength=2
                ))
        
        # Find significant swing lows (sell side liquidity)
        for i in range(2, len(lows) - 2):
            if lows[i] < lows[i-1] and lows[i] < lows[i-2] and \
               lows[i] < lows[i+1] and lows[i] < lows[i+2]:
                erl_targets.append(LiquidityPool(
                    type=LiquidityType.EXTERNAL,
                    direction="sell_side",
                    price=lows[i],
                    description="Swing Low - Sell Side Liquidity",
                    strength=2
                ))
        
        # Find equal highs/lows (higher strength ERL)
        for i in range(1, len(highs)):
            if abs(highs[i] - highs[i-1]) < 5 * self.pip_value:
                erl_targets.append(LiquidityPool(
                    type=LiquidityType.EXTERNAL,
                    direction="buy_side",
                    price=max(highs[i], highs[i-1]),
                    description="Equal Highs - Strong Buy Side Liquidity",
                    strength=3
                ))
        
        for i in range(1, len(lows)):
            if abs(lows[i] - lows[i-1]) < 5 * self.pip_value:
                erl_targets.append(LiquidityPool(
                    type=LiquidityType.EXTERNAL,
                    direction="sell_side",
                    price=min(lows[i], lows[i-1]),
                    description="Equal Lows - Strong Sell Side Liquidity",
                    strength=3
                ))
        
        # Internal Range Liquidity - FVGs (simplified detection)
        for i in range(2, len(daily_data)):
            candle = daily_data[i]
            prev_candle = daily_data[i-1]
            prev_prev = daily_data[i-2]
            
            # Bullish FVG (BISI) - entry for sells
            if prev_prev['high'] < candle['low']:
                gap_size = (candle['low'] - prev_prev['high']) / self.pip_value
                if gap_size >= 5:  # Minimum 5 pip gap
                    irl_entries.append(LiquidityPool(
                        type=LiquidityType.INTERNAL,
                        direction="buy_side",
                        price=(candle['low'] + prev_prev['high']) / 2,  # Mid of FVG
                        description=f"Bullish FVG ({gap_size:.0f} pips) - IRL Entry Zone",
                        strength=2 if gap_size >= 10 else 1
                    ))
            
            # Bearish FVG (SIBI) - entry for buys
            if prev_prev['low'] > candle['high']:
                gap_size = (prev_prev['low'] - candle['high']) / self.pip_value
                if gap_size >= 5:
                    irl_entries.append(LiquidityPool(
                        type=LiquidityType.INTERNAL,
                        direction="sell_side",
                        price=(prev_prev['low'] + candle['high']) / 2,
                        description=f"Bearish FVG ({gap_size:.0f} pips) - IRL Entry Zone",
                        strength=2 if gap_size >= 10 else 1
                    ))
        
        return erl_targets, irl_entries
    
    def create_weekly_setup(
        self,
        week_start: str,
        bias: WeeklyBias,
        daily_data: List[Dict],
        weekly_data: List[Dict]
    ) -> WeeklySetup:
        """
        Create a One Shot One Kill weekly setup.
        
        Args:
            week_start: Monday's date (YYYY-MM-DD)
            bias: Weekly directional bias
            daily_data: Daily candles
            weekly_data: Weekly candles
        
        Returns:
            WeeklySetup object
        """
        erl_targets, irl_entries = self.identify_liquidity_pools(daily_data, weekly_data)
        
        setup = WeeklySetup(
            week_start=week_start,
            bias=bias,
            erl_targets=erl_targets,
            irl_entries=irl_entries,
        )
        
        # Set weekly open if available
        if weekly_data:
            setup.weekly_open = weekly_data[-1].get('open')
        
        self.active_setup = setup
        return setup
    
    def check_entry_opportunity(
        self,
        current_price: float,
        current_day: DayOfWeek,
        timestamp: datetime
    ) -> Optional[OSOKSignal]:
        """
        Check if current price is at an IRL entry zone.
        
        Args:
            current_price: Current market price
            current_day: Day of the week
            timestamp: Current timestamp
        
        Returns:
            OSOKSignal if entry opportunity, None otherwise
        """
        if not self.active_setup or self.active_setup.entry_price:
            return None  # No setup or already entered
        
        # Check day weight
        day_weight = self.DAY_WEIGHTS.get(current_day, 0.1)
        if day_weight < 0.4:
            return None  # Not an ideal day
        
        # Check IRL entry zones
        primary_entry = self.active_setup.get_primary_entry()
        if not primary_entry:
            return None
        
        # Check if price is near entry zone (within 10 pips)
        distance = abs(current_price - primary_entry.price) / self.pip_value
        if distance <= 10:
            primary_target = self.active_setup.get_primary_target()
            
            signal = OSOKSignal(
                setup=self.active_setup,
                signal_type="entry",
                price=current_price,
                timestamp=timestamp,
                day=current_day,
                notes=f"Price at {primary_entry.description}. "
                      f"Target: {primary_target.price if primary_target else 'TBD'}",
                confidence=day_weight * primary_entry.strength / 3
            )
            self.signals.append(signal)
            return signal
        
        return None
    
    def calculate_trade_parameters(
        self,
        entry_price: float,
        setup: Optional[WeeklySetup] = None
    ) -> Dict:
        """
        Calculate stop loss and take profit for OSOK trade.
        
        Args:
            entry_price: Entry price
            setup: Optional setup (uses active_setup if not provided)
        
        Returns:
            Dict with stop, target, and R:R
        """
        setup = setup or self.active_setup
        if not setup:
            return {}
        
        primary_target = setup.get_primary_target()
        primary_entry = setup.get_primary_entry()
        
        if setup.bias == WeeklyBias.BULLISH:
            # Long trade
            target = primary_target.price if primary_target else entry_price + (self.MIN_TARGET * self.pip_value)
            stop = primary_entry.price - (20 * self.pip_value) if primary_entry else entry_price - (30 * self.pip_value)
        else:
            # Short trade
            target = primary_target.price if primary_target else entry_price - (self.MIN_TARGET * self.pip_value)
            stop = primary_entry.price + (20 * self.pip_value) if primary_entry else entry_price + (30 * self.pip_value)
        
        risk = abs(entry_price - stop) / self.pip_value
        reward = abs(target - entry_price) / self.pip_value
        rr_ratio = reward / risk if risk > 0 else 0
        
        return {
            "entry": entry_price,
            "stop": round(stop, 5),
            "target": round(target, 5),
            "risk_pips": round(risk, 1),
            "reward_pips": round(reward, 1),
            "rr_ratio": round(rr_ratio, 2),
            "direction": "LONG" if setup.bias == WeeklyBias.BULLISH else "SHORT"
        }
    
    def format_weekly_analysis(self, setup: Optional[WeeklySetup] = None) -> str:
        """Format weekly OSOK analysis as readable report"""
        setup = setup or self.active_setup
        if not setup:
            return "No active OSOK setup"
        
        bias_emoji = {"bullish": "📈", "bearish": "📉", "neutral": "➖"}
        
        lines = [
            f"═══════════════════════════════════════",
            f"  MODEL 9: One Shot One Kill",
            f"  Week of {setup.week_start}",
            f"═══════════════════════════════════════",
            f"",
            f"{bias_emoji.get(setup.bias.value, '?')} Weekly Bias: {setup.bias.value.upper()}",
            f"🎯 Target: {self.MIN_TARGET}-{self.MAX_TARGET} pips",
            f"📅 Focus Days: Monday-Wednesday",
            f"",
        ]
        
        # External Range Liquidity (Targets)
        lines.append("💎 EXTERNAL LIQUIDITY (Targets):")
        if setup.erl_targets:
            for target in sorted(setup.erl_targets, key=lambda x: -x.strength)[:5]:
                strength_stars = "⭐" * target.strength
                lines.append(f"   {target.direction.replace('_', ' ').title()}: {target.price:.5f} {strength_stars}")
        else:
            lines.append("   None identified")
        
        lines.append("")
        
        # Internal Range Liquidity (Entries)
        lines.append("🔹 INTERNAL LIQUIDITY (Entry Zones):")
        if setup.irl_entries:
            for entry in sorted(setup.irl_entries, key=lambda x: -x.strength)[:5]:
                strength_stars = "⭐" * entry.strength
                lines.append(f"   {entry.description[:40]}: {entry.price:.5f} {strength_stars}")
        else:
            lines.append("   None identified")
        
        lines.append("")
        
        # Trade plan
        primary_entry = setup.get_primary_entry()
        primary_target = setup.get_primary_target()
        
        if primary_entry and primary_target:
            lines.extend([
                "📋 TRADE PLAN:",
                f"   Entry Zone: {primary_entry.price:.5f}",
                f"   Target: {primary_target.price:.5f}",
                f"   Direction: {'BUY' if setup.bias == WeeklyBias.BULLISH else 'SELL'}",
                "",
                "⚡ EXECUTION RULES:",
                "   • Wait for IRL entry during London/NY AM",
                "   • Enter at OB/FVG within IRL zone",
                "   • Target ERL (swing high/low)",
                "   • If setup fails, switch to Model 8 (25 pips)",
            ])
        
        return "\n".join(lines)
