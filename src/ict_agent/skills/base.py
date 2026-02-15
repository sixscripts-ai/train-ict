"""
VEX Skill Base
==============
Abstract base class for all agent skills.
Each skill wraps an existing component and exposes a clean execute() interface.

Inspired by OpenHands microagent / agenthub pattern.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Type
from datetime import datetime
from zoneinfo import ZoneInfo

from ict_agent.events.event_types import VexEvent, EventType

NY_TZ = ZoneInfo("America/New_York")


@dataclass
class SkillResult:
    """Result from executing a skill."""
    success: bool
    data: Dict[str, Any] = field(default_factory=dict)
    events: List[VexEvent] = field(default_factory=list)
    error: str = ""
    execution_time_ms: float = 0.0

    def __bool__(self) -> bool:
        return self.success


class Skill(ABC):
    """
    Base class for all VEX skills.
    
    A skill is a discrete capability: scan, analyze, execute, learn, etc.
    Each skill:
    - Has a name and description
    - Takes context as input
    - Returns SkillResult with events
    - Is registered in the SkillRegistry
    """

    name: str = "base_skill"
    description: str = "Base skill — override this"
    version: str = "1.0.0"

    @abstractmethod
    def execute(self, context: Dict[str, Any]) -> SkillResult:
        """
        Execute the skill.
        
        Args:
            context: Dictionary with all needed data. Keys vary by skill.
        
        Returns:
            SkillResult with success status, data, and events to publish.
        """
        pass

    def validate_context(self, context: Dict[str, Any], required_keys: List[str]) -> Optional[str]:
        """Check that context has all required keys."""
        missing = [k for k in required_keys if k not in context]
        if missing:
            return f"{self.name} missing context keys: {', '.join(missing)}"
        return None

    def __repr__(self) -> str:
        return f"<Skill: {self.name} v{self.version}>"


class SkillRegistry:
    """
    Registry of all available skills.
    
    Skills are registered by name and can be retrieved dynamically.
    This enables hot-plugging new capabilities without changing the controller.
    """

    def __init__(self):
        self._skills: Dict[str, Skill] = {}

    def register(self, skill: Skill) -> None:
        """Register a skill instance."""
        self._skills[skill.name] = skill

    def get(self, name: str) -> Optional[Skill]:
        """Get a skill by name."""
        return self._skills.get(name)

    def has(self, name: str) -> bool:
        """Check if a skill is registered."""
        return name in self._skills

    def list_skills(self) -> List[str]:
        """List all registered skill names."""
        return list(self._skills.keys())

    def execute(self, name: str, context: Dict[str, Any]) -> SkillResult:
        """Execute a skill by name."""
        skill = self.get(name)
        if not skill:
            return SkillResult(success=False, error=f"Skill '{name}' not found")
        return skill.execute(context)

    def __len__(self) -> int:
        return len(self._skills)

    def __repr__(self) -> str:
        return f"<SkillRegistry: {len(self._skills)} skills — {', '.join(self._skills.keys())}>"
