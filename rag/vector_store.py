"""
Hybrid RAG vector store: ChromaDB (semantic) + BM25 (keyword) via EnsembleRetriever.
Includes query expansion, reranking, and improved document processing.
"""

import os
# Disable ChromaDB telemetry before import
os.environ["CHROMA_TELEMETRY"] = "False"
os.environ["ANONYMIZED_TELEMETRY"] = "False"

import json
import re
from typing import Optional, List, Dict, Tuple
from langchain_core.documents import Document

import chromadb
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.retrievers import BM25Retriever
from langchain_classic.retrievers.ensemble import EnsembleRetriever

# Optional: Reranking (install with: pip install sentence-transformers)
try:
    from sentence_transformers import CrossEncoder
    RERANKER_AVAILABLE = True
except ImportError:
    RERANKER_AVAILABLE = False
    CrossEncoder = None

from config.settings import (
    CHROMA_PATH,
    CHROMA_COLLECTION,
    EMBEDDING_MODEL,
    BM25_WEIGHT,
    VECTOR_WEIGHT,
    RAG_TOP_K,
    SAMPLE_DEALS_PATH,
)


def _load_deals() -> dict:
    with open(SAMPLE_DEALS_PATH, "r") as f:
        return json.load(f)


def _deal_to_document(deal: dict, deal_type: str) -> Document:
    """Convert a deal dict to a LangChain Document with rich page_content."""
    timeline_text = " | ".join(
        f"Day {e['day']}: {e['event']} — {e['details']}"
        for e in deal.get("timeline", [])
    )

    reason_key = "loss_reason" if deal_type == "lost" else "win_reason"
    reason = deal.get(reason_key, "unknown")

    # Determine value tier
    value = deal.get("value", 0)
    if value >= 100000:
        value_tier = "enterprise"
    elif value >= 50000:
        value_tier = "mid-market"
    else:
        value_tier = "small"

    # Create comprehensive content with key phrases for better retrieval
    key_phrases = _extract_key_phrases(deal, deal_type)
    
    page_content = (
        f"{deal_type.upper()} Deal | Company: {deal['company']} | "
        f"Industry: {deal.get('industry', 'Unknown')} | "
        f"Value: ${value:,} ({value_tier}) | "
        f"Reason: {reason} | "
        f"Competitors: {', '.join(deal.get('competitors', []))} | "
        f"Region: {deal.get('region', 'Unknown')} | "
        f"Sales Rep: {deal.get('sales_rep', 'Unknown')} | "
        f"Key Phrases: {key_phrases} | "
        f"Timeline: {timeline_text}"
    )

    metadata = {
        "type": deal_type,
        "deal_id": deal["deal_id"],
        "company": deal["company"],
        "industry": deal.get("industry", ""),
        "value": value,
        "value_tier": value_tier,
        "reason": reason,
        "region": deal.get("region", ""),
        "sales_rep": deal.get("sales_rep", ""),
        "competitors": ", ".join(deal.get("competitors", [])),
    }

    return Document(page_content=page_content, metadata=metadata)


def _extract_key_phrases(deal: dict, deal_type: str) -> str:
    """Extract key phrases from deal for better semantic search."""
    phrases = []
    
    # Add loss/win reason
    reason_key = "loss_reason" if deal_type == "lost" else "win_reason"
    if deal.get(reason_key):
        phrases.append(deal[reason_key].replace("_", " "))
    
    # Add competitor names
    if deal.get("competitors"):
        phrases.extend(deal["competitors"])
    
    # Add industry
    if deal.get("industry"):
        phrases.append(deal["industry"])
    
    # Add key timeline events (first and last events)
    timeline = deal.get("timeline", [])
    if timeline:
        phrases.append(timeline[0].get("event", ""))
        if len(timeline) > 1:
            phrases.append(timeline[-1].get("event", ""))
    
    return " ".join(phrases)


class HybridDealRetriever:
    """
    Hybrid retriever combining ChromaDB semantic search and BM25 keyword search.
    Uses LangChain's EnsembleRetriever for Reciprocal Rank Fusion (RRF).
    Includes query expansion and optional reranking.
    """

    def __init__(self):
        self.embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
        self._vectorstore: Optional[Chroma] = None
        self._documents: list[Document] = []
        self._ensemble: Optional[EnsembleRetriever] = None
        self._initialized = False
        self._reranker: Optional[CrossEncoder] = None
        self._init_reranker()

    def _init_reranker(self):
        """Initialize reranker if available."""
        if RERANKER_AVAILABLE and os.getenv("USE_RERANKER", "false").lower() == "true":
            try:
                self._reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
            except Exception:
                self._reranker = None

    def _build_documents(self) -> list[Document]:
        data = _load_deals()
        docs = []
        for deal in data.get("lost_deals", []):
            docs.append(_deal_to_document(deal, "lost"))
        for deal in data.get("won_deals", []):
            docs.append(_deal_to_document(deal, "won"))
        return docs

    def initialize(self, force_rebuild: bool = False):
        """Initialize or load the vector store and build the ensemble retriever."""
        docs = self._build_documents()
        self._documents = docs

        # ChromaDB / LangChain Chroma
        self._vectorstore = Chroma(
            collection_name=CHROMA_COLLECTION,
            embedding_function=self.embeddings,
            persist_directory=CHROMA_PATH,
        )

        # Only re-index if collection is empty or forced
        existing_count = self._vectorstore._collection.count()
        if existing_count == 0 or force_rebuild:
            # Clear and re-add
            self._vectorstore.delete_collection()
            self._vectorstore = Chroma.from_documents(
                documents=docs,
                embedding=self.embeddings,
                collection_name=CHROMA_COLLECTION,
                persist_directory=CHROMA_PATH,
            )

        # BM25 retriever (in-memory, built from all documents)
        bm25_retriever = BM25Retriever.from_documents(docs)
        bm25_retriever.k = RAG_TOP_K

        vector_retriever = self._vectorstore.as_retriever(
            search_kwargs={"k": RAG_TOP_K}
        )

        # Ensemble: BM25 + Vector with configurable weights
        self._ensemble = EnsembleRetriever(
            retrievers=[bm25_retriever, vector_retriever],
            weights=[BM25_WEIGHT, VECTOR_WEIGHT],
        )

        self._initialized = True

    def _expand_query(self, query: str, industry: str = "", deal_type: str = "") -> str:
        """
        Expand query with synonyms and related terms for better retrieval.
        """
        # Query expansion mappings
        expansions = {
            "pricing": "pricing cost budget price quote proposal",
            "competitor": "competitor competition rival alternative",
            "lost": "lost failed missed unsuccessful",
            "won": "won successful closed deal",
            "enterprise": "enterprise large corporation big",
            "technical": "technical integration api development",
            "legal": "legal compliance regulation contract",
            "timeline": "timeline duration days time response",
        }
        
        expanded = query.lower()
        for key, synonyms in expansions.items():
            if key in expanded:
                expanded = f"{expanded} {synonyms}"
        
        # Add metadata hints
        if industry:
            expanded = f"{expanded} industry:{industry}"
        if deal_type:
            expanded = f"{expanded} type:{deal_type}"
        
        return expanded

    def search(
        self,
        query: str,
        deal_type: Optional[str] = "won",
        industry: Optional[str] = "",
        n_results: int = RAG_TOP_K,
    ) -> list[Document]:
        """
        Perform hybrid BM25 + vector search with query expansion and optional reranking.

        Args:
            query: Search query string
            deal_type: Filter by 'won' or 'lost' (None = no filter)
            industry: Optional industry substring filter
            n_results: Max documents to return after filtering

        Returns:
            List of matching Document objects
        """
        if not self._initialized:
            self.initialize()

        # Expand query for better retrieval
        expanded_query = self._expand_query(query, industry or "", deal_type or "")
        
        # Retrieve more candidates for reranking
        retrieve_k = min(n_results * 3, 20)  # Get 3x results for reranking
        results = self._ensemble.invoke(expanded_query)

        # Post-filter by deal_type and industry
        filtered = []
        for doc in results:
            meta = doc.metadata
            if deal_type and meta.get("type") != deal_type:
                continue
            if industry and industry.lower() not in meta.get("industry", "").lower():
                continue
            filtered.append(doc)

        # If filtering removed everything, fall back to unfiltered
        if not filtered and results:
            filtered = [d for d in results if not deal_type or d.metadata.get("type") == deal_type]
            if not filtered:
                filtered = results

        # Rerank if reranker is available
        if self._reranker and filtered:
            filtered = self._rerank(query, filtered, top_k=n_results)
        else:
            filtered = filtered[:n_results]

        return filtered

    def _rerank(self, query: str, docs: list[Document], top_k: int = 3) -> list[Document]:
        """Rerank documents using CrossEncoder for better relevance."""
        if not self._reranker or not docs:
            return docs[:top_k]
        
        try:
            pairs = [[query, doc.page_content] for doc in docs]
            scores = self._reranker.predict(pairs)
            scored_docs = list(zip(docs, scores))
            scored_docs.sort(key=lambda x: x[1], reverse=True)
            return [doc for doc, score in scored_docs[:top_k]]
        except Exception:
            return docs[:top_k]


class DealVectorStore:
    """
    Legacy-compatible interface wrapping HybridDealRetriever.
    Used by main.py initialization.
    """

    def __init__(self):
        self._retriever = HybridDealRetriever()

    def initialize(self, force_rebuild: bool = False):
        self._retriever.initialize(force_rebuild=force_rebuild)
        total = len(self._retriever._documents)
        print(f"✅ Vector store ready — {total} deals indexed (hybrid BM25 + vector)")

    def search_similar_deals(
        self, query: str, deal_type: str = "won", n_results: int = 3
    ) -> dict:
        """Legacy interface: returns ChromaDB-style result dict."""
        docs = self._retriever.search(query=query, deal_type=deal_type, n_results=n_results)
        return {
            "documents": [[d.page_content for d in docs]],
            "metadatas": [[d.metadata for d in docs]],
            "ids": [[d.metadata.get("deal_id", str(i)) for i, d in enumerate(docs)]],
        }