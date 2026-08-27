import pytest

from cqr_product_pipeline.rag.collections import all_ingest_files
from cqr_product_pipeline.rag.ingest import ingest_corpus
from cqr_product_pipeline.rag.retriever import CQRKnowledgeRetriever, retrieve_for_feasibility
from cqr_product_pipeline.schemas.models import ConceptCandidate


@pytest.fixture(scope="module")
def indexed_chroma(tmp_path_factory):
    chroma_path = tmp_path_factory.mktemp("chroma")
    counts = ingest_corpus(chroma_path=chroma_path, rebuild=True)
    assert sum(counts.values()) > 0
    return chroma_path


@pytest.fixture(scope="module")
def retriever(indexed_chroma):
    return CQRKnowledgeRetriever(chroma_path=str(indexed_chroma))


def test_ingest_files_exist():
    files = all_ingest_files()
    assert len(files) >= 6
    collections = {name for name, _path, _doc in files}
    assert collections >= {"brand", "catalog", "product_spec", "process"}


def test_retrieve_for_feasibility_liberator_concept(retriever):
    concept = ConceptCandidate(
        concept_id="test-a",
        name="Liberator Lite Summer Cargo",
        line_recommendation="Liberator",
        garment_type="cargo pants",
        target_tpo="hot weather field",
        usp_hypothesis="lightweight ripstop cargo with reduced pocket stack",
        keywords=["Liberator", "pocket", "gusset", "PRODUCT_DEV", "Purpose Above All"],
    )
    bundle = retrieve_for_feasibility(concept, retriever=retriever, k_per_collection=4)

    assert bundle.concept_id == "test-a"
    assert len(bundle.blocks) > 0

    collections = {b.collection for b in bundle.blocks}
    assert "brand" in collections
    assert "product_spec" in collections

    source_paths = {b.source_path for b in bundle.blocks}
    assert any("PRODUCT_DEV_SPEC" in p or "CQR_BRAND_CONCEPT" in p for p in source_paths)


def test_retriever_returns_blocks_per_collection(retriever):
    blocks = retriever.retrieve_all_collections(
        "Liberator cargo pocket gusset heat TLP125",
        k_per_collection=2,
    )
    assert len(blocks) >= 2
    assert all(b.excerpt for b in blocks)
