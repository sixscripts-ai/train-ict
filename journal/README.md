# 📓 Trading Journal System

This journal system tracks **TWO separate accounts**:

---

## 👤 [Ashton's Journal](ashton/)
**Account:** FTMO ✅ FUNDED (Verification #2 Passed Jan 20, 2026)

- Pre-trade analysis & discussion with Vex
- Trade idea sheets
- Post-trade reviews
- Psychology breakdowns
- Lessons learned
- Video breakdowns

**Structure:**
```
ashton/
├── index.md              # Master trade log & stats
├── index.html            # Web dashboard
├── trades_database.json  # All trade records
├── pre_trade_scoring.md  # Trade scoring checklist
├── 2026/                 # Trade entries by date
│   └── 01/
│       ├── 2026-01-15_EURUSD_short/
│       ├── 2026-01-15_GBPUSD_short/
│       ├── 2026-01-16_EURUSD_short/
│       ├── 2026-01-16_GBPUSD_short/
│       └── 2026-01-20_session_review.md
└── videos/               # Trade video breakdowns
```

---

## 🤖 [Vex's Journal](vex/)
**Account:** OANDA Demo (Autonomous trading)

- Automated trade entries
- Model performance tracking
- Risk guardian logs
- System decisions

**Key Files:**
- `vex/YYYY-MM-DD.json` - Daily trade data

---

## 📋 Shared Resources

| Resource | Purpose |
|----------|---------|
| `templates/` | Trade entry, review, psychology templates |
| `lessons/` | Combined lessons (both accounts) |

---

## ⚠️ IMPORTANT: Keep These Separate!

- **Ashton's trades** = YOUR manual decisions on FTMO
- **Vex's trades** = VEX's autonomous decisions on OANDA Demo

**Do NOT mix stats or compare directly** - different accounts, different rules, different risk parameters.
