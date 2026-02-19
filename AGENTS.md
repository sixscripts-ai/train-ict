# AGENTS.md — Multi-Agent Collaboration Rules
# ============================================================================
# This file is the single source of truth for ALL AI agents working on this
# project. Both agents (VS Code Copilot & Antigravity) MUST read and
# follow these rules.
#
# Last Updated: 2026-02-15
# Owner: Ashton (villain)
# ============================================================================

## 🏗️ Project Overview

**Project:** VEX — An autonomous AI trading agent implementing ICT (Inner Circle
Trader) methodology for algorithmic forex trading.

**Goal:** 60%+ win rate, 3:1+ RR, fully autonomous ICT-based trading.

**The Human:** Ashton (GitHub: sixscripts-ai, local user: villain)

---

## 📁 Repository Map

### Primary Repo (GitHub — DO NOT BREAK)
- **URL:** `https://github.com/sixscripts-ai/train-ict`
- **Local Clone:** `/Users/villain/Documents/train-ict`
- **Purpose:** The powerhouse. Core ICT agent code, knowledge base, training data.
- **Branch Policy:** Direct modifications to main are allowed. Agents may commit and push to main.

### Local Development (Antigravity workspace)
- **Path:** `/Users/villain/Documents/trae_projects/vexbrain/Antigravity`
- **Purpose:** ICT research, journal entries, SOLO configs, analysis scripts, learning data.
- **NOT a git repo** — data syncs to train-ict via the bridge script.

### Unified Workspace (Bridge)
- **Path:** `/Users/villain/Documents/vex-workspace`
- **Purpose:** Symlinked workspace that connects both repos for easy access.
- **Sync Script:** `./sync_bridge.sh` (run `full`, `data`, `journal`, `status`, `pull`)

---

## 🚨 Critical Rules (ALL AGENTS)

### 1. Direct main branch modifications ARE allowed
- Agents may commit and push directly to main
- Feature branches are optional, not required
- Follow the `.agent/rules.md` in train-ict for general guidelines

### 2. The Brain is VexBrainV2
- `src/ict_agent/vex_brain.py` (V2 in local) is THE brain
- Do NOT create new brain files — improve the existing one
- Any changes to the brain must include backtest validation

### 3. Data Flow Direction
```
Local Antigravity (trae_projects)
        ↓  (one-way sync via bridge)
train-ict clone (/Documents/train-ict)
        ↓  (manual push only)
GitHub (sixscripts-ai/train-ict)
```

### 4. Never Commit These
- `.env` files (API keys)
- `venv/` directories
- `.DS_Store`
- Raw chat exports (>100MB)
- Personal credentials

### 5. Always Preserve the Learning System
- `data/learning/` contains learned patterns — NEVER overwrite, only append
- `knowledge_base/` is the ICT reference — add to it, don't restructure
- `journal/` entries must follow templates in `journal/templates/`

---

## 🤖 Agent Roles (Two-Agent Setup)

### VS Code Copilot (GitHub Copilot in VS Code)
- **Primary Role:** Code editing, refactoring, debugging, git operations
- **Has Access To:** GitHub MCP, Docker MCP, terminal, file system
- **Strengths:** Multi-file edits, code generation, running tests, Docker
- **Should Do:** Code changes, PR creation, running backtests, Docker setup
- **Owns:** `train-ict` repo (code + git)

### Antigravity (BS Code / Docker)
- **Primary Role:** Deep analysis, research, knowledge base expansion
- **Has Access To:** Local Antigravity workspace, SOLO configs, Docker-mounted `~/Documents`
- **Strengths:** Deep analysis, concept mapping, self-training configuration
- **Should Do:** ICT concept research, knowledge base updates, journal entries, SOLO system refinement, analysis scripts
- **Owns:** `trae_projects/vexbrain/Antigravity` (research + data)

---

## 🔄 Sync Workflow

### Antigravity → train-ict (research to code):
1. Make changes in `/Users/villain/Documents/trae_projects/vexbrain/Antigravity/`
2. Run bridge: `~/Documents/vex-workspace/sync_bridge.sh data`
3. Changes appear in the train-ict clone (not pushed)
4. Notify Copilot that new data is ready

### VS Code Copilot (code + git):
1. Open `/Users/villain/Documents/train-ict` as workspace
2. Pull latest: `git pull origin main`
3. Make changes, commit, and push directly to main
4. Feature branches are optional for larger refactors

### Syncing between agents:
1. **Copilot → Antigravity:** Push to GitHub, Antigravity runs `sync_bridge.sh pull`
2. **Antigravity → Copilot:** Run `sync_bridge.sh data`, Copilot reads from clone
3. **Before any session:** Run `sync_bridge.sh status` to verify links

---

## 🧠 ICT Methodology Quick Reference

All agents must understand these core concepts:

| Concept | What It Means |
|---------|--------------|
| **FVG** | Fair Value Gap — imbalance to fill |
| **OB** | Order Block — institutional entry zone |
| **BOS** | Break of Structure — trend continuation |
| **CHoCH** | Change of Character — trend reversal |
| **BSL/SSL** | Buy/Sell Side Liquidity — stop hunt targets |
| **Killzone** | High-probability time windows (London, NY AM, NY PM) |
| **OTE** | Optimal Trade Entry — 62-79% Fibonacci |
| **AMD** | Accumulation → Manipulation → Distribution |
| **Silver Bullet** | FVG in specific 1-hour windows |
| **Judas Swing** | False breakout before real move |

**Study Materials:** `knowledge_base/ICT_MASTER_LIBRARY.md`

---

## 📊 Key Files

| File | Purpose |
|------|---------|
| `src/ict_agent/vex_brain.py` | Main decision engine |
| `src/ict_agent/detectors/` | ICT pattern detection modules |
| `src/ict_agent/models/` | Trading model implementations |
| `src/ict_agent/execution/` | Broker API integration (OANDA) |
| `src/ict_agent/learning/` | Self-improvement system |
| `knowledge_base/ICT_MASTER_LIBRARY.md` | Complete ICT reference |
| `journal/` | Trade journal entries |
| `config/` | Agent configuration |
| `scripts/` | Runnable scripts (backtest, analysis, trading) |
| `vex.py` | Standalone VEX runner |
| `SOLO/` | Self-training configuration (local only) |

---

## 🐳 Docker (Optional)

For consistent environments across agents:
```bash
# From vex-workspace:
docker compose up -d   # Start environment
docker compose exec vex bash  # Enter container
```

---

## 💬 Communication Protocol

When agents need to communicate state:
1. **Use GitHub Issues** for tasks and bugs (Copilot creates, Antigravity references)
2. **Use commit messages** to describe what was done
3. **Update this AGENTS.md** when roles or rules change
4. **Run `sync_bridge.sh status`** before starting any session
5. **Ashton relays** context between agents when switching IDEs

---

*"Trade like the institutions. Hunt the liquidity. Respect the algorithm."*
*— VEX*
