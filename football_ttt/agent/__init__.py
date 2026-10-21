"""Агент, который решает, засчитать ли названного футболиста."""

from football_ttt.agent.agent import Verdict, verify_answer
from football_ttt.agent.errors import AgentError

__all__ = ["AgentError", "Verdict", "verify_answer"]
