"""
Playbook Agent — ReAct loop using LLM tool-use model.
Tools: get_industry_benchmarks, get_competitor_intel
"""

import json
import yaml

from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage

from config.settings import PROMPTS_PATH
from config.llm_helper import get_llm
from graph.state import AgentState
from tools.analytics_tools import get_industry_benchmarks
from tools.crm_tools import get_competitor_intel

PLAYBOOK_TOOLS = [get_industry_benchmarks, get_competitor_intel]
TOOL_MAP = {t.name: t for t in PLAYBOOK_TOOLS}


def _load_system_prompt() -> str:
    with open(PROMPTS_PATH, "r") as f:
        prompts = yaml.safe_load(f)
    return prompts["playbook_agent"]["system_prompt"]


def _parse_json_from_text(text: str) -> dict:
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


def run_playbook_agent(state: AgentState) -> dict:
    """
    LangGraph node: Playbook ReAct agent.
    Synthesizes timeline + comparative analysis into an actionable sales playbook.
    """
    llm = get_llm(temperature=0)
    llm_with_tools = llm.bind_tools(PLAYBOOK_TOOLS)

    lost_deal = state.get("lost_deal", {})
    timeline_analysis = state.get("timeline_analysis", {})
    comparative_analysis = state.get("comparative_analysis", {})
    competitors = lost_deal.get("competitors", [])

    # Summarize previous analyses for the prompt (avoid token explosion)
    timeline_summary = {
        "timeline_score": timeline_analysis.get("timeline_score"),
        "failure_point": timeline_analysis.get("failure_point"),
        "warning_signals": timeline_analysis.get("warning_signals", [])[:3],
        "recommendations": timeline_analysis.get("recommendations", [])[:3],
        "vs_benchmark": timeline_analysis.get("vs_benchmark"),
    }

    comparative_summary = {
        "response_time_comparison": comparative_analysis.get("response_time_comparison"),
        "strategy_differences": comparative_analysis.get("strategy_differences", [])[:3],
        "competitive_analysis": comparative_analysis.get("competitive_analysis"),
        "improvement_opportunities": comparative_analysis.get("improvement_opportunities", [])[:5],
        "success_factors": comparative_analysis.get("success_factors", [])[:4],
    }

    messages = [
        SystemMessage(content=_load_system_prompt()),
        HumanMessage(content=(
            f"Generate an actionable sales playbook for this deal:\n\n"
            f"Company: {lost_deal.get('company', 'Unknown')}\n"
            f"Industry: {lost_deal.get('industry', 'Unknown')}\n"
            f"Deal Value: ${lost_deal.get('value', 0):,}\n"
            f"Loss Reason: {lost_deal.get('loss_reason', 'Unknown')}\n"
            f"Competitors: {', '.join(competitors)}\n\n"
            f"TIMELINE ANALYSIS SUMMARY:\n{json.dumps(timeline_summary, indent=2)}\n\n"
            f"COMPARATIVE ANALYSIS SUMMARY:\n{json.dumps(comparative_summary, indent=2)}\n\n"
            f"STEP 1: Call get_industry_benchmarks for industry: {lost_deal.get('industry', 'General')}\n"
            f"STEP 2: Call get_competitor_intel for each competitor: {', '.join(competitors)}\n"
            f"STEP 3: Produce your comprehensive playbook JSON.\n"
            f"STEP 4: Call save_analysis_result with deal_id='{lost_deal.get('deal_id', 'unknown')}', "
            f"analysis_type='playbook', and your playbook JSON."
        )),
    ]

    trace = []
    max_iterations = 10

    for iteration in range(max_iterations):
        response = llm_with_tools.invoke(messages)
        messages.append(response)

        if not response.tool_calls:
            break

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

    playbook = _parse_json_from_text(response.content)

    # Compute real confidence score based on content completeness
    completeness = sum([
        bool(playbook.get("immediate_actions")),
        bool(playbook.get("trigger_responses")),
        bool(playbook.get("competitor_strategies")),
        bool(playbook.get("timing_guidelines")),
        bool(playbook.get("escalation_protocols")),
        bool(playbook.get("success_metrics")),
    ])
    playbook["confidence_score"] = min(98, 55 + completeness * 7)

    # Derive expected impact from completeness + timeline score
    timeline_score = timeline_analysis.get("timeline_score", 5)
    if isinstance(timeline_score, (int, float)):
        if timeline_score <= 4:
            playbook["expected_impact"] = "High"
        elif timeline_score <= 7:
            playbook["expected_impact"] = "Medium"
        else:
            playbook["expected_impact"] = "Low"
    else:
        playbook["expected_impact"] = "Medium"

    existing_trace = state.get("agent_trace", [])
    return {
        "playbook": playbook,
        "agent_trace": existing_trace + [{"agent": "playbook", "steps": trace}],
        "messages": messages,
        "current_agent": "playbook_agent",
    }