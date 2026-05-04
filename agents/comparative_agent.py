"""
Comparative Agent — ReAct loop using LLM tool-use model.
Tools: search_similar_deals (hybrid RAG), get_crm_data, get_competitor_intel
"""

import json
import yaml

from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage

from config.settings import PROMPTS_PATH
from config.llm_helper import get_llm
from graph.state import AgentState
from tools.rag_tools import search_similar_deals
from tools.crm_tools import get_crm_data, get_competitor_intel

COMPARATIVE_TOOLS = [search_similar_deals, get_crm_data, get_competitor_intel]
TOOL_MAP = {t.name: t for t in COMPARATIVE_TOOLS}


def _load_system_prompt() -> str:
    with open(PROMPTS_PATH, "r") as f:
        prompts = yaml.safe_load(f)
    return prompts["comparative_agent"]["system_prompt"]


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


def run_comparative_agent(state: AgentState) -> dict:
    """
    LangGraph node: Comparative ReAct agent.
    Retrieves similar won deals via hybrid RAG and compares against the lost deal.
    """
    llm = get_llm(temperature=0)
    llm_with_tools = llm.bind_tools(COMPARATIVE_TOOLS)

    lost_deal = state.get("lost_deal", {})
    timeline_analysis = state.get("timeline_analysis", {})
    competitors = lost_deal.get("competitors", [])

    # Build a rich search query for better RAG retrieval
    search_query = (
        f"{lost_deal.get('company', '')} "
        f"{lost_deal.get('industry', '')} "
        f"{lost_deal.get('loss_reason', '')} "
        f"{' '.join(competitors)}"
    ).strip()

    messages = [
        SystemMessage(content=_load_system_prompt()),
        HumanMessage(content=(
            f"Compare this lost deal with similar won deals:\n\n"
            f"Company: {lost_deal.get('company', 'Unknown')}\n"
            f"Industry: {lost_deal.get('industry', 'Unknown')}\n"
            f"Deal Value: ${lost_deal.get('value', 0):,}\n"
            f"Loss Reason: {lost_deal.get('loss_reason', 'Unknown')}\n"
            f"Competitors: {', '.join(competitors)}\n"
            f"Region: {lost_deal.get('region', 'Unknown')}\n\n"
            f"Timeline Analysis Summary:\n"
            f"- Timeline Score: {timeline_analysis.get('timeline_score', 'N/A')}/10\n"
            f"- Avg Response Days: {timeline_analysis.get('avg_response_days', 'N/A')}\n"
            f"- Max Gap Days: {timeline_analysis.get('max_response_gap', 'N/A')}\n\n"
            f"STEP 1: Call search_similar_deals with query='{search_query}' "
            f"and industry='{lost_deal.get('industry', '')}'\n"
            f"STEP 2: Call get_competitor_intel for each competitor: {', '.join(competitors)}\n"
            f"STEP 3: Call get_crm_data to get CRM context.\n"
            f"STEP 4: Produce your final comparative JSON analysis."
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

    analysis = _parse_json_from_text(response.content)

    # Compute real confidence from analysis completeness
    completeness = sum([
        bool(analysis.get("response_time_comparison")),
        bool(analysis.get("strategy_differences")),
        bool(analysis.get("competitive_analysis")),
        bool(analysis.get("improvement_opportunities")),
        bool(analysis.get("success_factors")),
    ])
    analysis["confidence_score"] = min(95, 50 + completeness * 9)

    existing_trace = state.get("agent_trace", [])

    return {
        "comparative_analysis": analysis,
        "agent_trace": existing_trace + [{"agent": "comparative_agent", "steps": trace}],
        "messages": messages,
        "current_agent": "comparative_agent",
    }