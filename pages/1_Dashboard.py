"""
Page 1: Portfolio Dashboard — Historical deal statistics and trend analysis.
"""

import streamlit as st
import pandas as pd

from rag.data_processor import DataProcessor
from utils.visualizer import DealVisualizer
from utils.helpers import Helpers

st.set_page_config(page_title="Dashboard — Deal Forensics AI", page_icon="📊", layout="wide")

st.markdown("""
<style>
  .stApp { background-color: #0F0F1E; color: #CCCCEE; }
  h1, h2, h3 { color: #7EC8E3 !important; }
  [data-testid="metric-container"] {
    background: linear-gradient(135deg, #1E1E3F, #2a2a5a);
    border: 1px solid #4A90D9; border-radius: 12px; padding: 16px;
  }
  [data-testid="stSidebar"] { background: linear-gradient(180deg,#0F0F2E,#1a1a3e); }
  hr { border-color: #333366; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<h1 style="background:linear-gradient(90deg,#4A90D9,#AA66CC);
           -webkit-background-clip:text; -webkit-text-fill-color:transparent;">
  📊 Portfolio Dashboard
</h1>
<p style="color:#8888AA;">Historical deal statistics and performance trends.</p>
""", unsafe_allow_html=True)

st.markdown("---")


@st.cache_resource
def get_processor():
    return DataProcessor()


@st.cache_resource
def get_visualizer():
    return DealVisualizer()


processor  = get_processor()
visualizer = get_visualizer()
stats      = processor.get_deal_statistics()
lost_deals = processor.get_all_lost_deals()
won_deals  = processor.get_all_won_deals()

# ── KPI row ──────────────────────────────────────────────────────────────────

k1, k2, k3, k4, k5 = st.columns(5)
with k1:
    st.metric("Total Deals Analyzed", stats["total_lost_deals"] + stats["total_won_deals"])
with k2:
    st.metric("Lost Deals", stats["total_lost_deals"])
with k3:
    st.metric("Won Deals", stats["total_won_deals"])
with k4:
    st.metric("Win Rate", f"{stats['win_rate'] * 100:.0f}%")
with k5:
    revenue_at_risk = stats["total_deal_value_lost"]
    st.metric("Revenue Lost", Helpers.format_currency(revenue_at_risk))

st.markdown("---")

# ── Charts row 1 ─────────────────────────────────────────────────────────────

c1, c2 = st.columns(2)
with c1:
    st.plotly_chart(
        visualizer.create_deal_statistics_chart(stats),
        use_container_width=True,
    )
with c2:
    st.plotly_chart(
        visualizer.create_loss_reasons_chart(stats["common_loss_reasons"]),
        use_container_width=True,
    )

# ── Charts row 2 ─────────────────────────────────────────────────────────────

c3, c4 = st.columns(2)
with c3:
    st.plotly_chart(
        visualizer.create_duration_comparison_chart(stats),
        use_container_width=True,
    )
with c4:
    # Losses by industry bar chart
    import plotly.graph_objects as go
    by_industry = stats.get("losses_by_industry", {})
    if by_industry:
        fig = go.Figure(go.Bar(
            x=list(by_industry.keys()),
            y=list(by_industry.values()),
            marker_color="#4A90D9",
            text=list(by_industry.values()),
            textposition="auto",
        ))
        fig.update_layout(
            title=dict(text="Losses by Industry", font=dict(color="#FFFFFF")),
            plot_bgcolor="#1E1E3F", paper_bgcolor="#1E1E3F",
            font=dict(color="#CCCCEE"),
            xaxis=dict(gridcolor="#333355"),
            yaxis=dict(gridcolor="#333355", title="Count"),
            showlegend=False, height=300,
            margin=dict(l=20, r=20, t=50, b=30),
        )
        st.plotly_chart(fig, use_container_width=True)

st.markdown("---")

# ── Deal tables ───────────────────────────────────────────────────────────────

tab_lost, tab_won = st.tabs(["❌ Lost Deals", "✅ Won Deals"])

with tab_lost:
    rows = []
    for d in lost_deals:
        rows.append({
            "Deal ID":      d["deal_id"],
            "Company":      d["company"],
            "Value ($)":    d.get("value", 0),
            "Industry":     d.get("industry", ""),
            "Loss Reason":  d.get("loss_reason", "").replace("_", " ").title(),
            "Duration (d)": Helpers.get_deal_duration(d),
            "Region":       d.get("region", ""),
            "Sales Rep":    d.get("sales_rep", ""),
        })
    df = pd.DataFrame(rows)
    st.dataframe(df.style.format({"Value ($)": "${:,.0f}"}), use_container_width=True)

with tab_won:
    rows = []
    for d in won_deals:
        rows.append({
            "Deal ID":      d["deal_id"],
            "Company":      d["company"],
            "Value ($)":    d.get("value", 0),
            "Industry":     d.get("industry", ""),
            "Win Reason":   d.get("win_reason", "").replace("_", " ").title(),
            "Duration (d)": Helpers.get_deal_duration(d),
            "Region":       d.get("region", ""),
            "Sales Rep":    d.get("sales_rep", ""),
        })
    df = pd.DataFrame(rows)
    st.dataframe(df.style.format({"Value ($)": "${:,.0f}"}), use_container_width=True)

# ── Sales rep leaderboard ────────────────────────────────────────────────────

st.markdown("---")
st.markdown("### 👥 Sales Rep Performance")

rep_stats: dict = {}
for d in lost_deals + won_deals:
    rep = d.get("sales_rep", "Unknown")
    outcome = "won" if d in won_deals else "lost"
    if rep not in rep_stats:
        rep_stats[rep] = {"won": 0, "lost": 0, "total_value": 0}
    rep_stats[rep][outcome] += 1
    rep_stats[rep]["total_value"] += d.get("value", 0)

rep_rows = []
for rep, data in rep_stats.items():
    total = data["won"] + data["lost"]
    rep_rows.append({
        "Sales Rep":   rep,
        "Won":         data["won"],
        "Lost":        data["lost"],
        "Win Rate":    f"{data['won'] / total * 100:.0f}%" if total else "0%",
        "Total Value": f"${data['total_value']:,}",
    })

st.dataframe(pd.DataFrame(rep_rows), use_container_width=True)
