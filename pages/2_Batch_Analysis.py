"""
Page 2: Batch Analysis — Run forensic analysis on all lost deals at once.
"""

import json
import streamlit as st
import pandas as pd

from rag.data_processor import DataProcessor
from rag.vector_store import DealVectorStore
from graph.workflow import build_graph
from graph.state import AgentState
from utils.helpers import Helpers
from utils.win_probability import calculate_win_probability

st.set_page_config(page_title="Batch Analysis — Deal Forensics AI", page_icon="🔍", layout="wide")

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
  hr { border-color: #333366; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<h1 style="background:linear-gradient(90deg,#4A90D9,#AA66CC);
-webkit-background-clip:text;-webkit-text-fill-color:transparent;">
🔍 Batch Analysis
</h1>
<p style="color:#8888AA;">Run forensic analysis across all lost deals simultaneously.</p>
""", unsafe_allow_html=True)
st.markdown("---")


@st.cache_resource
def get_processor():
    return DataProcessor()

@st.cache_resource(show_spinner="Initializing vector store...")
def get_vector_store():
    vs = DealVectorStore()
    vs.initialize()
    return vs

@st.cache_resource(show_spinner="Building LangGraph workflow...")
def get_graph():
    return build_graph()


ok, missing = Helpers.setup_environment()
if not ok:
    st.error(f"Missing: **{', '.join(missing)}**. Set GROQ_API_KEY in your .env file.")
    st.stop()

processor    = get_processor()
vector_store = get_vector_store()
graph        = get_graph()
lost_deals   = processor.get_all_lost_deals()

with st.sidebar:
    st.markdown("### Batch Settings")
    max_deals = st.slider("Max deals to analyze", 1, len(lost_deals), min(3, len(lost_deals)))
    run_batch = st.button("Run Batch Analysis", use_container_width=True)

overview_rows = [{
    "Deal ID":       d["deal_id"],
    "Company":       d["company"],
    "Value":         f"${d.get('value',0):,}",
    "Industry":      d.get("industry",""),
    "Loss Reason":   d.get("loss_reason","").replace("_"," ").title(),
    "Win Prob (Pre)":f"{calculate_win_probability(d).score:.0f}%",
} for d in lost_deals]

st.markdown(f"### Queued Deals ({len(lost_deals)} total)")
st.dataframe(pd.DataFrame(overview_rows), use_container_width=True)

if run_batch:
    st.markdown("---")
    results_table = []
    all_results   = {}
    deals_to_run  = lost_deals[:max_deals]
    overall_prog  = st.progress(0)

    for i, deal in enumerate(deals_to_run):
        deal = processor.enrich_deal_with_crm(deal)
        st.markdown(f"#### {i+1}/{len(deals_to_run)}: **{deal['company']}**")
        dp = st.progress(0)
        final_state: AgentState = {
            "messages":[],"deal_id":deal["deal_id"],"lost_deal":deal,
            "timeline_analysis":None,"comparative_analysis":None,"playbook":None,
            "agent_trace":[],"similar_won_deals":[],"errors":[],"next":"",
        }
        try:
            ac = 0
            for step_output in graph.stream(final_state):
                node = list(step_output.keys())[0]
                final_state = {**final_state, **step_output[node]}
                if node in ("timeline_agent","comparative_agent","playbook_agent"):
                    ac += 1
                    dp.progress(int(ac/3*100))
            dp.progress(100)
            ta = final_state.get("timeline_analysis",{}) or {}
            ca = final_state.get("comparative_analysis",{}) or {}
            pb = final_state.get("playbook",{}) or {}
            wp = calculate_win_probability(deal, ta)
            results_table.append({
                "Deal ID": deal["deal_id"],"Company": deal["company"],
                "Loss Reason": deal.get("loss_reason","").replace("_"," ").title(),
                "Timeline Score": ta.get("timeline_score","N/A"),
                "Confidence %": ca.get("confidence_score","N/A"),
                "Win Prob %": wp.score,"Risk Level": wp.risk_level,
                "Expected Impact": pb.get("expected_impact","N/A"),"Status":"✅",
            })
            all_results[deal["deal_id"]] = {"ta":ta,"ca":ca,"pb":pb}
            fp = ta.get("failure_point",{})
            if fp:
                st.error(f"Failure: Day {fp.get('day','?')} — {fp.get('event','')} | {fp.get('reason','')}")
            imps = ca.get("improvement_opportunities",[])
            if imps:
                st.info(f"Top opportunity: {imps[0]}")
            Helpers.save_analysis_results(deal["deal_id"],{"deal_id":deal["deal_id"],"ta":ta,"ca":ca,"pb":pb})
        except Exception as e:
            dp.progress(100)
            results_table.append({
                "Deal ID":deal["deal_id"],"Company":deal["company"],"Loss Reason":"",
                "Timeline Score":"Err","Confidence %":"Err","Win Prob %":0,
                "Risk Level":"Err","Expected Impact":"Err","Status":f"❌ {str(e)[:40]}",
            })
            st.error(f"Error: {e}")
        overall_prog.progress(int((i+1)/len(deals_to_run)*100))
        st.markdown("---")

    st.markdown("## Batch Results Summary")
    if results_table:
        df = pd.DataFrame(results_table)
        st.dataframe(df, use_container_width=True)
        successful = [r for r in results_table if r["Status"]=="✅"]
        if successful:
            nums = [r["Win Prob %"] for r in successful if isinstance(r["Win Prob %"],(int,float))]
            if nums:
                st.metric("Average Win Probability", f"{sum(nums)/len(nums):.1f}%")
            hi_risk = [r for r in successful if r["Risk Level"] in ("Critical","High")]
            if hi_risk:
                st.warning(f"{len(hi_risk)} deal(s) at HIGH/CRITICAL risk — prioritize these.")
        st.download_button(
            "Download Results (JSON)",
            data=json.dumps({k:{"ta_score":v["ta"].get("timeline_score"),"imps":v["ca"].get("improvement_opportunities",[])} for k,v in all_results.items()},indent=2),
            file_name="batch_results.json",
            mime="application/json",
            use_container_width=True,
        )
