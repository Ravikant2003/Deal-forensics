"""
Page 3: Win Probability Predictor — Score a deal before or during the sales cycle.
"""

import json
import streamlit as st

from utils.visualizer import DealVisualizer
from utils.win_probability import calculate_win_probability
from utils.helpers import Helpers

st.set_page_config(page_title="Win Probability — Deal Forensics AI", page_icon="📈", layout="wide")

st.markdown("""
<style>
  .stApp { background-color: #0F0F1E; color: #CCCCEE; }
  h1, h2, h3 { color: #7EC8E3 !important; }
  [data-testid="metric-container"] {
    background: linear-gradient(135deg,#1E1E3F,#2a2a5a);
    border: 1px solid #4A90D9; border-radius: 12px; padding: 16px;
  }
  [data-testid="stSidebar"] { background: linear-gradient(180deg,#0F0F2E,#1a1a3e); }
  .stButton > button {
    background: linear-gradient(135deg,#4A90D9,#7B52AB);
    color: white; border: none; border-radius: 8px; font-weight: 600;
  }
  .stTextArea textarea { background-color: #1E1E3F; color: #CCCCEE; }
  hr { border-color: #333366; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<h1 style="background:linear-gradient(90deg,#4A90D9,#00C851);
-webkit-background-clip:text;-webkit-text-fill-color:transparent;">
📈 Win Probability Predictor
</h1>
<p style="color:#8888AA;">Score a deal in real-time and get actionable improvement recommendations.</p>
""", unsafe_allow_html=True)
st.markdown("---")

visualizer = DealVisualizer()

# ── Input modes ───────────────────────────────────────────────────────────────

input_mode = st.radio(
    "Input method:",
    ["📝 Form Builder", "📂 Upload JSON", "📋 Paste JSON"],
    horizontal=True,
)

deal = None

if input_mode == "📝 Form Builder":
    st.markdown("### Build Your Deal")
    c1, c2 = st.columns(2)
    with c1:
        company   = st.text_input("Company Name", "Acme Corp")
        industry  = st.selectbox("Industry", ["Technology","SaaS","Enterprise","Retail","E-commerce","Other"])
        value     = st.number_input("Deal Value ($)", min_value=0, value=50000, step=5000)
        loss_reason = st.selectbox("Loss Reason (if known)", ["pricing","technical","timing","value_prop","responsiveness","compliance","unknown"])
    with c2:
        region    = st.text_input("Region", "North America")
        competitors = st.text_input("Competitors (comma-separated)", "Competitor A")
        sales_rep = st.text_input("Sales Rep", "John Doe")

    st.markdown("#### Timeline Events")
    st.caption("Add key events in chronological order.")
    timeline_input = st.text_area(
        "Timeline (one event per line: Day, Event, Details — separated by |)",
        value="1 | Initial contact | Positive response, requested demo\n3 | Product demo | Went well, positive feedback\n7 | Budget discussion | Client mentioned competitor has lower pricing\n10 | No response | Ghosted after pricing discussion",
        height=150,
    )

    timeline = []
    for line in timeline_input.strip().split("\n"):
        parts = [p.strip() for p in line.split("|")]
        if len(parts) == 3:
            try:
                timeline.append({"day": int(parts[0]), "event": parts[1], "details": parts[2]})
            except ValueError:
                pass

    deal = {
        "deal_id":    "PREVIEW-001",
        "company":    company,
        "industry":   industry,
        "value":      value,
        "loss_reason": loss_reason,
        "region":     region,
        "competitors": [c.strip() for c in competitors.split(",") if c.strip()],
        "sales_rep":  sales_rep,
        "timeline":   timeline,
    }

elif input_mode == "📂 Upload JSON":
    uploaded = st.file_uploader("Upload deal JSON", type=["json"])
    if uploaded:
        try:
            deal = json.load(uploaded)
            valid, msg = Helpers.validate_deal_data(deal)
            if not valid:
                st.error(f"Invalid deal JSON: {msg}")
                deal = None
            else:
                st.success(f"Loaded: {deal.get('company','Unknown')}")
        except Exception as e:
            st.error(f"Error reading JSON: {e}")

elif input_mode == "📋 Paste JSON":
    sample = json.dumps({
        "deal_id": "TEST-001","company": "Acme Corp","industry": "Technology",
        "value": 75000,"loss_reason": "pricing","region": "North America",
        "competitors": ["Competitor A"],
        "timeline": [
            {"day":1,"event":"Initial contact","details":"Positive response"},
            {"day":5,"event":"Demo","details":"Went well"},
            {"day":10,"event":"No response","details":"Ghosted after pricing"}
        ]
    }, indent=2)
    pasted = st.text_area("Paste deal JSON:", value=sample, height=220)
    try:
        deal = json.loads(pasted)
        valid, msg = Helpers.validate_deal_data(deal)
        if not valid:
            st.error(f"Invalid: {msg}")
            deal = None
    except Exception as e:
        st.error(f"JSON parse error: {e}")
        deal = None

# ── Score the deal ────────────────────────────────────────────────────────────

if deal:
    st.markdown("---")
    if st.button("🎯 Calculate Win Probability", use_container_width=True):
        result = calculate_win_probability(deal)

        # Gauge + summary
        g1, g2 = st.columns([1, 2])
        with g1:
            fig_gauge = visualizer.create_win_probability_gauge(result.score, result.risk_level)
            st.plotly_chart(fig_gauge, use_container_width=True)
        with g2:
            st.markdown(f"### Score: `{result.score}%` — {result.risk_level} Risk")

            risk_colors = {"Low":"#00C851","Medium":"#FFBB33","High":"#FF4444","Critical":"#8B0000"}
            color = risk_colors.get(result.risk_level, "#FFFFFF")
            st.markdown(
                f'<div style="background:{color}22;border:1px solid {color};border-radius:8px;padding:12px;">'
                f'<b style="color:{color};">{result.risk_level} Risk</b> — '
                f'{"Strong position! Maintain momentum." if result.risk_level=="Low" else "Several risk factors detected. Take action immediately." if result.risk_level in ("High","Critical") else "Moderate risk — address the flagged issues proactively."}'
                f'</div>', unsafe_allow_html=True
            )

            st.markdown("#### 💡 Top 3 Recommendations")
            for rec in result.top_recommendations:
                st.markdown(f"- ✅ {rec}")

        st.markdown("---")

        # Factor chart
        fig_factors = visualizer.create_win_probability_factors_chart(result.factors)
        st.plotly_chart(fig_factors, use_container_width=True)

        # Factor breakdown table
        st.markdown("#### 📊 Factor Breakdown")
        factor_rows = [{
            "Factor":  f["name"],
            "Impact":  f"{f['impact']:+.0f}",
            "Detail":  f["detail"],
            "Sign":    "✅ Positive" if f["impact"] >= 0 else "❌ Negative",
        } for f in sorted(result.factors, key=lambda x: x["impact"])]
        import pandas as pd
        st.dataframe(pd.DataFrame(factor_rows), use_container_width=True)

        # Benchmark section
        st.markdown("#### 📏 How to Get to 70%+")
        deficit = max(0, 70 - result.score)
        if deficit == 0:
            st.success("You're already above the 70% threshold — great position!")
        else:
            neg_factors = [f for f in result.factors if f["impact"] < 0]
            potential_gain = sum(abs(f["impact"]) for f in neg_factors[:3])
            st.info(
                f"Fixing the top 3 risk factors could add ~**{potential_gain:.0f} points**, "
                f"potentially reaching **{min(100, result.score + potential_gain):.0f}%**."
            )
            for f in neg_factors[:3]:
                st.markdown(f"- 🔧 **{f['name']}**: {f['detail']}")
