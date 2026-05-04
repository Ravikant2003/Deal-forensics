"""
Shared tools that allow agents to call other agents.
This avoids circular imports between agents and workflow.
"""

from graph.state import AgentState
from agents.timeline_agent import run_timeline_agent
from agents.comparative_agent import run_comparative_agent
from agents.playbook_agent import run_playbook_agent


def call_timeline_agent_tool(state: AgentState) -> dict:
    """Run the Timeline Agent to analyze deal timeline."""
    result = run_timeline_agent(state)
    return {
        "timeline_analysis": result.get("timeline_analysis"),
        "agent_trace": result.get("agent_trace", []),
        "messages": result.get("messages", []),
    }


def call_comparative_agent_tool(state: AgentState) -> dict:
    """Run the Comparative Agent to compare against won deals."""
    result = run_comparative_agent(state)
    return {
        "comparative_analysis": result.get("comparative_analysis"),
        "agent_trace": result.get("agent_trace", []),
        "messages": result.get("messages", []),
    }


def call_playbook_agent_tool(state: AgentState) -> dict:
    """Run the Playbook Agent to generate actionable recommendations."""
    result = run_playbook_agent(state)
    return {
        "playbook": result.get("playbook"),
        "agent_trace": result.get("agent_trace", []),
        "messages": result.get("messages", []),
    }
