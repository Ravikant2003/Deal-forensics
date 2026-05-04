"""
Shared state definition for the LangGraph multi-agent workflow.
"""

from typing import Annotated, Optional
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    """
    Shared state that flows through all nodes in the LangGraph StateGraph.

    Fields:
        messages:             Full conversation + tool call history (auto-appended via add_messages).
        deal_id:              ID of the deal being analyzed (e.g., 'LD-001').
        lost_deal:            Full dict of the lost deal data from sample_deals.json.
        timeline_analysis:    Output from TimelineAgent (structured JSON dict).
        comparative_analysis: Output from ComparativeAgent (structured JSON dict).
        playbook:             Output from PlaybookAgent (structured JSON dict).
        agent_trace:          List of ReAct step dicts for UI display
                               [{"agent": str, "steps": [{"iteration", "tool", "args", "result"}]}].
        similar_won_deals:    List of similar won deal documents retrieved by RAG.
        errors:               List of error messages encountered during execution.
        next:                 Routing target set by supervisor ('timeline_agent',
                               'comparative_agent', 'playbook_agent', or '__end__').
        current_agent:         The agent currently executing (for trace display).
    """

    messages: Annotated[list, add_messages]
    deal_id: str
    lost_deal: dict
    timeline_analysis: Optional[dict]
    comparative_analysis: Optional[dict]
    playbook: Optional[dict]
    agent_trace: list
    similar_won_deals: list
    errors: list
    next: str
    current_agent: Optional[str]
