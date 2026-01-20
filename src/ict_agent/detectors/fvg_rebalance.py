"""
FVG Rebalance Tracker

Tracks Fair Value Gaps (BISI/SIBI) and monitors when they get:
- Partially filled (price enters the FVG)
- Fully filled (price trades through entire FVG)
- Rebalanced (price offers delivery in both directions)

ICT Concept (from SIBI/BISI transcript):
- A range is NOT rebalanced just by price passing through it
- Rebalance requires BOTH buy-side AND sell-side delivery
- Until rebalanced, FVGs remain significant for entries/targets
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Literal
from enum import Enum


class FVGType(Enum):
    """Type of Fair Value Gap"""
    BISI = "BISI"  # Buyside Imbalance Sellside Inefficiency (Bullish FVG)
    SIBI = "SIBI"  # Sellside Imbalance Buyside Inefficiency (Bearish FVG)


class FVGStatus(Enum):
    """Status of FVG fill"""
    UNFILLED = "unfilled"           # Price hasn't touched FVG
    WICKED = "wicked"               # Wick entered but no body
    PARTIAL_FILL = "partial_fill"   # Price entered but didn't fill completely
    FULL_FILL = "full_fill"         # Price traded through entire FVG
    REBALANCED = "rebalanced"       # Both buy and sell side delivery occurred


@dataclass
class FVGFillEvent:
    """Record of an FVG fill attempt"""
    timestamp: datetime
    price: float
    fill_type: Literal["wick", "body", "full"]
    fill_percentage: float  # 0-100
    direction: Literal["into", "through"]  # Into = partial, Through = full
    

@dataclass
class TrackedFVG:
    """A Fair Value Gap being tracked for rebalance"""
    id: str
    type: FVGType
    timeframe: str
    
    # FVG boundaries
    high: float
    low: float
    midpoint: float
    
    # Context
    pair: str
    formation_time: datetime
    formation_candle_idx: int
    
    # Status tracking
    status: FVGStatus = FVGStatus.UNFILLED
    fill_percentage: float = 0.0
    
    # Rebalance tracking (ICT concept)
    buyside_delivered: bool = False   # Price moved up through zone
    sellside_delivered: bool = False  # Price moved down through zone
    
    # Fill history
    fill_events: List[FVGFillEvent] = field(default_factory=list)
    
    # Outcome
    entry_taken: bool = False
    target_hit: bool = False
    notes: str = ""
    
    @property
    def gap_size_pips(self) -> float:
        """Gap size in pips (assumes 0.0001 pip value)"""
        return (self.high - self.low) / 0.0001
    
    @property
    def is_valid_entry(self) -> bool:
        """FVG is valid for entry if not fully rebalanced"""
        return self.status not in [FVGStatus.REBALANCED]
    
    @property
    def remaining_gap(self) -> float:
        """Percentage of gap remaining unfilled"""
        return 100 - self.fill_percentage
    
    def check_rebalance(self) -> bool:
        """Check if FVG is now rebalanced"""
        if self.buyside_delivered and self.sellside_delivered:
            self.status = FVGStatus.REBALANCED
            return True
        return False


class FVGRebalanceTracker:
    """
    Tracks FVGs and monitors their fill/rebalance status.
    
    Key ICT Concepts:
    - FVG is not rebalanced until BOTH directions have been delivered
    - Buyside delivery = price moving up through zone
    - Sellside delivery = price moving down through zone
    - Partial fills create entry opportunities
    - Full rebalance removes FVG significance
    """
    
    def __init__(self, pip_value: float = 0.0001):
        self.pip_value = pip_value
        self.tracked_fvgs: Dict[str, TrackedFVG] = {}
        self.alerts: List[Dict] = []
    
    def add_fvg(
        self,
        pair: str,
        timeframe: str,
        fvg_type: FVGType,
        high: float,
        low: float,
        formation_time: datetime,
        candle_idx: int = 0
    ) -> TrackedFVG:
        """
        Add a new FVG to track.
        
        Args:
            pair: Trading pair
            timeframe: Timeframe (e.g., "15M", "4H")
            fvg_type: BISI or SIBI
            high: FVG high price
            low: FVG low price
            formation_time: When FVG formed
            candle_idx: Index of formation candle
        
        Returns:
            TrackedFVG object
        """
        fvg_id = f"{pair}_{timeframe}_{fvg_type.value}_{formation_time.strftime('%Y%m%d%H%M')}"
        
        fvg = TrackedFVG(
            id=fvg_id,
            type=fvg_type,
            timeframe=timeframe,
            high=high,
            low=low,
            midpoint=(high + low) / 2,
            pair=pair,
            formation_time=formation_time,
            formation_candle_idx=candle_idx
        )
        
        self.tracked_fvgs[fvg_id] = fvg
        return fvg
    
    def update_price(
        self,
        pair: str,
        current_price: float,
        candle_high: float,
        candle_low: float,
        candle_open: float,
        candle_close: float,
        timestamp: datetime
    ) -> List[Dict]:
        """
        Update all tracked FVGs with new price data.
        
        Args:
            pair: Trading pair
            current_price: Current price
            candle_high: Current candle high
            candle_low: Current candle low
            candle_open: Current candle open
            candle_close: Current candle close
            timestamp: Current time
        
        Returns:
            List of alerts generated
        """
        alerts = []
        
        for fvg_id, fvg in self.tracked_fvgs.items():
            if fvg.pair != pair:
                continue
            
            if fvg.status == FVGStatus.REBALANCED:
                continue  # Skip already rebalanced FVGs
            
            # Check for FVG interaction
            alert = self._check_fvg_interaction(
                fvg, candle_high, candle_low, candle_open, candle_close, timestamp
            )
            
            if alert:
                alerts.append(alert)
                self.alerts.append(alert)
        
        return alerts
    
    def _check_fvg_interaction(
        self,
        fvg: TrackedFVG,
        candle_high: float,
        candle_low: float,
        candle_open: float,
        candle_close: float,
        timestamp: datetime
    ) -> Optional[Dict]:
        """Check if candle interacts with FVG"""
        
        body_high = max(candle_open, candle_close)
        body_low = min(candle_open, candle_close)
        
        # Check if price entered FVG
        wick_entered = candle_low <= fvg.high and candle_high >= fvg.low
        body_entered = body_low <= fvg.high and body_high >= fvg.low
        
        if not wick_entered:
            return None  # No interaction
        
        alert = None
        old_status = fvg.status
        
        # Calculate fill percentage
        if fvg.type == FVGType.BISI:
            # Bullish FVG - filled from above (sellside delivery)
            if candle_low <= fvg.low:
                fill_pct = 100
                fvg.sellside_delivered = True
            elif candle_low < fvg.high:
                fill_pct = ((fvg.high - candle_low) / (fvg.high - fvg.low)) * 100
            else:
                fill_pct = 0
                
            # Check for buyside delivery (price moving up)
            if candle_high >= fvg.high:
                fvg.buyside_delivered = True
                
        else:
            # Bearish FVG (SIBI) - filled from below (buyside delivery)
            if candle_high >= fvg.high:
                fill_pct = 100
                fvg.buyside_delivered = True
            elif candle_high > fvg.low:
                fill_pct = ((candle_high - fvg.low) / (fvg.high - fvg.low)) * 100
            else:
                fill_pct = 0
                
            # Check for sellside delivery (price moving down)
            if candle_low <= fvg.low:
                fvg.sellside_delivered = True
        
        # Update fill percentage (keep highest)
        fvg.fill_percentage = max(fvg.fill_percentage, fill_pct)
        
        # Determine fill type
        if body_entered:
            fill_type = "body"
        else:
            fill_type = "wick"
        
        if fill_pct >= 100:
            fill_type = "full"
        
        # Record fill event
        event = FVGFillEvent(
            timestamp=timestamp,
            price=(candle_high + candle_low) / 2,
            fill_type=fill_type,
            fill_percentage=fill_pct,
            direction="through" if fill_pct >= 100 else "into"
        )
        fvg.fill_events.append(event)
        
        # Update status
        if fvg.check_rebalance():
            fvg.status = FVGStatus.REBALANCED
        elif fill_pct >= 100:
            fvg.status = FVGStatus.FULL_FILL
        elif body_entered:
            fvg.status = FVGStatus.PARTIAL_FILL
        elif wick_entered and fvg.status == FVGStatus.UNFILLED:
            fvg.status = FVGStatus.WICKED
        
        # Generate alert if status changed
        if fvg.status != old_status:
            alert = {
                "type": "fvg_status_change",
                "fvg_id": fvg.id,
                "fvg_type": fvg.type.value,
                "pair": fvg.pair,
                "timeframe": fvg.timeframe,
                "old_status": old_status.value,
                "new_status": fvg.status.value,
                "fill_percentage": round(fvg.fill_percentage, 1),
                "buyside_delivered": fvg.buyside_delivered,
                "sellside_delivered": fvg.sellside_delivered,
                "timestamp": timestamp.isoformat(),
                "message": self._generate_alert_message(fvg, old_status)
            }
        
        return alert
    
    def _generate_alert_message(self, fvg: TrackedFVG, old_status: FVGStatus) -> str:
        """Generate human-readable alert message"""
        
        if fvg.status == FVGStatus.REBALANCED:
            return (f"🔄 {fvg.pair} {fvg.timeframe} {fvg.type.value} REBALANCED - "
                    f"Both buy and sell side delivered. FVG no longer significant.")
        
        elif fvg.status == FVGStatus.FULL_FILL:
            return (f"✅ {fvg.pair} {fvg.timeframe} {fvg.type.value} FULL FILL - "
                    f"Price traded through entire FVG ({fvg.low:.5f} - {fvg.high:.5f})")
        
        elif fvg.status == FVGStatus.PARTIAL_FILL:
            return (f"🟡 {fvg.pair} {fvg.timeframe} {fvg.type.value} PARTIAL FILL - "
                    f"{fvg.fill_percentage:.0f}% filled. Potential entry zone!")
        
        elif fvg.status == FVGStatus.WICKED:
            return (f"⚡ {fvg.pair} {fvg.timeframe} {fvg.type.value} WICKED - "
                    f"Price wicked into FVG but no body close. Watch for entry.")
        
        return f"{fvg.pair} {fvg.type.value} status: {fvg.status.value}"
    
    def get_active_fvgs(
        self,
        pair: Optional[str] = None,
        timeframe: Optional[str] = None,
        fvg_type: Optional[FVGType] = None,
        exclude_rebalanced: bool = True
    ) -> List[TrackedFVG]:
        """
        Get active (non-rebalanced) FVGs.
        
        Args:
            pair: Optional filter by pair
            timeframe: Optional filter by timeframe
            fvg_type: Optional filter by BISI/SIBI
            exclude_rebalanced: If True, exclude rebalanced FVGs
        
        Returns:
            List of matching TrackedFVG objects
        """
        fvgs = []
        
        for fvg in self.tracked_fvgs.values():
            if pair and fvg.pair != pair:
                continue
            if timeframe and fvg.timeframe != timeframe:
                continue
            if fvg_type and fvg.type != fvg_type:
                continue
            if exclude_rebalanced and fvg.status == FVGStatus.REBALANCED:
                continue
            
            fvgs.append(fvg)
        
        return fvgs
    
    def get_entry_candidates(
        self,
        pair: str,
        direction: Literal["LONG", "SHORT"],
        current_price: float
    ) -> List[TrackedFVG]:
        """
        Get FVGs that could be entry candidates.
        
        Args:
            pair: Trading pair
            direction: Trade direction
            current_price: Current price
        
        Returns:
            List of FVGs suitable for entry
        """
        candidates = []
        
        # For LONG trades, look for SIBI (bearish FVGs) below price
        # For SHORT trades, look for BISI (bullish FVGs) above price
        target_type = FVGType.SIBI if direction == "LONG" else FVGType.BISI
        
        for fvg in self.get_active_fvgs(pair=pair, fvg_type=target_type):
            if not fvg.is_valid_entry:
                continue
            
            if direction == "LONG":
                # SIBI below price - price could retrace down to it
                if fvg.high < current_price:
                    distance_pips = (current_price - fvg.midpoint) / self.pip_value
                    if distance_pips <= 50:  # Within 50 pips
                        candidates.append(fvg)
            else:
                # BISI above price - price could retrace up to it
                if fvg.low > current_price:
                    distance_pips = (fvg.midpoint - current_price) / self.pip_value
                    if distance_pips <= 50:
                        candidates.append(fvg)
        
        return candidates
    
    def format_fvg_report(self, fvg: TrackedFVG) -> str:
        """Format FVG status as readable report"""
        status_emoji = {
            FVGStatus.UNFILLED: "⬜",
            FVGStatus.WICKED: "⚡",
            FVGStatus.PARTIAL_FILL: "🟡",
            FVGStatus.FULL_FILL: "✅",
            FVGStatus.REBALANCED: "🔄"
        }
        
        type_emoji = "📈" if fvg.type == FVGType.BISI else "📉"
        
        lines = [
            f"{type_emoji} {fvg.type.value} - {fvg.pair} {fvg.timeframe}",
            f"   Status: {status_emoji.get(fvg.status, '?')} {fvg.status.value}",
            f"   Range: {fvg.low:.5f} - {fvg.high:.5f} ({fvg.gap_size_pips:.1f} pips)",
            f"   Midpoint: {fvg.midpoint:.5f}",
            f"   Fill: {fvg.fill_percentage:.0f}%",
            f"   Buyside Delivered: {'✅' if fvg.buyside_delivered else '❌'}",
            f"   Sellside Delivered: {'✅' if fvg.sellside_delivered else '❌'}",
        ]
        
        if fvg.fill_events:
            lines.append(f"   Events: {len(fvg.fill_events)} interactions")
        
        return "\n".join(lines)
    
    def format_tracker_summary(self, pair: Optional[str] = None) -> str:
        """Format summary of all tracked FVGs"""
        fvgs = self.get_active_fvgs(pair=pair, exclude_rebalanced=False)
        
        if not fvgs:
            return "No FVGs being tracked"
        
        lines = [
            f"═══════════════════════════════════════",
            f"  FVG REBALANCE TRACKER",
            f"═══════════════════════════════════════",
            f"",
        ]
        
        # Group by status
        by_status = {}
        for fvg in fvgs:
            status = fvg.status.value
            if status not in by_status:
                by_status[status] = []
            by_status[status].append(fvg)
        
        for status, status_fvgs in by_status.items():
            lines.append(f"📊 {status.upper()} ({len(status_fvgs)})")
            for fvg in status_fvgs:
                type_emoji = "📈" if fvg.type == FVGType.BISI else "📉"
                lines.append(f"   {type_emoji} {fvg.pair} {fvg.timeframe}: "
                           f"{fvg.low:.5f}-{fvg.high:.5f} ({fvg.fill_percentage:.0f}% filled)")
            lines.append("")
        
        return "\n".join(lines)
