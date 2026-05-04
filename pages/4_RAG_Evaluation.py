"""
Page 4: RAG Evaluation — Measure the quality of the hybrid retrieval system.
"""

import streamlit as st
import pandas as pd

from rag.vector_store import HybridDealRetriever
from rag.evaluator import RAGEvaluator
from config.settings import BM25_WEIGHT, VECTOR_WEIGHT, RAG_TOP_K

st.set_page_config(page_title="RAG Evaluation — Deal Forensics AI", page_icon="📋", layout="wide")

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
  .stTextInput input { background-color: #1E1E3F; color: #CCCCEE; }
  hr { border-color: #333366; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<h1 style="background:linear-gradient(90deg,#AA66CC,#4A90D9);
-webkit-background-clip:text;-webkit-text-fill-color:transparent;">
📋 RAG Evaluation
</h1>
<p style="color:#8888AA;">Measure retrieval quality with Hit Rate, MRR, and live query testing.</p>
""", unsafe_allow_html=True)
st.markdown("---")

# ── Sidebar controls ──────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("### ⚙️ Retriever Settings")
    bm25_w  = st.slider("BM25 Weight",   0.0, 1.0, BM25_WEIGHT,   0.1, help="Keyword search weight")
    vec_w   = st.slider("Vector Weight", 0.0, 1.0, VECTOR_WEIGHT, 0.1, help="Semantic search weight")
    top_k   = st.slider("Top-K Results", 1, 10, RAG_TOP_K)
    st.info(f"Combined weight: {bm25_w + vec_w:.1f} (ideally = 1.0)")
    run_eval = st.button("🧪 Run Full Evaluation", use_container_width=True)


@st.cache_resource(show_spinner="Initializing retriever...")
def get_retriever():
    r = HybridDealRetriever()
    r.initialize()
    return r


retriever = get_retriever()
evaluator = RAGEvaluator(retriever)

# ── About section ─────────────────────────────────────────────────────────────

with st.expander("ℹ️ About This Evaluation", expanded=False):
    st.markdown("""
**Traditional Metrics:**
- **Hit Rate @ k**: Fraction of queries where the expected deal appears in the top-k results.
- **MRR (Mean Reciprocal Rank)**: Average of 1/rank across all queries. Higher = better.

**Retrieval Architecture:**
- Vector store: ChromaDB with `all-MiniLM-L6-v2` embeddings  
- Keyword store: BM25 in-memory index over all deal documents  
- Fusion: LangChain `EnsembleRetriever` with Reciprocal Rank Fusion  
- Query Expansion: Automatic synonym expansion for better retrieval
- Reranking: Optional CrossEncoder reranking (enable with `USE_RERANKER=true` in .env)
    """)

# ── Full benchmark evaluation ─────────────────────────────────────────────────

if run_eval:
    st.markdown("### 🧪 Ground-Truth Evaluation Results")
    with st.spinner("Running evaluation across all test queries..."):
        report = evaluator.evaluate(k=top_k, bm25_weight=bm25_w, vector_weight=vec_w)

    rep = report.to_dict()

    # KPI cards
    k1, k2, k3 = st.columns(3)
    with k1:
        hit_color = "normal" if rep["hit_rate"] >= 0.6 else "inverse"
        st.metric("Hit Rate @ k", f"{rep['hit_rate']*100:.0f}%",
                  delta=f"{'✅ Good' if rep['hit_rate']>=0.6 else '⚠️ Needs tuning'}")
    with k2:
        st.metric("MRR", f"{rep['mrr']:.3f}",
                  delta=f"{'✅ Good' if rep['mrr']>=0.5 else '⚠️ Needs tuning'}")
    with k3:
        st.metric("Hits / Total", f"{rep['hits']} / {rep['total_queries']}")

    # Interpretation
    if rep["hit_rate"] >= 0.8:
        st.success("🏆 Excellent retrieval quality! The hybrid RAG is performing well.")
    elif rep["hit_rate"] >= 0.5:
        st.warning("⚠️ Moderate retrieval quality. Try adjusting BM25/vector weights.")
    else:
        st.error("❌ Low retrieval quality. Consider expanding the dataset or tuning weights.")

    st.markdown("---")

    # Per-query results
    st.markdown("#### Per-Query Results")
    rows = []
    for r in rep["results"]:
        rows.append({
            "Query":    r["query"][:60] + "…" if len(r["query"]) > 60 else r["query"],
            "Expected": r["expected"],
            "Retrieved":  ", ".join(r["retrieved"][:3]),
            "Hit":       "✅" if r["hit"] else "❌",
            "Rank":      r["rank"] if r["rank"] else "—",
            "RR":        f"{r['reciprocal_rank']:.3f}",
        })

    df = pd.DataFrame(rows)
    st.dataframe(
        df.style.apply(
            lambda col: ["background-color: #1a4a1a" if v == "✅" else "background-color: #4a1a1a" if v == "❌" else "" for v in col],
            subset=["Hit"]
        ),
        use_container_width=True,
    )

    # Weight comparison tip
    st.markdown("---")
    st.markdown("#### 💡 Weight Tuning Guidance")
    col_a, col_b = st.columns(2)
    with col_a:
        st.info("**Increase BM25 weight** when your queries use specific terminology (competitor names, exact event names).")
    with col_b:
        st.info("**Increase Vector weight** when your queries are conceptual or semantic (e.g., 'deal with fast close').")

st.markdown("---")

# ── Live query tester ─────────────────────────────────────────────────────────

st.markdown("### 🔎 Live Query Tester")
st.caption("Test any query against the retrieval system and see what gets returned.")

qcol1, qcol2, qcol3 = st.columns([3, 1, 1])
with qcol1:
    custom_query = st.text_input("Search query:", "Enterprise deal legal compliance won")
with qcol2:
    query_type = st.selectbox("Deal type:", ["won", "lost", "any"])
with qcol3:
    query_k = st.number_input("Top-k:", min_value=1, max_value=10, value=3)

if st.button("🔍 Search", use_container_width=True):
    with st.spinner("Searching..."):
        deal_type_arg = None if query_type == "any" else query_type
        result = evaluator.evaluate_query(custom_query, deal_type=deal_type_arg or "won", k=query_k)

    st.markdown(f"**{len(result['results'])} result(s) for:** `{custom_query}`")
    for i, r in enumerate(result["results"], 1):
        with st.expander(f"Result {i}: {r.get('company','?')} ({r.get('deal_id','?')}) — {r.get('type','?').upper()}"):
            c1, c2, c3 = st.columns(3)
            c1.metric("Deal ID",  r.get("deal_id","?"))
            c2.metric("Industry", r.get("industry","?"))
            c3.metric("Type",     r.get("type","?").upper())
            st.markdown(f"**Snippet:** {r.get('snippet','')}")

st.markdown("---")
st.caption("Hybrid retrieval: ChromaDB (vector) + BM25 (keyword) via LangChain EnsembleRetriever")
