"""
CBDR - Central Bank Dealer Range Detector

ICT's CBDR is the price range formed between 2pm-8pm New York time.
This range is used to project standard deviations for the next session's
high/low of day targets.

Key Rules:
- Time: 2pm-8pm NY (18:00-00:00 UTC during EST, 17:00-23:00 UTC during EDT)
- Ideal Range: 20-30 pips
- Maximum Range: <40 pips for valid projections
- Projections: 1SD, 2SD, 3SD, 4SD above/below the range

Usage:
- Bullish days: Low of day forms 1-3 SD below CBDR
- Bearish days: High of day forms 1-3 SD above CBDR
- 4SD typically only on high-impact news or NY reversal profiles
"""

from dataclasses import dataclass, field
from datetime import datetime, time, timedelta
from typing import List, Optional, Dict, Literal
from enum import Enum
import pytz


class CBDRQuality(Enum):
    """Quality rating of a CBDR range"""
    IDEAL = "ideal"           # 20-30 pips - best for projections
    ACCEPTABLE = "acceptable" # 30-40 pips - can use with caution
    INVALID = "invalid"       # >40 pips - skip projections


@dataclass
class StandardDeviation:
    """A standard deviation projection from CBDR"""
    level: int                # 1, 2, 3, or 4
    direction: Literal["above", "below"]
    price: float
    pips_from_range: float


@dataclass 
class CBDRRange:
    """Complete CBDR analysis for a session"""
    date: str                 # Date of the CBDR (format: YYYY-MM-DD)
    start_time: datetime      # 2pm NY
    end_time: datetime        # 8pm NY
    high: float               # Highest price in range
    low: float                # Lowest price in range
    range_pips: float         # Range in pips
    quality: CBDRQuality      # Quality rating
    
    # Standard deviation projections
    sd_above: List[StandardDeviation] = field(default_factory=list)
    sd_below: List[StandardDeviation] = field(default_factory=list)
    
    # Body-based range (optional, more precise)
    body_high: Optional[float] = None
    body_low: Optional[float] = None
    body_range_pips: Optional[float] = None
    
    def __post_init__(self):
        """Calculate standard deviations after initialization"""
        if not self.sd_above or not self.sd_below:
            self._calculate_standard_deviations()
    
    def _calculate_standard_deviations(self):
        """Calculate 1-4 SD projections above and below"""
        self.sd_above = []
        self.sd_below = []
        
        for level in range(1, 5):
            # Above projections
            price_above = self.high + (self.range_pips * level * 0.0001)
            self.sd_above.append(StandardDeviation(
                level=level,
                direction="above",
                price=round(price_above, 5),
                pips_from_range=round(self.range_pips * level, 1)
            ))
            
            # Below projections
            price_below = self.low - (self.range_pips * level * 0.0001)
            self.sd_below.append(StandardDeviation(
                level=level,
                direction="below",
                price=round(price_below, 5),
                pips_from_range=round(self.range_pips * level, 1)
            ))
    
    def get_projection(self, direction: str, level: int) -> Optional[StandardDeviation]:
        """Get a specific SD projection"""
        projections = self.sd_above if direction == "above" else self.sd_below
        for sd in projections:
            if sd.level == level:
                return sd
        return None
    
    def get_bullish_targets(self) -> Dict[str, float]:
        """For bullish days, get likely LOW of day targets (below CBDR)"""
        return {
            "ideal_low": self.sd_below[0].price,      # 1SD - most common
            "extended_low": self.sd_below[1].price,   # 2SD - still common
            "extreme_low": self.sd_below[2].price,    # 3SD - high impact news
        }
    
    def get_bearish_targets(self) -> Dict[str, float]:
        """For bearish days, get likely HIGH of day targets (above CBDR)"""
        return {
            "ideal_high": self.sd_above[0].price,     # 1SD - most common
            "extended_high": self.sd_above[1].price,  # 2SD - still common
            "extreme_high": self.sd_above[2].price,   # 3SD - high impact news
        }


class CBDRDetector:
    """
    Detects and analyzes Central Bank Dealer Range.
    
    CBDR is used to project where the high/low of day will form:
    - Sell days: High forms 1-3 SD above CBDR
    - Buy days: Low forms 1-3 SD below CBDR
    """
    
    # CBDR time window (New York time)
    CBDR_START_HOUR = 14  # 2pm NY
    CBDR_END_HOUR = 20    # 8pm NY
    
    # Range thresholds (in pips)
    IDEAL_MIN = 20
    IDEAL_MAX = 30
    MAXIMUM = 40
    
    def __init__(self, pip_value: float = 0.0001):
        """
        Initialize CBDR detector.
        
        Args:
            pip_value: Pip value for the pair (0.0001 for most, 0.01 for JPY pairs)
        """
        self.pip_value = pip_value
        self.ny_tz = pytz.timezone('America/New_York')
    
    def detect(
        self,
        candles: List[Dict],
        date: Optional[str] = None,
        use_bodies: bool = True
    ) -> Optional[CBDRRange]:
        """
        Detect CBDR range from candle data.
        
        Args:
            candles: List of candle dicts with 'time', 'open', 'high', 'low', 'close'
            date: Optional specific date to analyze (YYYY-MM-DD)
            use_bodies: If True, also calculate body-based range (recommended)
        
        Returns:
            CBDRRange object or None if insufficient data
        """
        # Filter candles to CBDR window
        cbdr_candles = self._filter_cbdr_candles(candles, date)
        
        if not cbdr_candles:
            return None
        
        # Calculate wick-based range
        high = max(c['high'] for c in cbdr_candles)
        low = min(c['low'] for c in cbdr_candles)
        range_pips = (high - low) / self.pip_value
        
        # Determine quality
        quality = self._determine_quality(range_pips)
        
        # Get time bounds
        first_candle = cbdr_candles[0]
        last_candle = cbdr_candles[-1]
        
        cbdr = CBDRRange(
            date=date or self._extract_date(first_candle['time']),
            start_time=self._parse_time(first_candle['time']),
            end_time=self._parse_time(last_candle['time']),
            high=high,
            low=low,
            range_pips=round(range_pips, 1),
            quality=quality
        )
        
        # Calculate body-based range if requested
        if use_bodies:
            body_highs = [max(c['open'], c['close']) for c in cbdr_candles]
            body_lows = [min(c['open'], c['close']) for c in cbdr_candles]
            cbdr.body_high = max(body_highs)
            cbdr.body_low = min(body_lows)
            cbdr.body_range_pips = round(
                (cbdr.body_high - cbdr.body_low) / self.pip_value, 1
            )
        
        return cbdr
    
    def _filter_cbdr_candles(
        self, 
        candles: List[Dict], 
        date: Optional[str]
    ) -> List[Dict]:
        """Filter candles to CBDR time window (2pm-8pm NY)"""
        cbdr_candles = []
        
        for candle in candles:
            candle_time = self._parse_time(candle['time'])
            ny_time = candle_time.astimezone(self.ny_tz)
            
            # Check if in CBDR window
            if self.CBDR_START_HOUR <= ny_time.hour < self.CBDR_END_HOUR:
                # If date specified, check it matches
                if date:
                    candle_date = ny_time.strftime('%Y-%m-%d')
                    if candle_date == date:
                        cbdr_candles.append(candle)
                else:
                    cbdr_candles.append(candle)
        
        return cbdr_candles
    
    def _determine_quality(self, range_pips: float) -> CBDRQuality:
        """Determine CBDR quality based on range size"""
        if self.IDEAL_MIN <= range_pips <= self.IDEAL_MAX:
            return CBDRQuality.IDEAL
        elif range_pips < self.MAXIMUM:
            return CBDRQuality.ACCEPTABLE
        else:
            return CBDRQuality.INVALID
    
    def _parse_time(self, time_str: str) -> datetime:
        """Parse time string to datetime"""
        if isinstance(time_str, datetime):
            return time_str
        
        # Try common formats
        formats = [
            '%Y-%m-%dT%H:%M:%S.%fZ',
            '%Y-%m-%dT%H:%M:%SZ',
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%dT%H:%M:%S',
        ]
        
        for fmt in formats:
            try:
                dt = datetime.strptime(time_str, fmt)
                return dt.replace(tzinfo=pytz.UTC)
            except ValueError:
                continue
        
        raise ValueError(f"Cannot parse time: {time_str}")
    
    def _extract_date(self, time_str: str) -> str:
        """Extract date string from time"""
        dt = self._parse_time(time_str)
        ny_time = dt.astimezone(self.ny_tz)
        return ny_time.strftime('%Y-%m-%d')
    
    def analyze_day_projection(
        self,
        cbdr: CBDRRange,
        daily_bias: Literal["bullish", "bearish"],
        current_price: Optional[float] = None
    ) -> Dict:
        """
        Analyze CBDR projections for the trading day.
        
        Args:
            cbdr: CBDR range object
            daily_bias: Expected direction for the day
            current_price: Current market price for context
        
        Returns:
            Analysis dict with targets and recommendations
        """
        analysis = {
            "cbdr_date": cbdr.date,
            "range_pips": cbdr.range_pips,
            "quality": cbdr.quality.value,
            "bias": daily_bias,
            "tradeable": cbdr.quality != CBDRQuality.INVALID,
        }
        
        if daily_bias == "bullish":
            # Bullish day - look for LOW of day below CBDR
            targets = cbdr.get_bullish_targets()
            analysis["target_type"] = "low_of_day"
            analysis["targets"] = targets
            analysis["recommendation"] = (
                f"Look for LOW of day to form at 1SD ({targets['ideal_low']:.5f}) "
                f"or 2SD ({targets['extended_low']:.5f}) below CBDR during London session"
            )
        else:
            # Bearish day - look for HIGH of day above CBDR
            targets = cbdr.get_bearish_targets()
            analysis["target_type"] = "high_of_day"
            analysis["targets"] = targets
            analysis["recommendation"] = (
                f"Look for HIGH of day to form at 1SD ({targets['ideal_high']:.5f}) "
                f"or 2SD ({targets['extended_high']:.5f}) above CBDR during London session"
            )
        
        if current_price:
            analysis["current_price"] = current_price
            # Calculate distance to nearest target
            if daily_bias == "bullish":
                nearest = targets['ideal_low']
                distance = (current_price - nearest) / self.pip_value
            else:
                nearest = targets['ideal_high']
                distance = (nearest - current_price) / self.pip_value
            analysis["pips_to_target"] = round(distance, 1)
        
        return analysis
    
    def format_cbdr_report(self, cbdr: CBDRRange) -> str:
        """Format CBDR analysis as readable report"""
        quality_emoji = {
            CBDRQuality.IDEAL: "✅",
            CBDRQuality.ACCEPTABLE: "⚠️",
            CBDRQuality.INVALID: "❌"
        }
        
        lines = [
            f"═══════════════════════════════════════",
            f"  CBDR Analysis - {cbdr.date}",
            f"═══════════════════════════════════════",
            f"",
            f"📊 Range: {cbdr.range_pips} pips {quality_emoji[cbdr.quality]}",
            f"   High: {cbdr.high:.5f}",
            f"   Low:  {cbdr.low:.5f}",
            f"",
        ]
        
        if cbdr.body_range_pips:
            lines.extend([
                f"📦 Body Range: {cbdr.body_range_pips} pips",
                f"   Body High: {cbdr.body_high:.5f}",
                f"   Body Low:  {cbdr.body_low:.5f}",
                f"",
            ])
        
        lines.extend([
            f"📈 Bearish Day Targets (HIGH of day):",
        ])
        for sd in cbdr.sd_above[:3]:
            lines.append(f"   {sd.level}SD: {sd.price:.5f} (+{sd.pips_from_range} pips)")
        
        lines.extend([
            f"",
            f"📉 Bullish Day Targets (LOW of day):",
        ])
        for sd in cbdr.sd_below[:3]:
            lines.append(f"   {sd.level}SD: {sd.price:.5f} (-{sd.pips_from_range} pips)")
        
        if cbdr.quality == CBDRQuality.INVALID:
            lines.extend([
                f"",
                f"⚠️ WARNING: Range too large ({cbdr.range_pips} pips)",
                f"   Projections may be unreliable. Consider skipping day trades.",
            ])
        
        return "\n".join(lines)
