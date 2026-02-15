#!/usr/bin/env python3
"""
Quick integration test — runs VexController.step() with killzone override
to test the full scan → analyze → gate → execute pipeline.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ict_agent.controller.agent_controller import VexController, VexConfig

config = VexConfig.from_env()
config.dry_run = True
config.verbose = True
config.symbols = ["EUR_USD", "GBP_USD"]
config.scan_interval_seconds = 1

controller = VexController(config=config)

if not controller.boot():
    print("Boot failed!")
    sys.exit(1)

print("\n" + "=" * 50)
print("OVERRIDE: Forcing killzone check to pass for testing")
print("=" * 50 + "\n")

# Save the original scan skill execute
original_scan = controller.skill_registry.get("scan")
from ict_agent.skills.base import SkillResult

class ForcedScanSkill:
    """Override scan to always report killzone active."""
    name = "scan"
    def execute(self, context):
        result = original_scan.execute(context)
        if result.success:
            result.data["is_primary_killzone"] = True
            result.data["killzone"] = "ny_am_test"
        return result

controller.skill_registry.register(ForcedScanSkill())

# Run one step
controller.step()

# Print status
import json
status = controller.get_status()
print("\n📊 Final Status:")
print(json.dumps(status, indent=2, default=str))

# Print events
if controller.event_stream:
    print(f"\n📡 Events recorded: {controller.event_stream.event_count}")
    for evt in controller.event_stream.get_events():
        print(f"   {evt}")
