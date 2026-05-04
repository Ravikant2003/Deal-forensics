"""
PDF exporter: generates a structured, formatted playbook PDF report using fpdf2.
"""

from io import BytesIO
from fpdf import FPDF


def _clean(text: str) -> str:
    """Sanitize unicode characters that break FPDF's default fonts."""
    if not isinstance(text, str):
        text = str(text)
    replacements = {
        "\u2014": "-", "\u2013": "-",
        "\u201c": '"', "\u201d": '"',
        "\u2018": "'", "\u2019": "'",
        "\u2026": "...", "\u2192": "->"
    }
    for k, v in replacements.items():
        text = text.replace(k, v)
    return text.encode('latin-1', 'replace').decode('latin-1')


class PlaybookPDF(FPDF):
    def header(self):
        self.set_fill_color(30, 30, 60)
        self.rect(0, 0, 210, 18, "F")
        self.set_font("Helvetica", "B", 13)
        self.set_text_color(255, 255, 255)
        self.cell(0, 18, _clean("Deal Forensics AI - Analysis Report"), align="C")
        self.ln(12)
        self.set_text_color(0, 0, 0)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f"Page {self.page_no()}", align="C")

    def section_title(self, title: str):
        self.set_font("Helvetica", "B", 12)
        self.set_fill_color(240, 240, 255)
        self.set_text_color(30, 30, 90)
        self.cell(0, 9, _clean(f"  {title}"), new_x="LMARGIN", new_y="NEXT", fill=True)
        self.set_text_color(0, 0, 0)
        self.ln(2)

    def sub_title(self, title: str):
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(50, 50, 120)
        self.cell(0, 7, _clean(title), new_x="LMARGIN", new_y="NEXT")
        self.set_text_color(0, 0, 0)

    def body_text(self, text: str, indent: int = 0):
        self.set_font("Helvetica", size=9)
        self.set_x(self.l_margin + indent)
        self.multi_cell(0, 5, _clean(text))
        self.ln(1)

    def bullet(self, text: str, indent: int = 8):
        self.set_font("Helvetica", size=9)
        self.set_x(self.l_margin + indent)
        self.multi_cell(0, 5, _clean(f"-  {text}"))

    def metric_row(self, label: str, value: str):
        self.set_font("Helvetica", "B", 9)
        label_clean = _clean(label) or ""
        value_clean = _clean(str(value)[:100]) if value else "N/A"
        try:
            self.cell(50, 6, label_clean, border=0)
            self.ln(-1)
            self.set_font("Helvetica", size=9)
            self.multi_cell(0, 6, value_clean)
            self.ln(2)
        except Exception:
            self.ln(4)


def _safe(value, fallback: str = "N/A") -> str:
    if value is None:
        return fallback
    return str(value)


def generate_playbook_pdf(
    lost_deal: dict,
    timeline_analysis: dict,
    comparative_analysis: dict,
    playbook: dict,
) -> bytes:
    """
    Generate a structured PDF report from the forensic analysis.

    Args:
        lost_deal:            Original deal data dict.
        timeline_analysis:    Output from TimelineAgent.
        comparative_analysis: Output from ComparativeAgent.
        playbook:             Output from PlaybookAgent.

    Returns:
        Raw PDF bytes suitable for st.download_button.
    """
    pdf = PlaybookPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_margins(10, 15, 10)
    pdf.set_font("Helvetica", size=10)

    # ── Deal Overview ────────────────────────────────────────────────────────
    pdf.section_title("1. Deal Overview")
    pdf.metric_row("Company:", lost_deal.get("company", "Unknown"))
    pdf.metric_row("Deal Value:", f"${lost_deal.get('value', 0):,}")
    pdf.metric_row("Industry:", lost_deal.get("industry", "Unknown"))
    pdf.metric_row("Loss Reason:", lost_deal.get("loss_reason", "Unknown"))
    pdf.metric_row("Region:", lost_deal.get("region", "Unknown"))
    pdf.metric_row("Competitors:", ", ".join(lost_deal.get("competitors", [])))
    pdf.metric_row("Timeline Score:", f"{timeline_analysis.get('timeline_score', 'N/A')}/10")
    pdf.ln(4)

    # ── Timeline Analysis ────────────────────────────────────────────────────
    pdf.section_title("2. Timeline Analysis")

    fp = timeline_analysis.get("failure_point", {})
    if fp:
        pdf.sub_title("Critical Failure Point")
        pdf.body_text(
            f"Day {fp.get('day', '?')}: {fp.get('event', 'Unknown')} — {fp.get('reason', '')}"
        )

    warnings = timeline_analysis.get("warning_signals", [])
    if warnings:
        pdf.sub_title("Warning Signals")
        for w in warnings[:5]:
            pdf.bullet(
                f"Day {w.get('day', '?')} [{w.get('severity', '?').upper()}]: "
                f"{w.get('signal', '')} — {w.get('description', '')}"
            )
        pdf.ln(2)

    recs = timeline_analysis.get("recommendations", [])
    if recs:
        pdf.sub_title("Timeline Recommendations")
        for r in recs:
            pdf.bullet(r)
        pdf.ln(2)

    benchmark = timeline_analysis.get("vs_benchmark", {})
    if benchmark:
        pdf.sub_title("Benchmark Comparison")
        pdf.metric_row("Our Avg Response:", f"{benchmark.get('our_avg_response_days', 'N/A')} days")
        pdf.metric_row("Industry Avg:", f"{benchmark.get('industry_avg_response_days', 'N/A')} days")
        pdf.body_text(f"Assessment: {benchmark.get('assessment', 'N/A')}")

    # ── Comparative Analysis ─────────────────────────────────────────────────
    pdf.add_page()
    pdf.section_title("3. Comparative Analysis (vs. Won Deals)")

    rt = comparative_analysis.get("response_time_comparison", {})
    if rt:
        pdf.sub_title("Response Time Comparison")
        pdf.metric_row("Lost Deal Avg:", f"{rt.get('lost_deal_avg_days', 'N/A')} days")
        pdf.metric_row("Won Deals Avg:", f"{rt.get('won_deals_avg_days', 'N/A')} days")
        for diff in rt.get("key_differences", [])[:3]:
            pdf.bullet(diff)
        pdf.ln(2)

    strats = comparative_analysis.get("strategy_differences", [])
    if strats:
        pdf.sub_title("Key Strategy Differences")
        for s in strats[:4]:
            pdf.set_font("Helvetica", "B", 9)
            pdf.cell(0, 6, _clean(f"  {s.get('aspect', '')}"), new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("Helvetica", size=9)
            pdf.bullet(f"Lost approach: {s.get('lost_approach', '')}", indent=14)
            pdf.bullet(f"Won approach: {s.get('won_approach', '')}", indent=14)
            pdf.bullet(f"Recommendation: {s.get('recommendation', '')}", indent=14)
            pdf.ln(1)

    improvements = comparative_analysis.get("improvement_opportunities", [])
    if improvements:
        pdf.sub_title("Improvement Opportunities")
        for imp in improvements[:5]:
            pdf.bullet(imp)
        pdf.ln(2)

    # ── Playbook ─────────────────────────────────────────────────────────────
    pdf.add_page()
    pdf.section_title("4. Actionable Sales Playbook")

    actions = playbook.get("immediate_actions", [])
    if actions:
        pdf.sub_title("Immediate Actions")
        for a in actions[:6]:
            priority_icon = {"high": "[HIGH]", "medium": "[MED]", "low": "[LOW]"}.get(
                a.get("priority", "medium"), "[MED]"
            )
            pdf.bullet(
                f"{priority_icon} {a.get('action', '')} | "
                f"Owner: {a.get('owner', '?')} | Timeline: {a.get('timeline', '?')}"
            )
        pdf.ln(2)

    triggers = playbook.get("trigger_responses", [])
    if triggers:
        pdf.sub_title("Trigger-Based Responses")
        for t in triggers[:4]:
            pdf.set_font("Helvetica", "B", 9)
            pdf.cell(0, 6, f"  IF: {t.get('trigger', '')}", new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("Helvetica", size=9)
            pdf.bullet(f"THEN: {t.get('immediate_action', '')}", indent=14)
            pdf.bullet(f"Follow-up: {t.get('follow_up', '')}", indent=14)
            pdf.bullet(f"Timeframe: {t.get('timeframe', '')}", indent=14)
            pdf.ln(1)

    metrics = playbook.get("success_metrics", [])
    if metrics:
        pdf.sub_title("Success Metrics")
        for m in metrics[:4]:
            pdf.bullet(
                f"{m.get('metric', '')}: Target {m.get('target', 'N/A')} "
                f"({m.get('measurement_frequency', 'Monthly')})"
            )
        pdf.ln(2)

    escalation = playbook.get("escalation_protocols", [])
    if escalation:
        pdf.sub_title("Escalation Protocols")
        for e in escalation[:3]:
            pdf.bullet(
                f"IF: {e.get('condition', '')} → {e.get('action', '')} "
                f"(escalate to: {e.get('escalate_to', '?')})"
            )

    # Output
    buffer = BytesIO()
    pdf_bytes = pdf.output()
    return bytes(pdf_bytes)
