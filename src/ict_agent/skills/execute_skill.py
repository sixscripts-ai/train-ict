"""
ExecuteSkill — Places trades through OANDA.
Wraps: OANDAExecutor, RiskGuardian, AgentJournal
"""

import time
from typing import Any, Dict
from datetime import datetime
from zoneinfo import ZoneInfo

from ict_agent.skills.base import Skill, SkillResult
from ict_agent.events.event_types import TradeEvent, RiskEvent, EventType

NY_TZ = ZoneInfo("America/New_York")


class ExecuteSkill(Skill):
    name = "execute"
    description = "Execute a trade through OANDA with full risk management"
    version = "1.0.0"

    def execute(self, context: Dict[str, Any]) -> SkillResult:
        """
        Execute a trade.
        
        Context:
            setup: dict — trade setup from AnalyzeSkill (must have direction, symbol, entry_price, etc.)
            executor: OANDAExecutor instance
            risk_guardian: RiskGuardian instance
            journal: AgentJournal instance
            dry_run: bool — if True, simulate execution without placing order
            
        Returns:
            SkillResult with trade execution data and events.
        """
        start = time.time()
        err = self.validate_context(context, ["setup", "executor", "risk_guardian"])
        if err:
            return SkillResult(success=False, error=err)

        setup = context["setup"]
        executor = context["executor"]
        risk_guardian = context["risk_guardian"]
        journal = context.get("journal")
        dry_run = context.get("dry_run", False)
        events = []

        symbol = setup["symbol"]
        direction = setup["direction"]
        entry_price = setup["entry_price"]
        stop_loss = setup["stop_loss"]
        take_profit = setup.get("target_1", setup.get("take_profit", 0))
        confidence = setup.get("confidence", 0)
        model = setup.get("model", "unknown")

        # ─── RISK CHECK ──────────────────────────────────────────────────
        account_info = executor.get_account_info()
        if not account_info:
            return SkillResult(success=False, error="Could not get account info")

        balance = account_info.balance if hasattr(account_info, 'balance') else 10000.0

        # Position sizing
        pip_value = 0.01 if "JPY" in symbol.upper() else 0.0001
        if direction == "BUY":
            risk_pips = abs(entry_price - stop_loss) / pip_value
        else:
            risk_pips = abs(stop_loss - entry_price) / pip_value

        # Dynamic risk based on confidence
        if confidence >= 0.85:
            risk_percent = 2.5
        elif confidence >= 0.70:
            risk_percent = 2.0
        else:
            risk_percent = 1.5

        risk_amount = balance * (risk_percent / 100)

        pip_value_per_unit = 0.0001 if "JPY" not in symbol.upper() else 0.01
        if risk_pips > 0:
            units = int(risk_amount / (risk_pips * pip_value_per_unit))
            units = min(units, 500000)
            units = max(units, 1000)
        else:
            units = 10000

        # Risk guardian check
        can_trade, reason = risk_guardian.can_trade(
            symbol=symbol,
            risk_amount=risk_amount,
        )

        events.append(RiskEvent(
            event_type=EventType.RISK_CHECK,
            source="skill:execute",
            balance=balance,
            risk_amount=risk_amount,
            can_trade=can_trade,
            reason=reason or "Approved",
        ))

        if not can_trade:
            events.append(TradeEvent(
                event_type=EventType.TRADE_REJECTED,
                source="skill:execute",
                symbol=symbol,
                direction=direction,
                model=model,
            ))
            return SkillResult(
                success=False,
                error=f"Risk Guardian blocked: {reason}",
                events=events,
                execution_time_ms=(time.time() - start) * 1000,
            )

        # ─── DRY RUN ─────────────────────────────────────────────────────
        if dry_run:
            events.append(TradeEvent(
                event_type=EventType.TRADE_ENTRY,
                source="skill:execute",
                symbol=symbol,
                direction=direction,
                units=units,
                entry_price=entry_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                model=model,
                risk_amount=risk_amount,
            ))
            return SkillResult(
                success=True,
                data={
                    "dry_run": True,
                    "symbol": symbol,
                    "direction": direction,
                    "units": units,
                    "entry_price": entry_price,
                    "stop_loss": stop_loss,
                    "take_profit": take_profit,
                    "risk_amount": round(risk_amount, 2),
                    "risk_percent": risk_percent,
                    "model": model,
                },
                events=events,
                execution_time_ms=(time.time() - start) * 1000,
            )

        # ─── LIVE EXECUTION ──────────────────────────────────────────────
        if direction == "SELL":
            units = -abs(units)

        result = executor.place_market_order(
            instrument=symbol,
            units=units,
            stop_loss=stop_loss,
            take_profit=take_profit,
        )

        if result and "orderFillTransaction" in result:
            fill = result["orderFillTransaction"]
            trade_id = fill.get("tradeOpened", {}).get("tradeID", "")
            fill_price = float(fill.get("price", entry_price))

            events.append(TradeEvent(
                event_type=EventType.TRADE_ENTRY,
                source="skill:execute",
                trade_id=trade_id,
                symbol=symbol,
                direction=direction,
                units=abs(units),
                entry_price=fill_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                model=model,
                risk_amount=risk_amount,
            ))

            # Journal
            if journal:
                try:
                    from ict_agent.engine.killzone import KillzoneManager
                    kz_mgr = KillzoneManager()
                    kz = kz_mgr.get_current_killzone(datetime.now(NY_TZ))
                    session_name = kz.value if kz else ""

                    journal.record_entry(
                        symbol=symbol,
                        side=direction,
                        entry_price=fill_price,
                        stop_loss=stop_loss,
                        take_profit=take_profit,
                        units=abs(units),
                        trade_id=trade_id,
                        model=model,
                        timeframe=setup.get("timeframe", "M15"),
                        confluences=setup.get("confluences", []),
                        setup_description=setup.get("entry_reason", ""),
                        risk_amount=risk_amount,
                        risk_percent=risk_percent,
                        session=session_name,
                    )
                except Exception:
                    pass

            # Risk tracking
            risk_guardian.record_trade(
                trade_id=trade_id,
                symbol=symbol,
                side="long" if direction == "BUY" else "short",
                units=abs(units),
            )

            return SkillResult(
                success=True,
                data={
                    "trade_id": trade_id,
                    "symbol": symbol,
                    "direction": direction,
                    "fill_price": fill_price,
                    "units": abs(units),
                    "stop_loss": stop_loss,
                    "take_profit": take_profit,
                    "risk_amount": round(risk_amount, 2),
                    "model": model,
                },
                events=events,
                execution_time_ms=(time.time() - start) * 1000,
            )
        else:
            events.append(TradeEvent(
                event_type=EventType.TRADE_REJECTED,
                source="skill:execute",
                symbol=symbol,
                direction=direction,
                model=model,
            ))
            return SkillResult(
                success=False,
                error=f"Order failed: {result}",
                events=events,
                execution_time_ms=(time.time() - start) * 1000,
            )
