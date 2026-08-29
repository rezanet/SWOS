"""Autonomous SWOS reference runtime."""

from .models import ResearchRequest, RunOutcome
from .orchestrator import AutonomousSWOS

__all__ = ["AutonomousSWOS", "ResearchRequest", "RunOutcome"]
__version__ = "0.1.0"
