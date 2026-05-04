"""
RAG quality evaluator: measures Hit Rate, MRR, and other traditional IR metrics.
"""

import json
from dataclasses import dataclass, field
from typing import Optional, List

from rag.vector_store import HybridDealRetriever


@dataclass
class EvalResult:
    query: str
    expected_deal_id: str
    retrieved_ids: list[str]
    hit: bool
    reciprocal_rank: float
    rank: Optional[int]


@dataclass
class EvalReport:
    results: list[EvalResult] = field(default_factory=list)

    @property
    def hit_rate(self) -> float:
        if not self.results:
            return 0.0
        return sum(1 for r in self.results if r.hit) / len(self.results)

    @property
    def mrr(self) -> float:
        if not self.results:
            return 0.0
        return sum(r.reciprocal_rank for r in self.results) / len(self.results)

    def to_dict(self) -> dict:
        return {
            "hit_rate": round(self.hit_rate, 3),
            "mrr": round(self.mrr, 3),
            "total_queries": len(self.results),
            "hits": sum(1 for r in self.results if r.hit),
            "results": [
                {
                    "query": r.query,
                    "expected": r.expected_deal_id,
                    "retrieved": r.retrieved_ids,
                    "hit": r.hit,
                    "rank": r.rank,
                    "reciprocal_rank": round(r.reciprocal_rank, 3),
                }
                for r in self.results
            ],
        }


# Ground-truth evaluation set: (query, expected_deal_id, deal_type)
# Queries use company name + industry + win reason to match vector store content
EVAL_SET = [
    ("Cancity Retail superior product features", "WD-0001", "won"),
    ("Isdom Medical industry expertise", "WD-0002", "won"),
    ("Cancity Retail strong relationship", "WD-0003", "won"),
    ("Codehow Software industry expertise", "WD-0004", "won"),
    ("Hatfan Services best value proposition", "WD-0005", "won"),
    ("Ron-tech Medical best value proposition", "WD-0006", "won"),
    ("J-Texon Retail best value proposition", "WD-0007", "won"),
    ("Cheers Entertainment fast implementation", "WD-0008", "won"),
]


class RAGEvaluator:
    """Evaluates the quality of the hybrid RAG retrieval system."""

    def __init__(self, retriever: Optional[HybridDealRetriever] = None):
        self.retriever = retriever or HybridDealRetriever()

    def evaluate(self, k: int = 3, bm25_weight: float = 0.4, vector_weight: float = 0.6) -> EvalReport:
        """
        Run evaluation on the ground-truth query set.

        Args:
            k: Number of results to retrieve per query
            bm25_weight: Weight for BM25 retriever in ensemble
            vector_weight: Weight for vector retriever in ensemble

        Returns:
            EvalReport with hit rate, MRR, and per-query results
        """
        if not self.retriever._initialized:
            self.retriever.initialize()

        report = EvalReport()

        for query, expected_id, deal_type in EVAL_SET:
            docs = self.retriever.search(query=query, deal_type=deal_type, n_results=k)
            retrieved_ids = [d.metadata.get("deal_id", "") for d in docs]

            hit = expected_id in retrieved_ids
            rank = (retrieved_ids.index(expected_id) + 1) if hit else None
            rr = 1.0 / rank if rank else 0.0

            report.results.append(
                EvalResult(
                    query=query,
                    expected_deal_id=expected_id,
                    retrieved_ids=retrieved_ids,
                    hit=hit,
                    reciprocal_rank=rr,
                    rank=rank,
                )
            )

        return report

    def evaluate_query(self, query: str, deal_type: str = "won", k: int = 3) -> dict:
        """Evaluate a single custom query."""
        if not self.retriever._initialized:
            self.retriever.initialize()

        docs = self.retriever.search(query=query, deal_type=deal_type, n_results=k)
        return {
            "query": query,
            "deal_type": deal_type,
            "k": k,
            "results": [
                {
                    "deal_id": d.metadata.get("deal_id"),
                    "company": d.metadata.get("company"),
                    "industry": d.metadata.get("industry"),
                    "type": d.metadata.get("type"),
                    "snippet": d.page_content[:200] + "...",
                }
                for d in docs
            ],
        }
