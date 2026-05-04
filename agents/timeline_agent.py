"""
Timeline Agent — ReAct loop using LLM tool-use model.
Tools: calculate_deal_metrics, get_industry_benchmarks, get_crm_data
"""

import json
import yaml

from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage, AIMessage

from config.settings import PROMPTS_PATH
from config.llm_helper import get_llm
from graph.state import AgentState
from tools.analytics_tools import calculate_deal_metrics, get_industry_benchmarks
from tools.crm_tools import get_crm_data

TIMELINE_TOOLS = [calculate_deal_metrics, get_industry_benchmarks, get_crm_data]
TOOL_MAP = {t.name: t for t in TIMELINE_TOOLS}


def _load_system_prompt() -> str:
    with open(PROMPTS_PATH, "r") as f:
        prompts = yaml.safe_load(f)
    return prompts["timeline_agent"]["system_prompt"]


def _parse_json_from_text(text: str) -> dict:
    """Robustly extract a JSON object from LLM response text."""
    try:
        if "```json" in text:
            json_str = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            json_str = text.split("```")[1].strip()
        else:
            json_str = text

        start = json_str.find("{")
        end = json_str.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(json_str[start:end])
        return json.loads(json_str.strip())
    except Exception:
        return {"parse_error": True, "raw_response": text[:800]}


def run_timeline_agent(state: AgentState) -> dict:
    """
    LangGraph node: Timeline ReAct agent.
    Performs forensic timeline analysis using tool calls + LLM.
    """
    llm = get_llm(temperature=0)
    llm_with_tools = llm.bind_tools(TIMELINE_TOOLS)

    lost_deal = state.get("lost_deal", {})
    timeline_json = json.dumps(lost_deal.get("timeline", []))

    messages = [
        SystemMessage(content=_load_system_prompt()),
        HumanMessage(content=(
            f"Analyze this lost deal timeline:\n\n"
            f"Company: {lost_deal.get('company', 'Unknown')}\n"
            f"Industry: {lost_deal.get('industry', 'Unknown')}\n"
            f"Deal Value: ${lost_deal.get('value', 0):,}\n"
            f"Loss Reason: {lost_deal.get('loss_reason', 'Unknown')}\n"
            f"Competitors: {', '.join(lost_deal.get('competitors', []))}\n"
            f"Sales Rep: {lost_deal.get('sales_rep', 'Unknown')}\n"
            f"Region: {lost_deal.get('region', 'Unknown')}\n\n"
            f"Timeline JSON: {timeline_json}\n\n"
            f"STEP 1: Call calculate_deal_metrics with the Timeline JSON above.\n"
            f"STEP 2: Call get_industry_benchmarks with the industry: {lost_deal.get('industry', 'General')}\n"
            f"STEP 3: Call get_crm_data with company name or sales rep name.\n"
            f"STEP 4: Produce your final JSON analysis."
        )),
    ]

    trace = []
    max_iterations = 8

    for iteration in range(max_iterations):
        response = llm_with_tools.invoke(messages)
        messages.append(response)

        # No tool calls → final answer
        if not response.tool_calls:
            break

        # Execute each tool call
        for tc in response.tool_calls:
            tool_name = tc["name"]
            tool_args = tc["args"]

            if tool_name in TOOL_MAP:
                try:
                    result = TOOL_MAP[tool_name].invoke(tool_args)
                except Exception as e:
                    result = json.dumps({"error": str(e)})
            else:
                result = json.dumps({"error": f"Unknown tool: {tool_name}"})

            trace.append({
                "iteration": iteration + 1,
                "tool": tool_name,
                "args": str(tool_args)[:150],
                "result": str(result)[:300],
            })

            messages.append(
                ToolMessage(content=str(result), tool_call_id=tc["id"])
            )

    # Parse structured analysis from final LLM message
    analysis = _parse_json_from_text(response.content)

    # Attach computed timeline metrics if available
    try:
        raw_metrics = calculate_deal_metrics.invoke({"timeline_json": timeline_json})
        metrics = json.loads(raw_metrics)
        analysis["computed_metrics"] = metrics

        # Fix: actual duration from computed metrics
        analysis["total_duration_days"] = metrics.get("total_duration_days", 0)
        analysis["avg_response_days"] = metrics.get("avg_response_gap_days", 0)
        analysis["max_response_gap"] = metrics.get("max_gap_days", 0)
    except Exception:
        pass

    existing_trace = state.get("agent_trace", [])

    return {
        "timeline_analysis": analysis,
        "agent_trace": existing_trace + [{"agent": "timeline_agent", "steps": trace}],
        "messages": messages,
        "current_agent": "timeline_agent",
    }