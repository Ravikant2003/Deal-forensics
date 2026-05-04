"""
Analytics tools for quantitative deal metric calculation and industry benchmarking.
"""

import json
from langchain_core.tools import tool


@tool
def calculate_deal_metrics(timeline_json: str) -> str:
    """Calculate quantitative metrics from a deal timeline.

    Args:
        timeline_json: JSON string of timeline events. Each event must have
                       'day' (int), 'event' (str), and 'details' (str) keys.
                       Example: '[{"day": 1, "event": "Initial contact", "details": "..."}]'

    Returns:
        JSON string with computed metrics including total_duration_days,
        avg_response_gap_days, max_gap_days, long_gaps, timeline_density,
        critical_events_count, and a list of critical event names.
    """
    try:
        timeline = json.loads(timeline_json) if isinstance(timeline_json, str) else timeline_json

        if not timeline:
            return json.dumps({"error": "Empty timeline provided"})

        days = [e["day"] for e in timeline]
        total_duration = max(days) - min(days) if len(days) > 1 else 0

        gaps = []
        for i in range(1, len(timeline)):
            gap = timeline[i]["day"] - timeline[i - 1]["day"]
            gaps.append(gap)

        avg_gap = round(sum(gaps) / len(gaps), 2) if gaps else 0
        max_gap = max(gaps) if gaps else 0
        long_gaps = [g for g in gaps if g > 3]

        critical_keywords = [
            "proposal", "demo", "pricing", "competitor",
            "budget", "ghost", "no response", "lost", "technical",
        ]
        critical_events = [
            e for e in timeline
            if any(
                kw in (e.get("event", "") + " " + e.get("details", "")).lower()
                for kw in critical_keywords
            )
        ]

        return json.dumps({
            "total_duration_days": total_duration,
            "number_of_events": len(timeline),
            "avg_response_gap_days": avg_gap,
            "max_gap_days": max_gap,
            "long_gaps_count": len(long_gaps),
            "long_gap_days": long_gaps,
            "timeline_density": round(
                len(timeline) / total_duration if total_duration > 0 else 0, 3
            ),
            "critical_events_count": len(critical_events),
            "critical_events": [e["event"] for e in critical_events],
        })

    except json.JSONDecodeError as e:
        return json.dumps({"error": f"Invalid JSON: {str(e)}"})
    except Exception as e:
        return json.dumps({"error": str(e)})


@tool
def get_industry_benchmarks(industry: str) -> str:
    """Get industry-standard benchmarks for deal management performance.

    Args:
        industry: Industry name to look up. Supported values:
                  Technology, SaaS, Enterprise, Retail, E-commerce, General.
                  Partial / case-insensitive matching is supported.

    Returns:
        JSON string with avg_response_days, avg_deal_duration_days,
        industry_win_rate, best_practices, and red_flags.
    """
    try:
        with open("data/benchmarks.json", "r") as f:
            benchmarks = json.load(f)

        industry_lower = industry.lower().strip()

        # Exact or partial match
        for key, data in benchmarks.items():
            if industry_lower in key.lower() or key.lower() in industry_lower:
                return json.dumps({"industry": key, **data})

        # Fallback to General
        return json.dumps({"industry": "General", **benchmarks.get("General", {
            "avg_response_days": 1.5,
            "avg_deal_duration_days": 21,
            "industry_win_rate": 0.38,
            "best_practices": ["Respond within 4 hours", "Follow up within 48 hours"],
            "red_flags": ["No response for 4+ days", "Competitor unaddressed"],
        })})

    except FileNotFoundError:
        return json.dumps({
            "error": "benchmarks.json not found",
            "industry": industry,
            "avg_response_days": 1.5,
            "avg_deal_duration_days": 21,
            "industry_win_rate": 0.38,
        })
    except Exception as e:
        return json.dumps({"error": str(e)})
