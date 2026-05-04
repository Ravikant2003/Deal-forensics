"""
RAG-based tools for searching similar deals using hybrid BM25 + vector retrieval.
Includes query expansion and reranking for better results.
"""

from langchain_core.tools import tool

# Cache the retriever to avoid reinitialization
_retriever_cache = None


def _get_retriever():
    """Get or create cached retriever instance."""
    global _retriever_cache
    if _retriever_cache is None:
        from rag.vector_store import HybridDealRetriever
        _retriever_cache = HybridDealRetriever()
    return _retriever_cache


@tool
def search_similar_deals(
    query: str,
    industry: str = "",
    deal_type: str = "won",
    n_results: str = "3",
) -> str:
    """Search for similar deals using hybrid BM25 + vector retrieval with query expansion.

    Args:
        query: Rich search query describing the deal (company name, industry, loss reason, etc.)
        industry: Optional industry to filter results (Technology, SaaS, Enterprise, Retail, E-commerce)
        deal_type: Type of deals to search — 'won' or 'lost' (default: 'won')
        n_results: Number of results to return as a string (default: "3")

    Returns:
        Formatted string with matching deal summaries including timeline and win/loss reason.
    """
    try:
        retriever = _get_retriever()
        
        # Safely cast n_results to int
        try:
            k = int(n_results)
        except (ValueError, TypeError):
            k = 3

        results = retriever.search(
            query=query,
            deal_type=deal_type,
            industry=industry,
            n_results=k,
        )

        if not results:
            return "No similar deals found matching the search criteria."

        formatted = []
        for i, doc in enumerate(results, 1):
            meta = doc.metadata if hasattr(doc, "metadata") else {}
            formatted.append(
                f"--- DEAL {i} ---\n"
                f"Company: {meta.get('company', 'Unknown')} | "
                f"Type: {meta.get('type', deal_type).upper()} | "
                f"Industry: {meta.get('industry', 'Unknown')}\n"
                f"Deal ID: {meta.get('deal_id', 'Unknown')}\n"
                f"{doc.page_content[:300]}...\n"
            )

        return "\n".join(formatted)

    except Exception as e:
        return f"Error searching deals: {str(e)}. Ensure ChromaDB is populated by running the app first."
