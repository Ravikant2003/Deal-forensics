"""
CRM tools for looking up company intelligence and competitor data.
"""

import json
from langchain_core.tools import tool


@tool
def get_crm_data(company_name: str) -> str:
    """Look up CRM intelligence and sales team data for context about a deal.

    Args:
        company_name: Name of the company (case-insensitive, partial match supported).
                      Also useful to pass a sales rep name to get their performance stats.

    Returns:
        JSON string with CRM context: sales team performance, regional stats,
        customer segment insights, and playbook templates relevant to the company.
    """
    try:
        with open("data/crm_data.json", "r") as f:
            crm = json.load(f)

        company_lower = company_name.lower()

        # Try to match against a sales rep or regional data
        result = {}

        # Check sales team performance
        for rep in crm.get("sales_team", []):
            if company_lower in rep.get("name", "").lower():
                result["sales_rep"] = rep
                break

        # Include overall performance metrics
        result["performance_metrics"] = crm.get("performance_metrics", {})
        result["customer_segments"] = crm.get("customer_segments", {})

        # Include playbook templates for common triggers
        result["playbook_templates"] = crm.get("playbook_templates", {})

        if not result.get("sales_rep"):
            result["note"] = f"No direct CRM record found for '{company_name}'. Returning general CRM intelligence."

        return json.dumps(result)

    except FileNotFoundError:
        return json.dumps({"error": "crm_data.json not found", "company": company_name})
    except Exception as e:
        return json.dumps({"error": str(e)})


@tool
def get_competitor_intel(competitor_name: str) -> str:
    """Get competitive intelligence for a named competitor.

    Args:
        competitor_name: Name of the competitor (e.g., 'Competitor A', 'Competitor B').
                         Case-insensitive, partial match supported.

    Returns:
        JSON string with competitor strengths, weaknesses, common objection triggers,
        and recommended counter-strategies from the playbook.
    """
    try:
        with open("data/crm_data.json", "r") as f:
            crm = json.load(f)

        comp_lower = competitor_name.lower()

        # Find matching competitor
        for comp in crm.get("competitors", []):
            if comp_lower in comp.get("name", "").lower():
                # Enrich with playbook responses
                playbook_responses = crm.get("playbook_templates", {}).get(
                    "competitor_responses", {}
                )
                counter = playbook_responses.get(comp["name"], {})
                return json.dumps({
                    **comp,
                    "counter_strategies": counter,
                })

        # Generic fallback
        return json.dumps({
            "name": competitor_name,
            "message": "No specific intelligence found for this competitor.",
            "general_strategy": (
                "Focus on ROI proof, implementation speed, and dedicated support. "
                "Offer a pilot or free trial to reduce switching risk."
            ),
            "strengths": ["Unknown — gather intel through prospect conversation"],
            "weaknesses": ["Unknown — ask prospect what concerns they have about competitor"],
            "counter_strategies": {
                "key_messages": [
                    "Our customers achieve measurable ROI within 90 days",
                    "We provide dedicated onboarding and ongoing support",
                    "Flexible, risk-free pilot program available",
                ]
            },
        })

    except FileNotFoundError:
        return json.dumps({"error": "crm_data.json not found"})
    except Exception as e:
        return json.dumps({"error": str(e)})
