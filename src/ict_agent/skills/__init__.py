"""VEX Skill System - Pluggable capabilities for the agent."""
from ict_agent.skills.base import Skill, SkillResult, SkillRegistry
from ict_agent.skills.scan_skill import ScanSkill
from ict_agent.skills.analyze_skill import AnalyzeSkill
from ict_agent.skills.execute_skill import ExecuteSkill
from ict_agent.skills.learn_skill import LearnSkill
from ict_agent.skills.news_skill import NewsSkill

__all__ = [
    "Skill",
    "SkillResult",
    "SkillRegistry",
    "ScanSkill",
    "AnalyzeSkill",
    "ExecuteSkill",
    "LearnSkill",
    "NewsSkill",
]
