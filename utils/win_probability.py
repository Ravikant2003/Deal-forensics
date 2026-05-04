"""
Win probability scorer: heuristic model based on deal timeline quality signals.
"""

from dataclasses import dataclass, field


@dataclass
class WinProbabilityResult:
    score: float                    # 0–100
    risk_level: str                 # Low / Medium / High / Critical
    risk_color: str                 # Green / Yellow / Orange / Red
    factors: list[dict]             # Individual factor contributions
    top_recommendations: list[str]  # Top 3 actions to improve probability


def _clamp(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, value))


def calculate_win_probability(deal: dict, timeline_analysis: dict | None = None) -> WinProbabilityResult:
    """
    Calculate win probability for a deal based on heuristic signals.

    Scoring starts at 70 (optimistic baseline) and adjusts based on:
    - Response time gaps
    - Warning signals
    - Competitor presence
    - Timeline density
    - Whether a proposal was sent
    - Demo completeness

    Args:
        deal: Deal dict with 'timeline', 'competitors', 'value', 'industry'.
        timeline_analysis: Optional output from TimelineAgent for enriched signals.

    Returns:
        WinProbabilityResult with score, risk level, contributing factors, and recommendations.
    """
    score = 70.0
    factors = []
    recommendations = []

    timeline = deal.get("timeline", [])
    competitors = deal.get("competitors", [])

    # ── 1. Response time gaps ────────────────────────────────────────────────
    days = [e["day"] for e in timeline]
    gaps = [
        timeline[i]["day"] - timeline[i - 1]["day"]
        for i in range(1, len(timeline))
    ]

    long_gaps = [g for g in gaps if g > 3]
    max_gap = max(gaps) if gaps else 0
    avg_gap = sum(gaps) / len(gaps) if gaps else 0

    if long_gaps:
        penalty = min(25, len(long_gaps) * 8)
        score -= penalty
        factors.append({
            "name": "Response Time Gaps",
            "impact": -penalty,
            "detail": f"{len(long_gaps)} gap(s) > 3 days detected (max: {max_gap} days)",
        })
        if max_gap > 5:
            recommendations.append("Implement a 48-hour follow-up rule to prevent momentum loss.")
    else:
        score += 5
        factors.append({"name": "Response Time Gaps", "impact": +5, "detail": "No long gaps — good cadence"})

    # ── 2. Competitor presence ───────────────────────────────────────────────
    if competitors:
        penalty = min(20, len(competitors) * 10)
        score -= penalty
        factors.append({
            "name": "Competitor Presence",
            "impact": -penalty,
            "detail": f"{len(competitors)} competitor(s): {', '.join(competitors)}",
        })
        recommendations.append(f"Prepare counter-strategy for {competitors[0]} before next interaction.")
    else:
        score += 8
        factors.append({"name": "Competitor Presence", "impact": +8, "detail": "No competitor mentioned"})

    # ── 3. Key activities present ────────────────────────────────────────────
    events_text = " ".join(
        (e.get("event", "") + " " + e.get("details", "")).lower()
        for e in timeline
    )

    if "demo" in events_text or "demonstration" in events_text:
        score += 6
        factors.append({"name": "Demo Conducted", "impact": +6, "detail": "Product demo was completed"})
    else:
        score -= 10
        factors.append({"name": "Demo Conducted", "impact": -10, "detail": "No demo recorded in timeline"})
        recommendations.append("Schedule a customized product demo within 3 days of initial contact.")

    if "proposal" in events_text:
        score += 5
        factors.append({"name": "Proposal Sent", "impact": +5, "detail": "Proposal was delivered"})
    else:
        score -= 8
        factors.append({"name": "Proposal Sent", "impact": -8, "detail": "No proposal in timeline"})
        recommendations.append("Send a personalized proposal within 24 hours of the demo.")

    if "roi" in events_text or "return on investment" in events_text:
        score += 7
        factors.append({"name": "ROI Discussion", "impact": +7, "detail": "ROI or value discussed"})
    else:
        score -= 5
        factors.append({"name": "ROI Discussion", "impact": -5, "detail": "No ROI discussion recorded"})

    # ── 4. Negative signals ──────────────────────────────────────────────────
    ghost_signals = ["ghost", "no response", "no decision", "lost", "ghosted"]
    neg_count = sum(1 for s in ghost_signals if s in events_text)
    if neg_count > 0:
        penalty = min(20, neg_count * 7)
        score -= penalty
        factors.append({
            "name": "Negative Signals",
            "impact": -penalty,
            "detail": f"{neg_count} ghosting / no-response event(s) detected",
        })
        recommendations.append("Set up automated follow-up sequence after 48 hours of silence.")

    # ── 5. Timeline density ──────────────────────────────────────────────────
    total_duration = max(days) - min(days) if len(days) > 1 else 1
    density = len(timeline) / total_duration if total_duration > 0 else 0

    if density >= 0.4:
        score += 5
        factors.append({"name": "Timeline Density", "impact": +5, "detail": f"Good engagement cadence ({density:.2f} events/day)"})
    elif density < 0.2:
        score -= 5
        factors.append({"name": "Timeline Density", "impact": -5, "detail": f"Low engagement cadence ({density:.2f} events/day)"})
        recommendations.append("Increase touchpoint frequency — aim for at least 1 interaction every 2 days.")

    # ── 6. Enrichment from timeline_analysis ────────────────────────────────
    if timeline_analysis:
        tl_score = timeline_analysis.get("timeline_score")
        if isinstance(tl_score, (int, float)):
            adjustment = (tl_score - 5) * 2  # Range: -8 to +10
            score += adjustment
            factors.append({
                "name": "AI Timeline Score",
                "impact": adjustment,
                "detail": f"AI-computed timeline management score: {tl_score}/10",
            })

    # ── Final score and risk classification ──────────────────────────────────
    final_score = round(_clamp(score), 1)

    if final_score >= 70:
        risk_level, risk_color = "Low", "green"
    elif final_score >= 50:
        risk_level, risk_color = "Medium", "orange"
    elif final_score >= 30:
        risk_level, risk_color = "High", "red"
    else:
        risk_level, risk_color = "Critical", "darkred"

    # Ensure we have at least 3 recommendations
    default_recs = [
        "Map all stakeholders within the first 3 days.",
        "Send ROI calculator immediately after demo.",
        "Set a firm next-step date at the end of every meeting.",
    ]
    while len(recommendations) < 3:
        rec = default_recs.pop(0) if default_recs else "Maintain consistent engagement cadence."
        if rec not in recommendations:
            recommendations.append(rec)

    return WinProbabilityResult(
        score=final_score,
        risk_level=risk_level,
        risk_color=risk_color,
        factors=sorted(factors, key=lambda x: x["impact"]),
        top_recommendations=recommendations[:3],
    )
