"""
Deal Forensics AI — Main Streamlit Application
Multi-agent forensic analysis of lost sales deals using LangGraph + Groq.
"""

# Disable ChromaDB telemetry BEFORE any imports
import os
os.environ["ANONYMIZED_TELEMETRY"] = "False"
os.environ["CHROMA_TELEMETRY"] = "False"

import json
import streamlit as st

from rag.data_processor import DataProcessor
from rag.vector_store import DealVectorStore
from graph.workflow import build_graph
from graph.state import AgentState
from utils.visualizer import DealVisualizer
from utils.helpers import Helpers
from utils.pdf_exporter import generate_playbook_pdf
from utils.win_probability import calculate_win_probability

# ── Page config ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Deal Forensics AI",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS (dark premium theme) ──────────────────────────────────────────

st.markdown("""
<style>
  /* Global dark background */
  .stApp { background-color: #0F0F1E; color: #CCCCEE; }
  
  /* Metric cards */
  [data-testid="metric-container"] {
    background: linear-gradient(135deg, #1E1E3F, #2a2a5a);
    border: 1px solid #4A90D9;
    border-radius: 12px;
    padding: 16px;
  }

  /* Headers */
  h1, h2, h3 { color: #7EC8E3 !important; }

  /* Sidebar */
  [data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0F0F2E, #1a1a3e);
    border-right: 1px solid #333366;
  }

  /* Buttons */
  .stButton > button {
    background: linear-gradient(135deg, #4A90D9, #7B52AB);
    color: white;
    border: none;
    border-radius: 8px;
    font-weight: 600;
    transition: transform 0.2s;
  }
  .stButton > button:hover { transform: scale(1.03); }

  /* Expanders */
  .streamlit-expanderHeader {
    background-color: #1E1E3F;
    border-radius: 8px;
    color: #7EC8E3 !important;
  }

  /* Divider */
  hr { border-color: #333366; }

  /* Selectbox / inputs */
  .stSelectbox > div > div, .stTextInput > div > div {
    background-color: #1E1E3F;
    border-color: #4A90D9;
    color: #CCCCEE;
  }

  /* Agent trace badge */
  .trace-badge {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 12px;
    font-size: 12px;
    font-weight: bold;
    margin: 2px;
  }
  .badge-timeline    { background: #1a4a6e; color: #33B5E5; }
  .badge-comparative { background: #4a1a6e; color: #AA66CC; }
  .badge-playbook    { background: #1a6e3a; color: #00C851; }

  /* Download button */
  .stDownloadButton > button {
    background: linear-gradient(135deg, #00C851, #007A32);
    color: white;
    border: none;
    border-radius: 8px;
    font-weight: 600;
  }
</style>
""", unsafe_allow_html=True)


# ── Environment check ─────────────────────────────────────────────────────────

@st.cache_resource
def check_env():
    ok, missing = Helpers.setup_environment()
    return ok, missing


# ── Cached resource initialization ───────────────────────────────────────────

@st.cache_resource(show_spinner="🔧 Initializing vector store...")
def init_vector_store():
    vs = DealVectorStore()
    vs.initialize()
    return vs


@st.cache_resource(show_spinner="🔧 Building LangGraph workflow...")
def init_graph():
    return build_graph()


@st.cache_resource
def init_data_processor():
    return DataProcessor()


@st.cache_resource
def init_visualizer():
    return DealVisualizer()


# ── Helper: render agent trace ────────────────────────────────────────────────

def render_agent_trace(agent_trace: list):
    """Display the ReAct reasoning steps in an expander."""
    if not agent_trace:
        return

    badge_classes = {
        "timeline_agent":    "badge-timeline",
        "comparative_agent": "badge-comparative",
        "playbook_agent":    "badge-playbook",
    }

    total_calls = sum(len(a.get("steps", [])) for a in agent_trace)
    with st.expander(f"🤖 Agent Trace — {total_calls} tool call(s) across {len(agent_trace)} agent(s)", expanded=False):
        for agent_entry in agent_trace:
            agent_name = agent_entry.get("agent", "unknown")
            steps = agent_entry.get("steps", [])
            badge_cls = badge_classes.get(agent_name, "badge-timeline")
            display_name = agent_name.replace("_", " ").title()

            st.markdown(
                f'<span class="trace-badge {badge_cls}">🤖 {display_name}</span>',
                unsafe_allow_html=True,
            )

            if not steps:
                st.caption("  No tool calls — agent reasoned from context only.")
            else:
                for step in steps:
                    col_a, col_b = st.columns([1, 3])
                    with col_a:
                        st.caption(f"Iter {step.get('iteration', '?')} · `{step.get('tool', '?')}`")
                    with col_b:
                        st.caption(f"Args: `{step.get('args', '')[:80]}`")
                        st.caption(f"↳ {step.get('result', '')[:150]}")
            st.markdown("---")


# ── Main app ──────────────────────────────────────────────────────────────────

def main():
    # Header
    st.markdown("""
    <div style="text-align:center; padding: 10px 0 20px 0;">
      <h1 style="font-size:2.4rem; background: linear-gradient(90deg,#4A90D9,#AA66CC,#00C851);
                 -webkit-background-clip:text; -webkit-text-fill-color:transparent;">
        🔍 Deal Forensics AI
      </h1>
      <p style="color:#8888AA; font-size:1rem; margin-top:-10px;">
        Multi-Agent Post-Mortem Analysis · Powered by Groq + LangGraph
      </p>
    </div>
    """, unsafe_allow_html=True)

    # Environment check
    env_ok, missing = check_env()
    if not env_ok:
        st.error(
            f"❌ Missing environment variable(s): **{', '.join(missing)}**\n\n"
            "Create a `.env` file with your `GROQ_API_KEY`. "
            "Get a free key at https://console.groq.com"
        )
        st.stop()

    # Initialize resources
    vector_store = init_vector_store()
    graph = init_graph()
    data_processor = init_data_processor()
    visualizer = init_visualizer()

    # ── Sidebar ───────────────────────────────────────────────────────────────

    with st.sidebar:
        st.markdown("### 🔍 Deal Forensics AI")
        st.markdown("---")

        st.subheader("Select Deal")
        lost_deals = data_processor.get_all_lost_deals()
        deal_options = {d["deal_id"]: f"{d['deal_id']} — {d['company']}" for d in lost_deals}
        selected_id = st.selectbox("Choose a lost deal:", list(deal_options.keys()), format_func=lambda x: deal_options[x])

        # Upload custom deal
        st.markdown("---")
        st.subheader("📂 Upload Custom Deal")
        uploaded = st.file_uploader("Upload deal JSON file", type=["json"])
        if uploaded:
            try:
                custom_deal = json.load(uploaded)
                valid, msg = Helpers.validate_deal_data(custom_deal)
                if valid:
                    selected_id = custom_deal["deal_id"]
                    lost_deals.append(custom_deal)
                    deal_options[selected_id] = f"{selected_id} — {custom_deal['company']} (Custom)"
                    st.success(f"✅ Loaded: {custom_deal['company']}")
                else:
                    st.error(f"Invalid deal: {msg}")
            except Exception as e:
                st.error(f"Error reading file: {e}")

        st.markdown("---")
        st.markdown("### ⚙️ Settings")
        show_raw_json = st.toggle("Show raw JSON outputs", value=False)
        show_trace = st.toggle("Show ReAct agent trace", value=True)

        run_btn = st.button("🚀 Run Forensic Analysis", use_container_width=True)

        st.markdown("---")
        st.caption("🏗 Built with LangGraph · Groq · ChromaDB · Streamlit")

    # ── Deal overview (always visible) ────────────────────────────────────────

    lost_deal = data_processor.get_lost_deal_by_id(selected_id)
    if not lost_deal and uploaded:
        lost_deal = custom_deal

    if not lost_deal:
        st.warning("Please select a valid deal.")
        return

    # Enrich with CRM data
    lost_deal = data_processor.enrich_deal_with_crm(lost_deal)

    # Deal overview cards
    st.markdown("### 📋 Deal Overview")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("🏢 Company", lost_deal["company"])
    with col2:
        st.metric("💰 Deal Value", Helpers.format_currency(lost_deal.get("value", 0)))
    with col3:
        # BUG FIX: use actual duration days, not event count
        duration = Helpers.get_deal_duration(lost_deal)
        st.metric("📅 Duration", f"{duration} days")
    with col4:
        st.metric("⚔️ Competitors", ", ".join(lost_deal.get("competitors", ["None"])))

    col5, col6, col7, col8 = st.columns(4)
    with col5:
        st.metric("🏭 Industry", lost_deal.get("industry", "Unknown"))
    with col6:
        st.metric("❌ Loss Reason", lost_deal.get("loss_reason", "Unknown").replace("_", " ").title())
    with col7:
        st.metric("👤 Sales Rep", lost_deal.get("sales_rep", "Unknown"))
    with col8:
        st.metric("🌍 Region", lost_deal.get("region", "Unknown"))

    st.markdown("---")

    # Quick win probability preview
    wp_result = calculate_win_probability(lost_deal)
    wp_col1, wp_col2 = st.columns([1, 3])
    with wp_col1:
        fig_gauge = visualizer.create_win_probability_gauge(wp_result.score, wp_result.risk_level)
        st.plotly_chart(fig_gauge, use_container_width=True)
    with wp_col2:
        st.markdown(f"#### 📊 Pre-Analysis Win Probability: `{wp_result.score}%` ({wp_result.risk_level} Risk)")
        st.markdown("**Top Risk Factors:**")
        for f in [x for x in wp_result.factors if x["impact"] < 0][:3]:
            st.markdown(f"- 🔴 **{f['name']}**: {f['detail']}")
        st.markdown("**Quick Wins:**")
        for r in wp_result.top_recommendations:
            st.markdown(f"- 💡 {r}")

    # ── Analysis (runs on button click) ──────────────────────────────────────

    if run_btn:
        st.markdown("---")
        st.markdown("## 🔬 Forensic Analysis")

        # Build initial state
        initial_state: AgentState = {
            "messages":             [],
            "deal_id":              lost_deal["deal_id"],
            "lost_deal":            lost_deal,
            "timeline_analysis":    None,
            "comparative_analysis": None,
            "playbook":             None,
            "agent_trace":          [],
            "similar_won_deals":    [],
            "errors":               [],
            "next":                 "",
        }

        # Stream the graph — show progress live
        progress = st.progress(0, text="🤖 Supervisor routing...")
        status_placeholder = st.empty()
        final_state = initial_state

        # Map tool names to display names
        agent_steps = ["call_timeline_agent", "call_comparative_agent", "call_playbook_agent"]
        step_labels = {
            "call_timeline_agent":    "🔍 Timeline Agent — analyzing deal progression...",
            "call_comparative_agent": "📊 Comparative Agent — retrieving similar won deals via hybrid RAG...",
            "call_playbook_agent":    "🎯 Playbook Agent — synthesizing actionable recommendations...",
            "supervisor": "🤖 Supervisor routing...",
        }
        completed = 0

        try:
            for step_output in graph.stream(initial_state):
                node_name = list(step_output.keys())[0]
                state_chunk = step_output[node_name]
                final_state = {**final_state, **state_chunk}

                # Track agent completions
                if node_name in ["call_timeline_agent", "call_comparative_agent", "call_playbook_agent"]:
                    completed += 1
                    pct = int((completed / len(agent_steps)) * 100)
                    progress.progress(pct, text=step_labels.get(node_name, node_name))
                    display_name = node_name.replace("call_", "").replace("_", " ").title()
                    status_placeholder.info(f"✅ **{display_name}** completed ({pct}%)")
                elif node_name == "supervisor":
                    status_placeholder.warning(f"🤖 Supervisor deciding next step...")

            progress.progress(100, text="✅ Analysis complete!")
            status_placeholder.success("🎉 All agents completed successfully!")

        except Exception as e:
            st.error(f"❌ Analysis error: {str(e)}")
            st.exception(e)
            return

        timeline_analysis    = final_state.get("timeline_analysis", {})
        comparative_analysis = final_state.get("comparative_analysis", {})
        playbook             = final_state.get("playbook", {})
        agent_trace          = final_state.get("agent_trace", [])

        # ReAct trace
        if show_trace:
            render_agent_trace(agent_trace)
            fig_trace = visualizer.create_agent_trace_chart(agent_trace)
            st.plotly_chart(fig_trace, use_container_width=True)

        st.markdown("---")

        # ── Analysis columns ──────────────────────────────────────────────────

        col_left, col_right = st.columns(2)

        with col_left:
            st.markdown("### 📊 Timeline Analysis")
            if isinstance(timeline_analysis, dict) and not timeline_analysis.get("parse_error"):
                fp = timeline_analysis.get("failure_point", {})
                if fp:
                    st.error(
                        f"🚨 **Failure Point — Day {fp.get('day', '?')}**: "
                        f"{fp.get('event', '')} | *{fp.get('reason', '')}* | "
                        f"Recoverable: {fp.get('recoverable', 'unknown')}"
                    )

                score = timeline_analysis.get("timeline_score")
                if score:
                    color = "🟢" if score >= 7 else "🟡" if score >= 4 else "🔴"
                    st.metric("Timeline Management Score", f"{color} {score}/10")

                warns = timeline_analysis.get("warning_signals", [])
                if warns:
                    st.markdown("**⚠️ Warning Signals:**")
                    for w in warns[:4]:
                        severity_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(
                            w.get("severity", "medium"), "⚪"
                        )
                        st.markdown(
                            f"- {severity_icon} **Day {w.get('day', '?')}** "
                            f"[{w.get('severity', '').upper()}]: {w.get('signal', '')} — {w.get('description', '')}"
                        )

                recs = timeline_analysis.get("recommendations", [])
                if recs:
                    st.markdown("**💡 Recommendations:**")
                    for r in recs[:3]:
                        st.markdown(f"- {r}")

                benchmark = timeline_analysis.get("vs_benchmark", {})
                if benchmark:
                    st.info(
                        f"📏 **Benchmark**: Our avg response: "
                        f"{benchmark.get('our_avg_response_days', 'N/A')}d vs industry avg: "
                        f"{benchmark.get('industry_avg_response_days', 'N/A')}d — "
                        f"{benchmark.get('assessment', '')}"
                    )

                if show_raw_json:
                    with st.expander("Raw Timeline JSON"):
                        st.json(timeline_analysis)
            else:
                st.warning("Timeline analysis returned an unexpected format.")

            st.markdown("#### 📈 Timeline Visualization")
            fig_timeline = visualizer.create_timeline_visualization(lost_deal, timeline_analysis)
            st.plotly_chart(fig_timeline, use_container_width=True)

        with col_right:
            st.markdown("### 🔍 Comparative Analysis")
            if isinstance(comparative_analysis, dict) and not comparative_analysis.get("parse_error"):
                rt = comparative_analysis.get("response_time_comparison", {})
                if rt:
                    lost_avg = rt.get("lost_deal_avg_days", "N/A")
                    won_avg  = rt.get("won_deals_avg_days", "N/A")
                    st.metric(
                        "Response Time Gap",
                        f"{lost_avg}d vs {won_avg}d",
                        delta=f"{round(float(str(won_avg).replace('N/A','0')) - float(str(lost_avg).replace('N/A','0')), 1)}d"
                        if isinstance(lost_avg, (int, float)) and isinstance(won_avg, (int, float)) else None,
                        delta_color="inverse",
                    )

                strats = comparative_analysis.get("strategy_differences", [])
                if strats:
                    st.markdown("**🎯 Key Strategy Differences:**")
                    for s in strats[:3]:
                        with st.expander(f"🔄 {s.get('aspect', 'Strategy Gap')}"):
                            c1, c2 = st.columns(2)
                            with c1:
                                st.markdown(f"❌ **Lost:** {s.get('lost_approach', '')}")
                            with c2:
                                st.markdown(f"✅ **Won:** {s.get('won_approach', '')}")
                            st.success(f"💡 Recommendation: {s.get('recommendation', '')}")

                imps = comparative_analysis.get("improvement_opportunities", [])
                if imps:
                    st.markdown("**🚀 Improvement Opportunities:**")
                    for imp in imps[:4]:
                        st.markdown(f"- {imp}")

                confidence = comparative_analysis.get("confidence_score")
                if confidence:
                    st.metric("Analysis Confidence", f"{confidence}%")

                if show_raw_json:
                    with st.expander("Raw Comparative JSON"):
                        st.json(comparative_analysis)
            else:
                st.warning("Comparative analysis returned an unexpected format.")

            st.markdown("#### 📊 Response Time Comparison")
            fig_comp = visualizer.create_comparative_analysis_chart(comparative_analysis)
            if fig_comp:
                st.plotly_chart(fig_comp, use_container_width=True)

        # ── Playbook ──────────────────────────────────────────────────────────

        st.markdown("---")
        st.markdown("### 🎯 Generated Playbook")

        if isinstance(playbook, dict) and not playbook.get("parse_error"):
            # Summary metrics
            pb_col1, pb_col2, pb_col3 = st.columns(3)
            with pb_col1:
                st.metric("Confidence Score", f"{playbook.get('confidence_score', 'N/A')}%")
            with pb_col2:
                st.metric("Expected Impact", playbook.get("expected_impact", "N/A"))
            with pb_col3:
                n_actions = len(playbook.get("immediate_actions", []))
                st.metric("Immediate Actions", n_actions)

            # Improvement chart
            fig_improvements = visualizer.create_improvement_opportunities_chart(playbook)
            if fig_improvements:
                st.plotly_chart(fig_improvements, use_container_width=True)

            # Immediate actions
            actions = playbook.get("immediate_actions", [])
            if actions:
                st.markdown("#### 📋 Immediate Actions")
                for i, action in enumerate(actions[:6], 1):
                    priority = action.get("priority", "medium")
                    icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(priority, "⚪")
                    with st.container():
                        a1, a2, a3, a4 = st.columns([4, 1, 1, 1])
                        with a1:
                            st.markdown(f"**{i}. {action.get('action', '')}**")
                        with a2:
                            st.caption(f"👤 {action.get('owner', '?')}")
                        with a3:
                            st.caption(f"{icon} {priority}")
                        with a4:
                            st.caption(f"⏰ {action.get('timeline', '?')}")
                    st.divider()

            # Trigger responses
            triggers = playbook.get("trigger_responses", [])
            if triggers:
                st.markdown("#### ⚡ Trigger-Based Responses")
                for t in triggers[:4]:
                    with st.expander(f"🔔 IF: {t.get('trigger', 'Unknown trigger')}"):
                        st.success(f"**Immediate Action:** {t.get('immediate_action', '')}")
                        st.info(f"**Timeframe:** {t.get('timeframe', '')}  |  **Follow-up:** {t.get('follow_up', '')}")

            # Competitor strategies
            comp_strats = playbook.get("competitor_strategies", [])
            if comp_strats:
                st.markdown("#### ⚔️ Competitor Counter-Strategies")
                for cs in comp_strats[:3]:
                    with st.expander(f"🏴 vs. {cs.get('competitor', 'Competitor')}"):
                        st.warning(f"**Counter-Strategy:** {cs.get('counter_strategy', '')}")
                        msgs = cs.get("key_messages", [])
                        if msgs:
                            for msg in msgs[:3]:
                                st.markdown(f"- 💬 {msg}")

            # Success metrics
            metrics = playbook.get("success_metrics", [])
            if metrics:
                st.markdown("#### 📈 Success Metrics")
                m_cols = st.columns(min(len(metrics[:4]), 4))
                for i, metric in enumerate(metrics[:4]):
                    with m_cols[i]:
                        st.metric(
                            label=metric.get("metric", "Metric"),
                            value=metric.get("target", "N/A"),
                            help=f"Measured: {metric.get('measurement_frequency', 'N/A')}",
                        )

            if show_raw_json:
                with st.expander("Raw Playbook JSON"):
                    st.json(playbook)

        # ── Overall confidence & PDF export ──────────────────────────────────

        st.markdown("---")
        st.markdown("### 📊 Analysis Summary")
        sum_col1, sum_col2, sum_col3 = st.columns(3)

        analysis_results = {
            "timeline_analysis":    timeline_analysis,
            "comparative_analysis": comparative_analysis,
            "playbook":             playbook,
        }
        overall_confidence = Helpers.calculate_confidence_score(analysis_results)

        with sum_col1:
            tl_score = timeline_analysis.get("timeline_score") if isinstance(timeline_analysis, dict) else None
            st.metric("Timeline Score", f"{tl_score}/10" if tl_score else "N/A")
        with sum_col2:
            st.metric("Overall Confidence", f"{overall_confidence}%")
        with sum_col3:
            impact = playbook.get("expected_impact", "N/A") if isinstance(playbook, dict) else "N/A"
            st.metric("Expected Impact", impact)

        # Win probability post-analysis
        if isinstance(timeline_analysis, dict):
            wp_post = calculate_win_probability(lost_deal, timeline_analysis)
            st.markdown(f"#### 🎯 Post-Analysis Win Probability: `{wp_post.score}%` ({wp_post.risk_level} Risk)")
            fig_factors = visualizer.create_win_probability_factors_chart(wp_post.factors)
            st.plotly_chart(fig_factors, use_container_width=True)

        # PDF export
        st.markdown("---")
        st.markdown("### 📄 Export Report")
        try:
            pdf_bytes = generate_playbook_pdf(lost_deal, timeline_analysis, comparative_analysis, playbook)
            st.download_button(
                label="⬇️ Download Playbook as PDF",
                data=pdf_bytes,
                file_name=f"deal_forensics_{lost_deal['deal_id']}_{lost_deal['company'].replace(' ', '_')}.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
        except Exception as e:
            st.warning(f"PDF export failed: {e}")

        # Save full results to disk
        Helpers.save_analysis_results(lost_deal["deal_id"], {
            "deal_id":              lost_deal["deal_id"],
            "company":              lost_deal["company"],
            "timeline_analysis":    timeline_analysis,
            "comparative_analysis": comparative_analysis,
            "playbook":             playbook,
        })


if __name__ == "__main__":
    main()