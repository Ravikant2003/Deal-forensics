"""
Output tools for persisting analysis results to disk.
"""

import json
import os
import time
from langchain_core.tools import tool


@tool
def save_analysis_result(deal_id: str, analysis_type: str, data_json: dict) -> str:
    """Save analysis result to the output directory as a JSON file.

    Args:
        deal_id: The unique deal identifier (e.g., 'LD-001').
        analysis_type: Type of analysis being saved — one of:
                       'timeline', 'comparative', 'playbook', or 'full'.
        data_json: A dictionary (JSON object) of the analysis data to persist.

    Returns:
        Confirmation message with the saved file path, or an error message.
    """
    try:
        os.makedirs("output", exist_ok=True)

        timestamp = int(time.time())
        filename = f"output/{analysis_type}_{deal_id}_{timestamp}.json"

        # Accept both string and dict inputs
        if isinstance(data_json, str):
            data = json.loads(data_json)
        else:
            data = data_json

        with open(filename, "w") as f:
            json.dump(data, f, indent=2)

        return f"✅ Successfully saved {analysis_type} analysis for deal {deal_id} → {filename}"

    except json.JSONDecodeError as e:
        return f"❌ Error: Invalid JSON data provided — {str(e)}"
    except Exception as e:
        return f"❌ Error saving analysis: {str(e)}"
