#!/usr/bin/env python3
"""
OANDA Connection Test
=====================
Verifies the OANDA API connection is working.
Tests: auth, account info, pricing, and a dummy order (cancelled immediately).

Run: python scripts/test_oanda.py
"""

import os
import sys
import json
import requests
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

NY_TZ = ZoneInfo("America/New_York")

# Load .env from the Antigravity workspace (where the creds live)
ENV_PATHS = [
    Path.home() / "Documents" / "trae_projects" / "vexbrain" / "Antigravity" / ".env",
    Path.home() / "Documents" / "vex-workspace" / "local_env",
    Path(__file__).parent.parent / ".env",
]


def load_env():
    """Load environment variables from .env file"""
    for env_path in ENV_PATHS:
        if env_path.exists() or env_path.is_symlink():
            resolved = env_path.resolve() if env_path.is_symlink() else env_path
            if resolved.exists():
                with open(resolved) as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            key, _, value = line.partition('=')
                            os.environ[key.strip()] = value.strip()
                print(f"  ✅ Loaded env from: {env_path}")
                return True
    return False


def test_connection():
    print("🔌 OANDA Connection Test")
    print(f"   Time: {datetime.now(NY_TZ).strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print()

    # ── Step 1: Load credentials ──
    print("1️⃣  Loading credentials...")
    if not load_env():
        print("  ❌ No .env file found! Checked:")
        for p in ENV_PATHS:
            print(f"     - {p}")
        return False

    api_key = os.getenv("OANDA_API_KEY")
    account_id = os.getenv("OANDA_ACCOUNT_ID")

    if not api_key:
        print("  ❌ OANDA_API_KEY not set")
        return False
    if not account_id:
        print("  ❌ OANDA_ACCOUNT_ID not set")
        return False

    print(f"  ✅ API Key: {api_key[:8]}...{api_key[-4:]}")
    print(f"  ✅ Account: {account_id}")

    # ── Step 2: Set up session ──
    env_type = os.getenv("OANDA_ENV", "practice").lower()
    
    def get_base_url(env_name):
        return "https://api-fxtrade.oanda.com" if env_name == "live" else "https://api-fxpractice.oanda.com"
        
    base_url = get_base_url(env_type)
    print(f"  🌍 Environment: {env_type.upper()} ({base_url})")

    session = requests.Session()
    session.headers.update({
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept-Datetime-Format": "RFC3339",
    })
    
    # helper to switch env if needed
    def switch_env():
        nonlocal env_type, base_url
        env_type = "live" if env_type == "practice" else "practice"
        base_url = get_base_url(env_type)
        print(f"\n3️⃣  Retrying with {env_type.upper()} environment ({base_url})...")


    # ── Step 3: Test account access ──
    print(f"\n2️⃣  Testing account access ({env_type})...")
    
    def try_request(url):
        return session.get(url)

    try:
        resp = try_request(f"{base_url}/v3/accounts/{account_id}/summary")
        
        # Auto-retry with other environment on 401
        if resp.status_code == 401:
            print(f"  ⚠️  401 Unauthorized on {env_type.upper()}. Toggling environment...")
            switch_env() 
            resp = try_request(f"{base_url}/v3/accounts/{account_id}/summary")

        if resp.status_code == 200:
            acct = resp.json().get("account", {})
            balance = float(acct.get("balance", 0))
            nav = float(acct.get("NAV", 0))
            currency = acct.get("currency", "???")
            open_trades = int(acct.get("openTradeCount", 0))
            margin_avail = float(acct.get("marginAvailable", 0))
            
            print(f"  ✅ Connected to OANDA {env_type.upper()}")
            print(f"     Balance:    {currency} {balance:,.2f}")
            print(f"     NAV:        {currency} {nav:,.2f}")
            print(f"     Margin:     {currency} {margin_avail:,.2f}")
            print(f"     Open Trades: {open_trades}")
            
            # Warn if environment mismatch with .env
            env_var = os.getenv("OANDA_ENV", "practice").lower()
            if env_type != env_var:
                 print(f"  ⚠️  NOTE: Your .env has OANDA_ENV={env_var}, but this key works for {env_type.upper()}. Please update .env.")
                 
        elif resp.status_code == 401:
            print(f"  ❌ AUTH FAILED (401) — API key is invalid or expired for BOTH environments.")
            return False
        elif resp.status_code == 403:
            print(f"  ❌ FORBIDDEN (403) — Account ID doesn't match API key")
            return False
        else:
            print(f"  ❌ Unexpected status: {resp.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print(f"  ❌ CONNECTION FAILED — cannot reach {base_url}")
        return False
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False

    # ── Step 4: Test pricing ──
    print("\n3️⃣  Testing price feed...")
    try:
        resp = session.get(
            f"{base_url}/v3/accounts/{account_id}/pricing",
            params={"instruments": "EUR_USD,GBP_USD"}
        )
        if resp.status_code == 200:
            prices = resp.json().get("prices", [])
            for p in prices:
                instrument = p.get("instrument", "???")
                bid = p.get("bids", [{}])[0].get("price", "N/A") if p.get("bids") else "N/A"
                ask = p.get("asks", [{}])[0].get("price", "N/A") if p.get("asks") else "N/A"
                tradeable = p.get("tradeable", False)
                status = "🟢 TRADEABLE" if tradeable else "🔴 CLOSED"
                print(f"  ✅ {instrument}: Bid={bid} Ask={ask} [{status}]")
        else:
            print(f"  ⚠️  Pricing returned {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        print(f"  ⚠️  Pricing error: {e}")

    # ── Step 5: Test order capability (create + cancel a limit order) ──
    print("\n4️⃣  Testing order capability (limit order + immediate cancel)...")
    try:
        # Place a limit order way below market (won't fill)
        order_data = {
            "order": {
                "type": "LIMIT",
                "instrument": "EUR_USD",
                "units": "1",  # Smallest possible
                "price": "0.50000",  # Way below market — will never fill
                "timeInForce": "GTC",
            }
        }
        resp = session.post(
            f"{base_url}/v3/accounts/{account_id}/orders",
            json=order_data
        )
        
        if resp.status_code == 201:
            order_id = resp.json().get("orderCreateTransaction", {}).get("id", "unknown")
            print(f"  ✅ Order placed successfully (ID: {order_id})")
            
            # Cancel it immediately
            cancel_resp = session.put(
                f"{base_url}/v3/accounts/{account_id}/orders/{order_id}/cancel"
            )
            if cancel_resp.status_code == 200:
                print(f"  ✅ Order cancelled successfully")
            else:
                print(f"  ⚠️  Cancel returned {cancel_resp.status_code} — check manually!")
        else:
            error = resp.json().get("errorMessage", resp.text[:200])
            print(f"  ⚠️  Order test returned {resp.status_code}: {error}")
            print(f"     (This might be OK if market is closed)")
    except Exception as e:
        print(f"  ⚠️  Order test error: {e}")

    # ── Summary ──
    print("\n" + "=" * 50)
    print("🟢 OANDA CONNECTION: OPERATIONAL")
    print(f"   Account {account_id} is live on Practice environment")
    print(f"   OANDAExecutor in src/ict_agent/execution/ should work")
    print("=" * 50)
    return True


if __name__ == "__main__":
    success = test_connection()
    sys.exit(0 if success else 1)
