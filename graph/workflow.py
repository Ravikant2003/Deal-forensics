"""
LangGraph StateGraph workflow: Agentic supervisor with tools pattern.
Supervisor uses LLM to decide next agent based on current state.
"""

from langgraph.graph import StateGraph, END
from langchain_core.messages import SystemMessage, HumanMessage
from config.llm_helper import get_llm

# Lazy imports to avoid circular imports
def _get_timeline_agent():
    from agents.timeline_agent import run_timeline_agent
    return run_timeline_agent

def _get_comparative_agent():
    from agents.comparative_agent import run_comparative_agent
    return run_comparative_agent

def _get_playbook_agent():
    from agents.playbook_agent import run_playbook_agent
    return run_playbook_agent


# Agent tool definitions for the supervisor
AGENT_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "call_timeline_agent",
            "description": "Run the Timeline Agent to analyze deal timeline, identify failure points, warning signals, and generate timeline score.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "call_comparative_agent",
            "description": "Run the Comparative Agent to compare lost deal against similar won deals using RAG retrieval.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "call_playbook_agent",
            "description": "Run the Playbook Agent to generate actionable sales playbook from analysis results.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "finish_analysis",
            "description": "Call this when all required analysis is complete. Ends the workflow.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
]


def call_timeline_agent(state):
    """Tool wrapper: Run the Timeline Agent."""
    run_fn = _get_timeline_agent()
    result = run_fn(state)
    return {
        "timeline_analysis": result.get("timeline_analysis"),
        "agent_trace": result.get("agent_trace", []),
        "messages": result.get("messages", []),
    }


def call_comparative_agent(state):
    """Tool wrapper: Run the Comparative Agent."""
    run_fn = _get_comparative_agent()
    result = run_fn(state)
    return {
        "comparative_analysis": result.get("comparative_analysis"),
        "agent_trace": result.get("agent_trace", []),
        "messages": result.get("messages", []),
    }


def call_playbook_agent(state):
    """Tool wrapper: Run the Playbook Agent."""
    run_fn = _get_playbook_agent()
    result = run_fn(state)
    return {
        "playbook": result.get("playbook"),
        "agent_trace": result.get("agent_trace", []),
        "messages": result.get("messages", []),
    }


def agentic_supervisor(state):
    """
    Agentic supervisor: Uses LLM to decide which agent to run next based on current state.
    """
    llm = get_llm(temperature=0)
    llm_with_tools = llm.bind_tools(AGENT_TOOLS)

    # Build context for the supervisor
    context = f"""
Current State:
- Deal ID: {state.get('deal_id', 'Unknown')}
- Timeline Analysis: {'Complete' if state.get('timeline_analysis') else 'Not done'}
- Comparative Analysis: {'Complete' if state.get('comparative_analysis') else 'Not done'}
- Playbook: {'Complete' if state.get('playbook') else 'Not done'}

Based on this state, which tool should I call next?
"""

    messages = [
        SystemMessage(content="You are an agentic supervisor. Call the appropriate tool based on the current state."),
        HumanMessage(content=context),
    ]

    response = llm_with_tools.invoke(messages)

    # Parse tool call from response
    if hasattr(response, "tool_calls") and response.tool_calls:
        tool_name = response.tool_calls[0]["name"]
        return {"next": tool_name}
    else:
        # Fallback: parse from content
        content = response.content.lower()
        if "finish" in content:
            return {"next": "finish_analysis"}
        elif "timeline" in content and not state.get("timeline_analysis"):
            return {"next": "call_timeline_agent"}
        elif "comparative" in content and not state.get("comparative_analysis"):
            return {"next": "call_comparative_agent"}
        elif "playbook" in content and not state.get("playbook"):
            return {"next": "call_playbook_agent"}
        elif state.get("playbook"):
            return {"next": "finish_analysis"}
        else:
            return {"next": "call_timeline_agent"}


def route(state):
    """Edge routing function — reads the 'next' field set by supervisor."""
    return state["next"]


def build_graph():
    """
    Build and compile the LangGraph StateGraph with agentic supervisor.

    Returns:
        A compiled LangGraph runnable (supports .invoke() and .stream())
    """
    from graph.state import AgentState

    workflow = StateGraph(AgentState)

    # Register nodes
    workflow.add_node("supervisor", agentic_supervisor)
    workflow.add_node("call_timeline_agent", call_timeline_agent)
    workflow.add_node("call_comparative_agent", call_comparative_agent)
    workflow.add_node("call_playbook_agent", call_playbook_agent)
    workflow.add_node("finish_analysis", lambda s: {"next": "__end__"})

    # Entry point
    workflow.set_entry_point("supervisor")

    # Supervisor routes conditionally
    workflow.add_conditional_edges(
        "supervisor",
        route,
        {
            "call_timeline_agent": "call_timeline_agent",
            "call_comparative_agent": "call_comparative_agent",
            "call_playbook_agent": "call_playbook_agent",
            "finish_analysis": "finish_analysis",
            "__end__": END,
        },
    )

    # After each agent completes, return to supervisor for next decision
    workflow.add_edge("call_timeline_agent", "supervisor")
    workflow.add_edge("call_comparative_agent", "supervisor")
    workflow.add_edge("call_playbook_agent", "supervisor")
    workflow.add_edge("finish_analysis", END)

    return workflow.compile()
