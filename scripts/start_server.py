#!/usr/bin/env python3
"""
ICT Knowledge Engine — Server Launcher
=======================================

Usage:
    python scripts/start_server.py              # Production
    python scripts/start_server.py --dev        # Development (auto-reload)
    python scripts/start_server.py --port 9000  # Custom port

Alternative:
    uvicorn ict_agent.api.app:app --reload --port 8000
"""

import argparse
import os
import sys
from pathlib import Path

# Ensure project root is in path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))
os.chdir(PROJECT_ROOT)

# Load .env if present
env_file = PROJECT_ROOT / ".env"
if env_file.exists():
    from dotenv import load_dotenv
    load_dotenv(env_file)
    print(f"Loaded env from {env_file}")


def main():
    parser = argparse.ArgumentParser(description="ICT Knowledge Engine Server")
    parser.add_argument("--host", default="0.0.0.0", help="Bind host")
    parser.add_argument("--port", type=int, default=8000, help="Bind port")
    parser.add_argument("--dev", action="store_true", help="Development mode (auto-reload)")
    parser.add_argument("--workers", type=int, default=1, help="Number of workers")
    args = parser.parse_args()

    import uvicorn

    print(f"""
╔══════════════════════════════════════════════════════════╗
║  ICT Knowledge Engine — VEX Backend                     ║
║  {'Development' if args.dev else 'Production':20s} Mode                          ║
║  http://{args.host}:{args.port:<5d}                                ║
║  Docs: http://localhost:{args.port}/docs                       ║
║  Dashboard: http://localhost:{args.port}/hub/dashboard.html    ║
╚══════════════════════════════════════════════════════════╝
""")

    uvicorn.run(
        "ict_agent.api.app:app",
        host=args.host,
        port=args.port,
        reload=args.dev,
        workers=args.workers if not args.dev else 1,
        log_level="info" if not args.dev else "debug",
    )


if __name__ == "__main__":
    main()
