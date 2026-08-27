"""CQR knowledge retriever for feasibility scoring."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed

import chromadb
from chromadb.utils import embedding_functions

from cqr_product_pipeline.config.settings import Settings, get_settings
from cqr_product_pipeline.rag.collections import COLLECTIONS
from cqr_product_pipeline.schemas.models import ConceptCandidate, EvidenceBlock, RAGContextBundle


def _build_feasibility_query(concept: ConceptCandidate) -> str:
    parts = [
        concept.name,
        concept.line_recommendation or "",
        concept.garment_type or "",
        concept.target_tpo or "",
        concept.usp_hypothesis or "",
        " ".join(concept.keywords),
    ]
    return " ".join(p.strip() for p in parts if p.strip())


def _dedupe_blocks(blocks: list[EvidenceBlock]) -> list[EvidenceBlock]:
    seen: set[tuple[str, str]] = set()
    unique: list[EvidenceBlock] = []
    for block in sorted(blocks, key=lambda b: b.relevance, reverse=True):
        key = (block.source_path, block.excerpt[:120])
        if key in seen:
            continue
        seen.add(key)
        unique.append(block)
    return unique


class CQRKnowledgeRetriever:
    def __init__(
        self,
        *,
        chroma_path: str | None = None,
        settings: Settings | None = None,
    ) -> None:
        settings = settings or get_settings()
        self.settings = settings
        self.client = chromadb.PersistentClient(path=str(chroma_path or settings.chroma_path))
        self.embed_fn = embedding_functions.DefaultEmbeddingFunction()

    def _get_collection(self, name: str):
        return self.client.get_or_create_collection(
            name=name,
            embedding_function=self.embed_fn,
        )

    def retrieve_collection(
        self,
        collection: str,
        query: str,
        *,
        k: int | None = None,
    ) -> list[EvidenceBlock]:
        k = k or self.settings.k_per_collection
        try:
            col = self._get_collection(collection)
        except Exception:
            return []

        if col.count() == 0:
            return []

        results = col.query(query_texts=[query], n_results=min(k, col.count()))
        blocks: list[EvidenceBlock] = []
        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        for doc, meta, dist in zip(documents, metadatas, distances, strict=False):
            if not doc or not meta:
                continue
            relevance = max(0.0, 1.0 - (dist or 1.0))
            blocks.append(
                EvidenceBlock(
                    source_path=str(meta.get("source_path", "")),
                    excerpt=doc[:600],
                    relevance=relevance,
                    collection=str(meta.get("collection", collection)),
                )
            )
        return blocks

    def retrieve_all_collections(
        self,
        query: str,
        *,
        k_per_collection: int | None = None,
    ) -> list[EvidenceBlock]:
        k = k_per_collection or self.settings.k_per_collection
        blocks: list[EvidenceBlock] = []

        with ThreadPoolExecutor(max_workers=len(COLLECTIONS)) as pool:
            futures = {
                pool.submit(self.retrieve_collection, spec.name, query, k=k): spec.name
                for spec in COLLECTIONS
            }
            for future in as_completed(futures):
                blocks.extend(future.result())

        return _dedupe_blocks(blocks)


def retrieve_for_feasibility(
    concept: ConceptCandidate,
    *,
    retriever: CQRKnowledgeRetriever | None = None,
    k_per_collection: int = 4,
) -> RAGContextBundle:
    """
    1) concept.keywords + line + garment_type로 hybrid query 생성
    2) brand / catalog / product_spec / process 4-way parallel retrieve
    3) MMR dedupe
    4) Feasibility prompt에 주입할 EvidenceBlock[] 반환
    """
    retriever = retriever or CQRKnowledgeRetriever()
    query = _build_feasibility_query(concept)
    blocks = retriever.retrieve_all_collections(query, k_per_collection=k_per_collection)
    return RAGContextBundle(concept_id=concept.concept_id, query=query, blocks=blocks)
