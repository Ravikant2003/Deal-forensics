"""
Utility helper functions — now actively used across the application.
"""

import os
import json
import time
import re
from datetime import datetime


class Helpers:

    @staticmethod
    def setup_environment() -> tuple[bool, list[str]]:
        """
        Check that all required environment variables are set.

        Returns:
            (success: bool, missing_vars: list[str])
        """
        from config.settings import LLM_PROVIDER
        required = ["GROQ_API_KEY"] if LLM_PROVIDER == "groq" else []
        missing = [v for v in required if not os.getenv(v)]
        return len(missing) == 0, missing

    @staticmethod
    def format_timestamp() -> str:
        """Return current timestamp as a readable string."""
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    @staticmethod
    def validate_deal_data(deal_data: dict) -> tuple[bool, str]:
        """
        Validate that a deal dict has the required structure.

        Returns:
            (valid: bool, message: str)
        """
        if not isinstance(deal_data, dict):
            return False, "Deal data must be a dictionary."

        required_fields = ["deal_id", "company", "timeline"]
        missing = [f for f in required_fields if f not in deal_data]
        if missing:
            return False, f"Missing required fields: {', '.join(missing)}"

        timeline = deal_data.get("timeline", [])
        if not isinstance(timeline, list) or len(timeline) == 0:
            return False, "Timeline must be a non-empty list."

        for i, event in enumerate(timeline):
            if not all(k in event for k in ["day", "event", "details"]):
                return False, f"Timeline event #{i + 1} must have 'day', 'event', and 'details' keys."

        return True, "Deal data is valid."

    @staticmethod
    def calculate_confidence_score(analysis_results: dict) -> int:
        """
        Compute a real confidence score (0–100) from the completeness of analysis results.

        Args:
            analysis_results: Dict with keys 'timeline_analysis', 'comparative_analysis', 'playbook'.

        Returns:
            Integer score from 0 to 100.
        """
        score = 40  # Base

        timeline = analysis_results.get("timeline_analysis", {})
        comparative = analysis_results.get("comparative_analysis", {})
        playbook = analysis_results.get("playbook", {})

        # Timeline completeness
        if timeline.get("critical_moments"):
            score += 8
        if timeline.get("failure_point"):
            score += 8
        if timeline.get("timeline_score"):
            score += 5
        if timeline.get("vs_benchmark"):
            score += 4

        # Comparative completeness
        if comparative.get("strategy_differences"):
            score += 8
        if comparative.get("competitive_analysis"):
            score += 6
        if comparative.get("improvement_opportunities"):
            score += 5

        # Playbook completeness
        if playbook.get("immediate_actions"):
            score += 6
        if playbook.get("trigger_responses"):
            score += 5
        if playbook.get("success_metrics"):
            score += 5

        # Penalize fallback / error states
        if timeline.get("parse_error") or comparative.get("parse_error") or playbook.get("parse_error"):
            score -= 20

        return max(0, min(100, score))

    @staticmethod
    def format_currency(amount) -> str:
        """Format a numeric amount as a USD currency string."""
        try:
            return "${:,.0f}".format(float(amount))
        except (ValueError, TypeError):
            return "$0"

    @staticmethod
    def get_deal_duration(deal: dict) -> int:
        """
        Return the actual deal duration in days (max_day - min_day).
        Fixes the old bug where len(timeline) was used instead.
        """
        timeline = deal.get("timeline", [])
        if not timeline:
            return 0
        days = [e["day"] for e in timeline]
        return max(days) - min(days)

    @staticmethod
    def generate_deal_summary(deal: dict) -> str:
        """Generate a quick human-readable summary of a deal."""
        timeline = deal.get("timeline", [])
        duration = Helpers.get_deal_duration(deal)

        lines = [
            f"Company: {deal.get('company', 'Unknown')}",
            f"Value: {Helpers.format_currency(deal.get('value', 0))}",
            f"Duration: {duration} days",
            f"Events: {len(timeline)} timeline events",
        ]
        if deal.get("competitors"):
            lines.append(f"Competitors: {', '.join(deal['competitors'])}")
        if timeline:
            last = timeline[-1]
            lines.append(f"Last Event: {last['event']} (Day {last['day']})")

        return "\n".join(lines)

    @staticmethod
    def save_analysis_results(deal_id: str, analysis_results: dict, output_dir: str = "output") -> bool:
        """Persist full analysis results dict to a JSON file."""
        try:
            os.makedirs(output_dir, exist_ok=True)
            filename = f"{output_dir}/full_analysis_{deal_id}_{int(time.time())}.json"
            with open(filename, "w") as f:
                json.dump(analysis_results, f, indent=2)
            return True
        except Exception:
            return False

    @staticmethod
    def load_analysis_results(filename: str) -> dict | None:
        """Load persisted analysis results from a JSON file."""
        try:
            with open(filename, "r") as f:
                return json.load(f)
        except Exception:
            return None

    @staticmethod
    def check_api_health() -> tuple[bool, str]:
        """Check if required LLM API is configured based on provider."""
        from config.settings import LLM_PROVIDER
        if LLM_PROVIDER == "ollama":
            return True, "Ollama: ✅ Using local model"
        if os.getenv("GROQ_API_KEY"):
            return True, "Groq API: ✅ Configured"
        return False, f"{LLM_PROVIDER.upper()} API: ❌ Not configured — check your .env file"

    @staticmethod
    def extract_competitor_names(text: str) -> list[str]:
        """Extract competitor names from free text using pattern matching."""
        if not text:
            return []
        patterns = [
            r"competitor\s+([A-Z][a-z]+)",
            r"([A-Z][a-z]+\s+(?:Inc|Corp|LLC|Ltd))",
            r"competing with\s+([A-Z][a-z]+)",
            r"vs\.?\s+([A-Z][a-z]+)",
        ]
        found = set()
        for pattern in patterns:
            found.update(re.findall(pattern, text, re.IGNORECASE))
        return list(found)