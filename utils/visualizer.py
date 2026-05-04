"""
Visualizer: Plotly chart factory for Deal Forensics AI dashboard.
Includes timeline, comparative, improvement, win probability, agent trace, and portfolio charts.
"""

import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd


class DealVisualizer:
    COLORS = {
        "positive":  "#00C851",
        "negative":  "#FF4444",
        "warning":   "#FFBB33",
        "neutral":   "#33B5E5",
        "critical":  "#AA66CC",
        "accent":    "#4A90D9",
        "bg":        "rgba(0,0,0,0)",
    }

    PRIORITY_COLORS = {
        "high":   "#FF4444",
        "medium": "#FFBB33",
        "low":    "#00C851",
    }

    # ── Timeline ──────────────────────────────────────────────────────────────

    def create_timeline_visualization(self, deal_data: dict, analysis_results: dict) -> go.Figure:
        """Interactive deal timeline with critical moment and warning overlays."""
        timeline_events = deal_data.get("timeline", [])

        if not timeline_events:
            return self._empty("No timeline data available")

        fig = make_subplots(specs=[[{"secondary_y": True}]])

        events = [e["event"] for e in timeline_events]
        days = [e["day"] for e in timeline_events]
        details = [e["details"] for e in timeline_events]
        colors = self._event_colors(timeline_events, analysis_results)

        fig.add_trace(
            go.Scatter(
                x=days, y=[1] * len(days),
                mode="markers+lines+text",
                marker=dict(size=22, color=colors, line=dict(width=2, color="#1a1a2e")),
                line=dict(color="#4A90D9", width=2, dash="dot"),
                text=events, textposition="top center",
                textfont=dict(size=9, color="#FFFFFF"),
                customdata=details,
                hovertemplate="<b>Day %{x}</b><br><b>%{text}</b><br>%{customdata}<extra></extra>",
                name="Timeline Events",
            ),
            secondary_y=False,
        )

        # Critical moments layer
        critical = analysis_results.get("critical_moments", [])
        if critical:
            fig.add_trace(
                go.Scatter(
                    x=[m["day"] for m in critical],
                    y=[1.15] * len(critical),
                    mode="markers",
                    marker=dict(size=16, color=self.COLORS["critical"], symbol="star"),
                    name="Critical Moments",
                    hovertemplate="<b>CRITICAL: Day %{x}</b><br>%{text}<extra></extra>",
                    text=[m.get("event", "") for m in critical],
                ),
                secondary_y=False,
            )

        # Warning signals layer
        warnings = analysis_results.get("warning_signals", [])
        if warnings:
            fig.add_trace(
                go.Scatter(
                    x=[w["day"] for w in warnings],
                    y=[0.85] * len(warnings),
                    mode="markers",
                    marker=dict(size=14, color=self.COLORS["warning"], symbol="triangle-up"),
                    name="Warning Signals",
                    hovertemplate="<b>WARNING: Day %{x}</b><br>%{text}<extra></extra>",
                    text=[w.get("signal", "") for w in warnings],
                ),
                secondary_y=False,
            )

        # Failure point marker
        fp = analysis_results.get("failure_point", {})
        if fp and fp.get("day"):
            fig.add_vline(
                x=fp["day"],
                line_dash="dash",
                line_color=self.COLORS["negative"],
                annotation_text=f"⚠ Failure Point",
                annotation_position="top",
                annotation_font_color=self.COLORS["negative"],
            )

        fig.update_layout(
            title=dict(
                text=f"Deal Timeline: {deal_data.get('company', 'Unknown')}",
                font=dict(size=16, color="#FFFFFF"),
            ),
            plot_bgcolor="#1E1E3F",
            paper_bgcolor="#1E1E3F",
            font=dict(color="#CCCCEE"),
            xaxis=dict(title="Days", gridcolor="#333355", showgrid=True),
            yaxis=dict(showticklabels=False, range=[0.5, 1.4]),
            showlegend=True,
            legend=dict(bgcolor="#2a2a4a", bordercolor="#4A90D9", borderwidth=1),
            height=380,
            margin=dict(l=20, r=20, t=60, b=40),
        )

        return fig

    def _event_colors(self, events: list, analysis: dict) -> list:
        failure_day = analysis.get("failure_point", {}).get("day")
        colors = []
        for e in events:
            day = e["day"]
            text = (e["event"] + " " + e["details"]).lower()
            if day == failure_day:
                colors.append(self.COLORS["critical"])
            elif any(w in text for w in ["ghost", "lost", "no response", "competitor", "budget concern"]):
                colors.append(self.COLORS["negative"])
            elif any(w in text for w in ["positive", "won", "signed", "approved", "interested"]):
                colors.append(self.COLORS["positive"])
            elif any(w in text for w in ["delay", "concern", "issue", "waiting"]):
                colors.append(self.COLORS["warning"])
            else:
                colors.append(self.COLORS["neutral"])
        return colors

    # ── Comparative ───────────────────────────────────────────────────────────

    def create_comparative_analysis_chart(self, comparative_analysis: dict) -> go.Figure | None:
        """Bar chart comparing avg response times: lost vs won deals."""
        if not comparative_analysis:
            return None

        rt = comparative_analysis.get("response_time_comparison", {})
        lost_avg = rt.get("lost_deal_avg_days", 0)
        won_avg = rt.get("won_deals_avg_days", 0)

        if not lost_avg and not won_avg:
            return None

        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=["Lost Deal", "Won Deals (Avg)"],
            y=[lost_avg, won_avg],
            marker_color=[self.COLORS["negative"], self.COLORS["positive"]],
            text=[f"{lost_avg:.1f}d" if isinstance(lost_avg, (int, float)) else str(lost_avg),
                  f"{won_avg:.1f}d" if isinstance(won_avg, (int, float)) else str(won_avg)],
            textposition="auto",
            textfont=dict(color="white", size=13),
            width=0.4,
        ))

        fig.update_layout(
            title=dict(text="Response Time: Lost vs Won Deals", font=dict(color="#FFFFFF")),
            yaxis_title="Avg Response Time (Days)",
            plot_bgcolor="#1E1E3F",
            paper_bgcolor="#1E1E3F",
            font=dict(color="#CCCCEE"),
            xaxis=dict(gridcolor="#333355"),
            yaxis=dict(gridcolor="#333355"),
            showlegend=False,
            height=320,
            margin=dict(l=20, r=20, t=50, b=30),
        )
        return fig

    # ── Improvement Opportunities ─────────────────────────────────────────────

    def create_improvement_opportunities_chart(self, playbook: dict) -> go.Figure | None:
        """Horizontal bar chart of immediate actions by priority."""
        if not playbook:
            return None

        actions = playbook.get("immediate_actions", [])
        if not actions:
            return None

        priority_map = {"high": 3, "medium": 2, "low": 1}
        labels, values, bar_colors = [], [], []

        for a in actions[:8]:
            label = a.get("action", "")
            label = label[:55] + "…" if len(label) > 55 else label
            p = a.get("priority", "medium").lower()
            labels.append(label)
            values.append(priority_map.get(p, 1))
            bar_colors.append(self.PRIORITY_COLORS.get(p, self.COLORS["neutral"]))

        fig = go.Figure()
        fig.add_trace(go.Bar(
            y=labels, x=values,
            orientation="h",
            marker_color=bar_colors,
            text=[a.get("priority", "").capitalize() for a in actions[:8]],
            textposition="auto",
            textfont=dict(color="white", size=10),
        ))

        fig.update_layout(
            title=dict(text="Immediate Improvement Actions (by Priority)", font=dict(color="#FFFFFF")),
            xaxis=dict(
                tickvals=[1, 2, 3],
                ticktext=["Low", "Medium", "High"],
                gridcolor="#333355",
            ),
            plot_bgcolor="#1E1E3F",
            paper_bgcolor="#1E1E3F",
            font=dict(color="#CCCCEE"),
            yaxis=dict(gridcolor="#333355"),
            showlegend=False,
            height=max(320, len(actions[:8]) * 45 + 80),
            margin=dict(l=20, r=20, t=50, b=30),
        )
        return fig

    # ── Win Probability ───────────────────────────────────────────────────────

    def create_win_probability_gauge(self, score: float, risk_level: str) -> go.Figure:
        """Gauge chart showing win probability score."""
        color_map = {
            "Low": self.COLORS["positive"],
            "Medium": self.COLORS["warning"],
            "High": self.COLORS["negative"],
            "Critical": "#8B0000",
        }
        bar_color = color_map.get(risk_level, self.COLORS["neutral"])

        fig = go.Figure(go.Indicator(
            mode="gauge+number+delta",
            value=score,
            number=dict(suffix="%", font=dict(size=36, color="#FFFFFF")),
            delta=dict(reference=50, increasing=dict(color=self.COLORS["positive"])),
            title=dict(text=f"Win Probability<br><span style='font-size:14px;color:#AAAACC'>{risk_level} Risk</span>"),
            gauge=dict(
                axis=dict(range=[0, 100], tickwidth=1, tickcolor="#CCCCEE"),
                bar=dict(color=bar_color, thickness=0.25),
                bgcolor="#1E1E3F",
                borderwidth=2,
                bordercolor="#4A90D9",
                steps=[
                    dict(range=[0, 30], color="#3D1515"),
                    dict(range=[30, 50], color="#3D2B15"),
                    dict(range=[50, 70], color="#2B3D15"),
                    dict(range=[70, 100], color="#153D1F"),
                ],
                threshold=dict(
                    line=dict(color="#FFFFFF", width=3),
                    thickness=0.75,
                    value=score,
                ),
            ),
        ))

        fig.update_layout(
            paper_bgcolor="#1E1E3F",
            font=dict(color="#CCCCEE"),
            height=320,
            margin=dict(l=30, r=30, t=60, b=20),
        )
        return fig

    def create_win_probability_factors_chart(self, factors: list) -> go.Figure:
        """Horizontal bar chart of win probability factor contributions."""
        if not factors:
            return self._empty("No factor data")

        labels = [f["name"] for f in factors]
        values = [f["impact"] for f in factors]
        colors = [self.COLORS["positive"] if v >= 0 else self.COLORS["negative"] for v in values]

        fig = go.Figure(go.Bar(
            y=labels, x=values,
            orientation="h",
            marker_color=colors,
            text=[f"{v:+.0f}" for v in values],
            textposition="auto",
            textfont=dict(color="white", size=11),
        ))

        fig.update_layout(
            title=dict(text="Win Probability Factors", font=dict(color="#FFFFFF")),
            xaxis=dict(title="Score Impact", gridcolor="#333355", zeroline=True, zerolinecolor="#AAAAAA"),
            plot_bgcolor="#1E1E3F",
            paper_bgcolor="#1E1E3F",
            font=dict(color="#CCCCEE"),
            yaxis=dict(gridcolor="#333355"),
            showlegend=False,
            height=max(300, len(factors) * 40 + 80),
            margin=dict(l=20, r=20, t=50, b=30),
        )
        return fig

    # ── Agent Trace ───────────────────────────────────────────────────────────

    def create_agent_trace_chart(self, agent_trace: list) -> go.Figure:
        """Timeline-style chart showing ReAct tool call steps across all agents."""
        if not agent_trace:
            return self._empty("No agent trace data")

        rows, labels, agents, iterations = [], [], [], []
        agent_colors = {
            "timeline_agent":    "#33B5E5",
            "comparative_agent": "#AA66CC",
            "playbook_agent":    "#00C851",
        }

        for agent_entry in agent_trace:
            agent_name = agent_entry.get("agent", "unknown")
            for step in agent_entry.get("steps", []):
                rows.append({
                    "agent": agent_name.replace("_", " ").title(),
                    "tool": step.get("tool", "unknown"),
                    "iteration": step.get("iteration", 0),
                    "result_preview": step.get("result", "")[:80],
                })

        if not rows:
            return self._empty("No tool calls made during analysis")

        df = pd.DataFrame(rows)

        fig = px.scatter(
            df, x="iteration", y="agent",
            color="tool", size=[15] * len(df),
            hover_data={"result_preview": True, "iteration": True, "agent": True},
            title="ReAct Loop — Tool Calls by Agent",
            color_discrete_sequence=px.colors.qualitative.Plotly,
        )

        fig.update_traces(marker=dict(size=18, line=dict(width=2, color="#1a1a2e")))
        fig.update_layout(
            plot_bgcolor="#1E1E3F",
            paper_bgcolor="#1E1E3F",
            font=dict(color="#CCCCEE"),
            title_font=dict(color="#FFFFFF"),
            xaxis=dict(title="Iteration", gridcolor="#333355", dtick=1),
            yaxis=dict(title="", gridcolor="#333355"),
            legend=dict(bgcolor="#2a2a4a", bordercolor="#4A90D9"),
            height=320,
            margin=dict(l=20, r=20, t=60, b=30),
        )
        return fig

    # ── Portfolio / Dashboard ─────────────────────────────────────────────────

    def create_deal_statistics_chart(self, stats: dict) -> go.Figure:
        """Portfolio overview: win/loss counts + value bar chart."""
        fig = make_subplots(
            rows=1, cols=2,
            subplot_titles=("Deal Count", "Deal Value ($)"),
        )

        fig.add_trace(go.Bar(
            x=["Lost", "Won"],
            y=[stats.get("total_lost_deals", 0), stats.get("total_won_deals", 0)],
            marker_color=[self.COLORS["negative"], self.COLORS["positive"]],
            text=[stats.get("total_lost_deals", 0), stats.get("total_won_deals", 0)],
            textposition="auto",
        ), row=1, col=1)

        fig.add_trace(go.Bar(
            x=["Lost Value", "Won Value"],
            y=[stats.get("total_deal_value_lost", 0), stats.get("total_deal_value_won", 0)],
            marker_color=[self.COLORS["negative"], self.COLORS["positive"]],
            text=[
                f"${stats.get('total_deal_value_lost', 0):,}",
                f"${stats.get('total_deal_value_won', 0):,}",
            ],
            textposition="auto",
        ), row=1, col=2)

        fig.update_layout(
            plot_bgcolor="#1E1E3F",
            paper_bgcolor="#1E1E3F",
            font=dict(color="#CCCCEE"),
            showlegend=False,
            height=320,
            margin=dict(l=20, r=20, t=60, b=30),
        )
        return fig

    def create_loss_reasons_chart(self, loss_reasons: dict) -> go.Figure:
        """Pie chart of loss reasons."""
        if not loss_reasons:
            return self._empty("No loss reason data")

        labels = [r.replace("_", " ").title() for r in loss_reasons.keys()]
        values = list(loss_reasons.values())

        fig = go.Figure(go.Pie(
            labels=labels, values=values,
            hole=0.45,
            marker=dict(colors=px.colors.sequential.Plasma_r),
            textinfo="label+percent",
            textfont=dict(color="white", size=12),
        ))

        fig.update_layout(
            title=dict(text="Loss Reasons Breakdown", font=dict(color="#FFFFFF")),
            paper_bgcolor="#1E1E3F",
            font=dict(color="#CCCCEE"),
            showlegend=True,
            legend=dict(bgcolor="#2a2a4a"),
            height=360,
            margin=dict(l=20, r=20, t=50, b=20),
        )
        return fig

    def create_duration_comparison_chart(self, stats: dict) -> go.Figure:
        """Bar chart comparing avg deal duration: lost vs won."""
        fig = go.Figure(go.Bar(
            x=["Lost Deals", "Won Deals"],
            y=[stats.get("avg_deal_duration_lost", 0), stats.get("avg_deal_duration_won", 0)],
            marker_color=[self.COLORS["negative"], self.COLORS["positive"]],
            text=[
                f"{stats.get('avg_deal_duration_lost', 0):.1f} days",
                f"{stats.get('avg_deal_duration_won', 0):.1f} days",
            ],
            textposition="auto",
            textfont=dict(color="white", size=13),
            width=0.4,
        ))

        fig.update_layout(
            title=dict(text="Avg Deal Duration: Lost vs Won", font=dict(color="#FFFFFF")),
            yaxis_title="Days",
            plot_bgcolor="#1E1E3F",
            paper_bgcolor="#1E1E3F",
            font=dict(color="#CCCCEE"),
            xaxis=dict(gridcolor="#333355"),
            yaxis=dict(gridcolor="#333355"),
            showlegend=False,
            height=300,
            margin=dict(l=20, r=20, t=50, b=30),
        )
        return fig

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _empty(self, message: str) -> go.Figure:
        fig = go.Figure()
        fig.add_annotation(
            text=message,
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            showarrow=False,
            font=dict(size=14, color="#AAAACC"),
        )
        fig.update_layout(
            plot_bgcolor="#1E1E3F",
            paper_bgcolor="#1E1E3F",
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            height=280,
        )
        return fig