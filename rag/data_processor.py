"""
Data processor: loads deal data, computes metrics, and provides similarity matching.
Now integrates CRM data for enriched deal context.
"""

import json
from config.settings import SAMPLE_DEALS_PATH, CRM_DATA_PATH


class DataProcessor:
    def __init__(self):
        self.sample_data = self._load_sample_data()
        self.crm_data = self._load_crm_data()

    # ── Data loading ────────────────────────────────────────────────────────

    def _load_sample_data(self) -> dict:
        try:
            with open(SAMPLE_DEALS_PATH, "r") as f:
                return json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(
                f"sample_deals.json not found at '{SAMPLE_DEALS_PATH}'. "
                "Ensure the data file exists in the data/ directory."
            )
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in sample_deals.json: {e}")

    def _load_crm_data(self) -> dict:
        try:
            with open(CRM_DATA_PATH, "r") as f:
                return json.load(f)
        except FileNotFoundError:
            return {}
        except json.JSONDecodeError:
            return {}

    # ── Deal accessors ──────────────────────────────────────────────────────

    def get_all_lost_deals(self) -> list:
        return self.sample_data.get("lost_deals", [])

    def get_all_won_deals(self) -> list:
        return self.sample_data.get("won_deals", [])

    def get_lost_deal_by_id(self, deal_id: str) -> dict | None:
        for deal in self.get_all_lost_deals():
            if deal["deal_id"] == deal_id:
                return deal
        return None

    # ── CRM enrichment ──────────────────────────────────────────────────────

    def enrich_deal_with_crm(self, deal: dict) -> dict:
        """Attach CRM context (rep performance, segment insights) to a deal dict."""
        enriched = dict(deal)

        # Sales rep performance
        rep_name = deal.get("sales_rep", "")
        for rep in self.crm_data.get("sales_team", []):
            if rep_name and rep_name.lower() in rep.get("name", "").lower():
                enriched["rep_stats"] = {
                    "win_rate": rep.get("win_rate"),
                    "avg_deal_size": rep.get("avg_deal_size"),
                    "active_deals": rep.get("active_deals"),
                }
                break

        # Overall performance context
        enriched["org_metrics"] = self.crm_data.get("performance_metrics", {})

        # Competitor playbook templates
        enriched["competitor_playbooks"] = self.crm_data.get(
            "playbook_templates", {}
        ).get("competitor_responses", {})

        # Value tier
        value = deal.get("value", 0)
        if value >= 100000:
            enriched["value_tier"] = "enterprise"
        elif value >= 50000:
            enriched["value_tier"] = "mid-market"
        else:
            enriched["value_tier"] = "small"

        return enriched

    # ── Metrics ─────────────────────────────────────────────────────────────

    def extract_timeline_metrics(self, deal: dict) -> dict:
        """Compute quantitative metrics from a deal's timeline."""
        timeline = deal.get("timeline", [])
        if not timeline:
            return {}

        days = [e["day"] for e in timeline]
        total_duration = max(days) - min(days) if len(days) > 1 else 0

        gaps = [
            timeline[i]["day"] - timeline[i - 1]["day"]
            for i in range(1, len(timeline))
        ]
        avg_gap = sum(gaps) / len(gaps) if gaps else 0
        max_gap = max(gaps) if gaps else 0

        critical_keywords = [
            "proposal", "demo", "pricing", "competitor",
            "budget", "ghost", "no response", "lost",
        ]
        critical_events = [
            e for e in timeline
            if any(
                kw in (e["event"] + " " + e["details"]).lower()
                for kw in critical_keywords
            )
        ]

        return {
            "total_duration_days": total_duration,
            "number_of_events": len(timeline),
            "avg_response_gap_days": round(avg_gap, 2),
            "max_response_gap_days": max_gap,
            "long_gaps_count": sum(1 for g in gaps if g > 3),
            "timeline_density": round(
                len(timeline) / total_duration if total_duration > 0 else 0, 3
            ),
            "critical_events_count": len(critical_events),
        }

    # ── Deal similarity ─────────────────────────────────────────────────────

    def _calculate_deal_similarity(self, deal1: dict, deal2: dict) -> float:
        score = 0.0

        # Industry match (40%)
        if deal1.get("industry") == deal2.get("industry"):
            score += 0.4

        # Value range match within 50% (30%)
        v1, v2 = deal1.get("value", 0), deal2.get("value", 0)
        if v1 > 0 and v2 > 0:
            ratio = min(v1, v2) / max(v1, v2)
            if ratio > 0.5:
                score += 0.3

        # Competitor overlap (20%)
        c1 = set(deal1.get("competitors", []))
        c2 = set(deal2.get("competitors", []))
        if c1 & c2:
            score += 0.2

        # Region match (10%)
        if deal1.get("region") == deal2.get("region"):
            score += 0.1

        return score

    def get_won_deals_for_comparison(self, lost_deal: dict, n: int = 3) -> list:
        """Get top-N most similar won deals by scoring."""
        won_deals = self.get_all_won_deals()
        scored = [
            (deal, self._calculate_deal_similarity(lost_deal, deal))
            for deal in won_deals
        ]
        scored.sort(key=lambda x: x[1], reverse=True)
        return [d for d, score in scored[:n] if score > 0.2]

    # ── Statistics ──────────────────────────────────────────────────────────

    def get_deal_statistics(self) -> dict:
        """Portfolio-level statistics across all deals."""
        lost = self.get_all_lost_deals()
        won = self.get_all_won_deals()

        return {
            "total_lost_deals": len(lost),
            "total_won_deals": len(won),
            "total_deal_value_lost": sum(d.get("value", 0) for d in lost),
            "total_deal_value_won": sum(d.get("value", 0) for d in won),
            "win_rate": round(len(won) / (len(won) + len(lost)), 2) if (won or lost) else 0,
            "common_loss_reasons": self._get_common_loss_reasons(lost),
            "avg_deal_duration_lost": round(self._get_avg_deal_duration(lost), 1),
            "avg_deal_duration_won": round(self._get_avg_deal_duration(won), 1),
            "losses_by_industry": self._group_by_field(lost, "industry"),
            "losses_by_region": self._group_by_field(lost, "region"),
        }

    def _get_common_loss_reasons(self, lost_deals: list) -> dict:
        reasons: dict = {}
        for deal in lost_deals:
            r = deal.get("loss_reason", "unknown")
            reasons[r] = reasons.get(r, 0) + 1
        return dict(sorted(reasons.items(), key=lambda x: x[1], reverse=True))

    def _get_avg_deal_duration(self, deals: list) -> float:
        durations = []
        for deal in deals:
            timeline = deal.get("timeline", [])
            if timeline:
                days = [e["day"] for e in timeline]
                durations.append(max(days) - min(days))
        return sum(durations) / len(durations) if durations else 0

    def _group_by_field(self, deals: list, field: str) -> dict:
        groups: dict = {}
        for deal in deals:
            key = deal.get(field, "Unknown")
            groups[key] = groups.get(key, 0) + 1
        return groups