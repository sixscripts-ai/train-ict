#!/usr/bin/env python3
"""
VEX Diagnostic Report
=====================
Full system health snapshot.

Shows:
  - Component status (all 13+ subsystems)
  - Memory stats (short-term, long-term, recall)
  - Performance metrics (win rate, P&L, drawdown)
  - Knowledge graph stats
  - Strategy evaluation
  - Event stream health
  - OANDA connection status
  - Risk guardian state
  - Configuration dump

Usage:
    PYTHONPATH=src python3 scripts/diagnostic_report.py
    PYTHONPATH=src python3 scripts/diagnostic_report.py --json
    PYTHONPATH=src python3 scripts/diagnostic_report.py --section memory
"""

import argparse
import json
import os
import sys
import traceback
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

NY_TZ = ZoneInfo("America/New_York")
PROJECT_ROOT = Path(__file__).parent.parent


def header(title: str) -> str:
    return f"\n{'═' * 62}\n  {title}\n{'═' * 62}"


def subheader(title: str) -> str:
    return f"\n  {'─' * 40}\n  {title}\n  {'─' * 40}"


def load_env():
    """Load .env file."""
    env_paths = [
        PROJECT_ROOT / ".env",
        Path.home() / "Documents" / "trae_projects" / "vexbrain" / "Antigravity" / ".env",
    ]
    for p in env_paths:
        if p.exists():
            for line in open(p):
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ[k.strip()] = v.strip()
            return True
    return False


def check_component(name: str, factory, verbose=True):
    """Try to initialize a component and return its status."""
    try:
        obj = factory()
        status = "✅"
        detail = ""
        if hasattr(obj, "__len__"):
            detail = f"({len(obj)} items)"
        return {"name": name, "status": "ok", "icon": status, "detail": detail, "obj": obj}
    except Exception as e:
        if verbose:
            traceback.print_exc()
        return {"name": name, "status": "error", "icon": "❌", "detail": str(e), "obj": None}


def run_diagnostic(sections=None, output_json=False, verbose=True):
    """Run full diagnostic report."""
    now = datetime.now(NY_TZ)
    report = {
        "timestamp": now.isoformat(),
        "timestamp_human": now.strftime("%Y-%m-%d %H:%M:%S ET"),
        "components": {},
        "sections": {},
    }

    if not output_json:
        print(header("🔧 VEX DIAGNOSTIC REPORT"))
        print(f"  Time: {now.strftime('%Y-%m-%d %H:%M:%S ET')}")
        print(f"  Python: {sys.version.split()[0]}")
        print(f"  Root: {PROJECT_ROOT}")

    # ─── Environment ──────────────────────────────────────────────────────
    load_env()
    api_key = os.getenv("OANDA_API_KEY", "")
    account_id = os.getenv("OANDA_ACCOUNT_ID", "")
    env = os.getenv("OANDA_ENV", "practice")

    report["sections"]["environment"] = {
        "api_key_set": bool(api_key),
        "api_key_preview": f"...{api_key[-8:]}" if len(api_key) > 8 else "(not set)",
        "account_id": account_id or "(not set)",
        "environment": env,
    }

    if not output_json and (not sections or "environment" in sections):
        print(subheader("Environment"))
        print(f"    API Key:    {'✅ Set' if api_key else '❌ Missing'} ({report['sections']['environment']['api_key_preview']})")
        print(f"    Account:    {account_id or '❌ Missing'}")
        print(f"    Env:        {env}")

    # ─── Components ───────────────────────────────────────────────────────
    if not sections or "components" in sections:
        if not output_json:
            print(subheader("Component Health"))

        components = []

        # EventStream
        c = check_component("EventStream", lambda: __import__(
            "ict_agent.events.event_stream", fromlist=["EventStream"]
        ).EventStream(log_dir=PROJECT_ROOT / "data" / "events"), verbose)
        components.append(c)

        # OANDAExecutor
        if api_key and account_id:
            c = check_component("OANDAExecutor", lambda: __import__(
                "ict_agent.execution.oanda_executor", fromlist=["OANDAExecutor"]
            ).OANDAExecutor(api_key=api_key, account_id=account_id, environment=env), verbose)
            components.append(c)
        else:
            components.append({"name": "OANDAExecutor", "status": "skip", "icon": "⚠️",
                               "detail": "No credentials", "obj": None})

        # RiskGuardian
        executor_obj = next((c["obj"] for c in components if c["name"] == "OANDAExecutor" and c["obj"]), None)
        if executor_obj:
            c = check_component("RiskGuardian", lambda: __import__(
                "ict_agent.execution.risk_guardian", fromlist=["RiskGuardian", "RiskConfig"]
            ).RiskGuardian(executor=executor_obj), verbose)
            components.append(c)
        else:
            components.append({"name": "RiskGuardian", "status": "skip", "icon": "⚠️",
                               "detail": "No executor", "obj": None})

        # VexCoreEngine
        c = check_component("VexCoreEngine", lambda: __import__(
            "ict_agent.core.vex_core_engine", fromlist=["VexCoreEngine"]
        ).VexCoreEngine(), verbose)
        components.append(c)

        # KnowledgeManager
        c = check_component("KnowledgeManager", lambda: __import__(
            "ict_agent.learning.knowledge_manager", fromlist=["KnowledgeManager"]
        ).KnowledgeManager(), verbose)
        components.append(c)
        km_obj = c["obj"]

        # KillzoneManager
        c = check_component("KillzoneManager", lambda: __import__(
            "ict_agent.engine.killzone", fromlist=["KillzoneManager"]
        ).KillzoneManager(), verbose)
        components.append(c)
        kz_obj = c["obj"]

        # TradeLearner
        c = check_component("TradeLearner", lambda: __import__(
            "ict_agent.learning.trade_learner", fromlist=["TradeLearner"]
        ).TradeLearner(data_dir=PROJECT_ROOT / "data" / "learning"), verbose)
        components.append(c)
        learner_obj = c["obj"]

        # NewsFilter
        c = check_component("NewsFilter", lambda: __import__(
            "ict_agent.engine.news_filter", fromlist=["NewsFilter"]
        ).NewsFilter(), verbose)
        components.append(c)

        # SkillRegistry
        def build_skills():
            from ict_agent.skills.base import SkillRegistry
            from ict_agent.skills.scan_skill import ScanSkill
            from ict_agent.skills.analyze_skill import AnalyzeSkill
            from ict_agent.skills.execute_skill import ExecuteSkill
            from ict_agent.skills.learn_skill import LearnSkill
            from ict_agent.skills.news_skill import NewsSkill
            from ict_agent.skills.strategy_skill import StrategySkill
            reg = SkillRegistry()
            for s in [ScanSkill(), AnalyzeSkill(), ExecuteSkill(), LearnSkill(), NewsSkill(), StrategySkill()]:
                reg.register(s)
            return reg
        c = check_component("SkillRegistry", build_skills, verbose)
        components.append(c)

        # MemoryManager
        c = check_component("MemoryManager", lambda: __import__(
            "ict_agent.memory.memory_manager", fromlist=["MemoryManager"]
        ).MemoryManager(data_dir=PROJECT_ROOT / "data" / "learning"), verbose)
        components.append(c)
        mem_obj = c["obj"]

        # PerformanceTracker
        c = check_component("PerformanceTracker", lambda: __import__(
            "ict_agent.memory.performance", fromlist=["PerformanceTracker"]
        ).PerformanceTracker(starting_balance=10000.0), verbose)
        components.append(c)

        for c in components:
            report["components"][c["name"]] = {"status": c["status"], "detail": c["detail"]}
            if not output_json:
                print(f"    {c['icon']} {c['name']:20s} {c['detail']}")

        ok = sum(1 for c in components if c["status"] == "ok")
        total = len(components)
        if not output_json:
            print(f"\n    Health: {ok}/{total} components online")

    # ─── OANDA Connection ─────────────────────────────────────────────────
    if not sections or "oanda" in sections:
        if not output_json:
            print(subheader("OANDA Connection"))

        oanda_status = {"connected": False}
        if executor_obj:
            try:
                account = executor_obj.get_account_info()
                if account:
                    bal = account.balance if hasattr(account, "balance") else 0
                    nav = account.nav if hasattr(account, "nav") else 0
                    margin = account.margin_used if hasattr(account, "margin_used") else 0
                    oanda_status = {
                        "connected": True,
                        "balance": bal,
                        "nav": nav,
                        "margin_used": margin,
                        "open_trades": account.open_trades if hasattr(account, "open_trades") else 0,
                    }
                    if not output_json:
                        print(f"    Balance:      ${bal:,.2f}")
                        print(f"    NAV:          ${nav:,.2f}")
                        print(f"    Margin Used:  ${margin:,.2f}")
                        print(f"    Open Trades:  {oanda_status['open_trades']}")
            except Exception as e:
                oanda_status["error"] = str(e)
                if not output_json:
                    print(f"    ❌ Connection error: {e}")
        else:
            if not output_json:
                print("    ⚠️ No executor available")

        report["sections"]["oanda"] = oanda_status

    # ─── Killzone ─────────────────────────────────────────────────────────
    if not sections or "killzone" in sections:
        if not output_json:
            print(subheader("Killzone Status"))
        kz_status = {}
        if kz_obj:
            try:
                current = kz_obj.get_current_killzone(now)
                is_primary = kz_obj.is_primary_killzone(now) if hasattr(kz_obj, "is_primary_killzone") else False
                kz_status = {
                    "current": current.value if current else "none",
                    "is_primary": is_primary,
                    "time": now.strftime("%H:%M ET"),
                }
                if not output_json:
                    icon = "🟢" if is_primary else "⚪"
                    print(f"    {icon} Current: {kz_status['current']} (primary: {is_primary})")
                    print(f"    Time: {kz_status['time']}")
            except Exception as e:
                kz_status["error"] = str(e)
                if not output_json:
                    print(f"    ❌ Error: {e}")
        report["sections"]["killzone"] = kz_status

    # ─── Memory ───────────────────────────────────────────────────────────
    if not sections or "memory" in sections:
        if not output_json:
            print(subheader("Memory System"))

        mem_status = {}
        if mem_obj:
            try:
                boot_info = mem_obj.boot()
                full_status = mem_obj.get_status()
                mem_status = full_status
                if not output_json:
                    st = full_status.get("short_term", {})
                    lt = full_status.get("long_term", {})
                    kn = full_status.get("knowledge", {})
                    print(f"    Short-Term:")
                    print(f"      Trades: {st.get('trades', 0)} | Signals: {st.get('signals', 0)} | Events: {st.get('events', 0)}")
                    print(f"    Long-Term:")
                    print(f"      Lessons: {lt.get('trade_lessons', 0)} | Patterns: {lt.get('patterns_tracked', 0)}")
                    print(f"      Golden Rules: {lt.get('golden_rules', 0)} | Concepts: {lt.get('concepts_learned', 0)}")
                    print(f"      Insights: {lt.get('insight_categories', 0)} categories")
                    print(f"      Pairs: {lt.get('pairs_with_memory', [])} | Models: {lt.get('models_with_memory', [])}")
                    print(f"    Knowledge Recall:")
                    print(f"      Files: {kn.get('files', 0)} | Names: {kn.get('names', [])}")
            except Exception as e:
                mem_status["error"] = str(e)
                if not output_json:
                    print(f"    ❌ Error: {e}")
        else:
            if not output_json:
                print("    ⚠️ MemoryManager not available")

        report["sections"]["memory"] = mem_status

    # ─── Knowledge Graph ──────────────────────────────────────────────────
    if not sections or "knowledge" in sections:
        if not output_json:
            print(subheader("Knowledge Graph"))

        kg_status = {}
        if km_obj:
            try:
                concepts = len(km_obj.concepts) if hasattr(km_obj, "concepts") else 0
                models = len(km_obj.models) if hasattr(km_obj, "models") else 0
                relationships = len(km_obj.relationships) if hasattr(km_obj, "relationships") else 0
                learned = len(km_obj.learned_combos) if hasattr(km_obj, "learned_combos") else 0
                kg_status = {
                    "concepts": concepts,
                    "models": models,
                    "relationships": relationships,
                    "learned_combos": learned,
                }
                if not output_json:
                    print(f"    Concepts:       {concepts}")
                    print(f"    Models:         {models}")
                    print(f"    Relationships:  {relationships}")
                    print(f"    Learned Combos: {learned}")

                    if hasattr(km_obj, "models"):
                        print(f"    Model Names:    {list(km_obj.models.keys())}")
            except Exception as e:
                kg_status["error"] = str(e)
                if not output_json:
                    print(f"    ❌ Error: {e}")
        else:
            if not output_json:
                print("    ⚠️ KnowledgeManager not available")

        report["sections"]["knowledge"] = kg_status

    # ─── Learning Data ────────────────────────────────────────────────────
    if not sections or "learning" in sections:
        if not output_json:
            print(subheader("Learning Data"))

        learning_dir = PROJECT_ROOT / "data" / "learning"
        learning_status = {"path": str(learning_dir), "files": {}}

        if learning_dir.exists():
            for f in sorted(learning_dir.glob("*.json")):
                try:
                    data = json.loads(f.read_text())
                    size = f.stat().st_size
                    if isinstance(data, list):
                        count = len(data)
                        dtype = "list"
                    elif isinstance(data, dict):
                        count = len(data)
                        dtype = "dict"
                    else:
                        count = 1
                        dtype = type(data).__name__
                    learning_status["files"][f.name] = {
                        "type": dtype, "count": count, "size_bytes": size,
                    }
                    if not output_json:
                        print(f"    {f.name:35s} {dtype:6s} {count:4d} items  {size:,d} bytes")
                except Exception as e:
                    learning_status["files"][f.name] = {"error": str(e)}
                    if not output_json:
                        print(f"    {f.name:35s} ❌ {e}")
        else:
            if not output_json:
                print(f"    ⚠️ Learning dir not found: {learning_dir}")

        report["sections"]["learning"] = learning_status

    # ─── Event Log ────────────────────────────────────────────────────────
    if not sections or "events" in sections:
        if not output_json:
            print(subheader("Event Logs"))

        events_dir = PROJECT_ROOT / "data" / "events"
        events_status = {"path": str(events_dir), "files": []}

        if events_dir.exists():
            for f in sorted(events_dir.glob("*.jsonl"))[-5:]:  # Last 5 logs
                lines = sum(1 for _ in open(f))
                size = f.stat().st_size
                events_status["files"].append({
                    "name": f.name, "events": lines, "size_bytes": size,
                })
                if not output_json:
                    print(f"    {f.name:45s} {lines:4d} events  {size:,d} bytes")
        else:
            if not output_json:
                print(f"    ⚠️ Events dir not found: {events_dir}")

        report["sections"]["events"] = events_status

    # ─── Data Files ───────────────────────────────────────────────────────
    if not sections or "data" in sections:
        if not output_json:
            print(subheader("Data Files"))

        vex_memory_dir = PROJECT_ROOT / "data" / "vex_memory"
        data_status = {}

        if vex_memory_dir.exists():
            files = list(vex_memory_dir.glob("*.json"))
            data_status["vex_memory_files"] = len(files)
            if not output_json:
                print(f"    Knowledge files: {len(files)}")
                for f in sorted(files):
                    size = f.stat().st_size
                    print(f"      {f.stem:40s} {size:,d} bytes")

        kb_dir = PROJECT_ROOT / "knowledge_base"
        if kb_dir.exists():
            yaml_files = list(kb_dir.glob("**/*.yaml")) + list(kb_dir.glob("**/*.yml"))
            md_files = list(kb_dir.glob("**/*.md"))
            data_status["kb_yaml_files"] = len(yaml_files)
            data_status["kb_md_files"] = len(md_files)
            if not output_json:
                print(f"    Knowledge base: {len(yaml_files)} YAML, {len(md_files)} MD")
                for f in sorted(yaml_files + md_files):
                    rel = f.relative_to(kb_dir)
                    print(f"      {str(rel):40s} {f.stat().st_size:,d} bytes")

        report["sections"]["data"] = data_status

    # ─── TradeLearner Stats ───────────────────────────────────────────────
    if not sections or "learner" in sections:
        if not output_json:
            print(subheader("TradeLearner"))

        learner_status = {}
        if learner_obj:
            try:
                lessons = len(learner_obj.lessons) if hasattr(learner_obj, "lessons") else 0
                patterns = len(learner_obj.patterns) if hasattr(learner_obj, "patterns") else 0
                learner_status = {"lessons": lessons, "patterns": patterns}
                if not output_json:
                    print(f"    Lessons:  {lessons}")
                    print(f"    Patterns: {patterns}")
                    if hasattr(learner_obj, "patterns") and learner_obj.patterns:
                        for name, p in learner_obj.patterns.items():
                            wr = round(p.win_rate * 100, 1) if hasattr(p, "win_rate") else 0
                            total = p.total_trades if hasattr(p, "total_trades") else 0
                            print(f"      {name:35s} {total:3d} trades  {wr}% WR")
            except Exception as e:
                learner_status["error"] = str(e)
                if not output_json:
                    print(f"    ❌ Error: {e}")
        else:
            if not output_json:
                print("    ⚠️ TradeLearner not available")

        report["sections"]["learner"] = learner_status

    # ─── Git Status ───────────────────────────────────────────────────────
    if not sections or "git" in sections:
        if not output_json:
            print(subheader("Git Status"))

        import subprocess
        git_status = {}
        try:
            result = subprocess.run(
                ["git", "log", "--oneline", "-5"],
                capture_output=True, text=True, cwd=PROJECT_ROOT,
            )
            commits = result.stdout.strip().split("\n") if result.stdout else []
            git_status["recent_commits"] = commits

            result2 = subprocess.run(
                ["git", "status", "--short"],
                capture_output=True, text=True, cwd=PROJECT_ROOT,
            )
            changes = result2.stdout.strip().split("\n") if result2.stdout.strip() else []
            git_status["uncommitted_changes"] = len(changes)

            result3 = subprocess.run(
                ["git", "branch", "--show-current"],
                capture_output=True, text=True, cwd=PROJECT_ROOT,
            )
            git_status["branch"] = result3.stdout.strip()

            if not output_json:
                print(f"    Branch: {git_status['branch']}")
                print(f"    Uncommitted: {len(changes)} files")
                print(f"    Recent commits:")
                for c in commits:
                    print(f"      {c}")
        except Exception as e:
            git_status["error"] = str(e)
            if not output_json:
                print(f"    ❌ Error: {e}")

        report["sections"]["git"] = git_status

    # ─── Summary ──────────────────────────────────────────────────────────
    if not output_json:
        print(header("📋 SUMMARY"))
        ok = sum(1 for c in report["components"].values() if c["status"] == "ok")
        total = len(report["components"])
        errors = sum(1 for c in report["components"].values() if c["status"] == "error")
        print(f"    Components: {ok}/{total} online ({errors} errors)")

        oanda = report["sections"].get("oanda", {})
        if oanda.get("connected"):
            print(f"    OANDA: Connected (${oanda['balance']:,.2f})")
        else:
            print(f"    OANDA: Not connected")

        mem = report["sections"].get("memory", {})
        lt = mem.get("long_term", {})
        kn = mem.get("knowledge", {})
        print(f"    Memory: {lt.get('golden_rules', 0)} rules, {lt.get('patterns_tracked', 0)} patterns, {kn.get('files', 0)} knowledge files")

        kg = report["sections"].get("knowledge", {})
        print(f"    Knowledge: {kg.get('concepts', 0)} concepts, {kg.get('models', 0)} models")

        git = report["sections"].get("git", {})
        print(f"    Git: {git.get('branch', '?')} ({git.get('uncommitted_changes', '?')} uncommitted)")
        print()

    if output_json:
        # Remove non-serializable objects
        for c in report.get("components", {}).values():
            c.pop("obj", None)
        print(json.dumps(report, indent=2, default=str))

    return report


def main():
    parser = argparse.ArgumentParser(description="VEX Diagnostic Report")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--section", type=str, help="Only show specific section")
    parser.add_argument("--quiet", action="store_true", help="Suppress tracebacks")
    args = parser.parse_args()

    sections = [args.section] if args.section else None
    run_diagnostic(sections=sections, output_json=args.json, verbose=not args.quiet)


if __name__ == "__main__":
    main()
