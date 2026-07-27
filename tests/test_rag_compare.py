"""Unit and integration tests for rag_compare (offline hash + heuristic backends)."""

from __future__ import annotations

from pathlib import Path

import pytest

from rag_compare.config import EmbeddingBackend, LLMBackend, Settings, VectorBackend
from rag_compare.embeddings import HashEmbedder
from rag_compare.evaluation.metrics import mean_reciprocal_rank, percentile
from rag_compare.llm import HeuristicLLM
from rag_compare.models import (
    Document,
    RetrievalResult,
    RetrievalTrace,
    RetrieverKind,
    ScoredDocument,
    VectorBackendKind,
)
from rag_compare.pipeline.ingest import build_parent_child_documents, chunk_text, load_corpus
from rag_compare.retrievers.factory import build_retriever_bundle, get_retriever
from rag_compare.service import RagCompareService
from rag_compare.stores.faiss_store import FaissVectorStore


ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "data" / "corpus"


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        corpus_dir=CORPUS,
        index_dir=tmp_path / "indexes",
        eval_dir=ROOT / "data" / "eval",
        embedding_backend=EmbeddingBackend.HASH,
        llm_backend=LLMBackend.HEURISTIC,
        embedding_dim=64,
        default_vector_backend=VectorBackend.FAISS,
        top_k=3,
        child_chunk_size=220,
        child_chunk_overlap=40,
        parent_chunk_size=600,
        multi_query_count=3,
    )


def test_chunk_text_respects_size_and_overlap():
    text = "alpha " * 80
    chunks = chunk_text(text, chunk_size=50, overlap=10)
    assert len(chunks) >= 2
    assert all(len(c) <= 50 for c in chunks)


def test_load_corpus_parses_front_matter():
    docs = load_corpus(CORPUS)
    assert len(docs) >= 7
    topics = {d.metadata.get("topic") for d in docs}
    assert "retrieval" in topics
    assert "vector_db" in topics


def test_hash_embedder_is_deterministic_and_normalized():
    emb = HashEmbedder(dimension=32)
    a = emb.embed_query("faiss chroma comparison")
    b = emb.embed_query("faiss chroma comparison")
    assert a == b
    assert abs(sum(x * x for x in a) - 1.0) < 1e-6


def test_faiss_roundtrip_and_filter(tmp_path: Path):
    store = FaissVectorStore(dimension=32, persist_dir=tmp_path, index_name="t")
    emb = HashEmbedder(32)
    docs = [
        Document(content="faiss similarity search internals", metadata={"topic": "vector_db"}),
        Document(content="parent document retrieval pattern", metadata={"topic": "retrieval"}),
    ]
    vectors = emb.embed_documents([d.content for d in docs])
    store.upsert(docs, vectors)
    hits = store.similarity_search(
        emb.embed_query("faiss search"),
        top_k=2,
        metadata_filter={"topic": "vector_db"},
    )
    assert hits
    assert hits[0][0].metadata["topic"] == "vector_db"


def test_parent_child_links():
    parents_src = [Document(content="A" * 500 + "\n\n" + "B" * 500, metadata={"topic": "ops"})]
    parents, children = build_parent_child_documents(
        parents_src,
        parent_chunk_size=400,
        child_chunk_size=120,
        child_overlap=20,
    )
    assert parents
    assert children
    assert all(c.parent_id in parents for c in children)


def test_all_strategies_retrieve(settings: Settings):
    source = load_corpus(settings.corpus_dir)
    parents, children = build_parent_child_documents(
        source,
        parent_chunk_size=settings.parent_chunk_size,
        child_chunk_size=settings.child_chunk_size,
        child_overlap=settings.child_chunk_overlap,
    )
    bundle = build_retriever_bundle(
        vector_backend=VectorBackend.FAISS,
        settings=settings,
        namespace="test_faiss",
        parents=parents,
    )
    vectors = bundle.embedder.embed_documents([c.content for c in children])
    bundle.child_store.upsert(children, vectors)

    query = "advanced parent document retrieval strategy"
    for kind in RetrieverKind:
        result = get_retriever(bundle, kind).retrieve(query, top_k=3)
        assert result.documents
        assert result.latency_ms >= 0
        assert result.trace.strategy == kind


def test_compare_report(settings: Settings):
    service = RagCompareService(settings)
    service.ingest(VectorBackend.FAISS)
    labels = {
        "How do multi-query retrievers improve recall?": ["02_multi_query.md"],
        "Compare FAISS and Chroma for production RAG": ["05_faiss_vs_chroma.md"],
    }
    report = service.compare(
        list(labels.keys()),
        top_k=5,
        relevant_ids_by_query=labels,
    )
    assert report.query_count == 2
    assert len(report.strategies) == 4
    assert report.winner_by_latency is not None
    assert any(item.hit_rate_at_k > 0 for item in report.strategies)
    assert "Evaluated 4" in report.summary


def test_rag_answer(settings: Settings):
    service = RagCompareService(settings)
    service.ingest(VectorBackend.FAISS)
    answer = service.answer(
        "What should I monitor for retriever evaluation?",
        strategy=RetrieverKind.VECTOR,
        top_k=3,
    )
    assert answer.answer
    assert answer.citations
    assert answer.total_latency_ms >= answer.generation_latency_ms


def test_mrr_and_percentile_helpers():
    assert percentile([1, 2, 3, 4], 50) == 2.5
    result = RetrievalResult(
        query="q",
        documents=[
            ScoredDocument(
                document=Document(id="a", content="x"),
                score=0.9,
                rank=1,
            ),
            ScoredDocument(
                document=Document(id="b", content="y"),
                score=0.8,
                rank=2,
            ),
        ],
        latency_ms=1.0,
        trace=RetrievalTrace(
            strategy=RetrieverKind.VECTOR,
            vector_backend=VectorBackendKind.FAISS,
        ),
    )
    mrr = mean_reciprocal_rank([result], [{"b"}])
    assert mrr == 0.5


def test_heuristic_llm_self_query_plan():
    llm = HeuristicLLM()
    raw = llm.complete("self-query metadata filter planner", "advanced faiss vector notes")
    assert "filter" in raw


def test_chroma_backend_optional(settings: Settings, tmp_path: Path):
    pytest.importorskip("chromadb")
    settings = settings.model_copy(update={"index_dir": tmp_path / "idx"})
    service = RagCompareService(settings)
    status = service.ingest(VectorBackend.CHROMA)
    assert status["ready"] is True
    result = service.retrieve("FAISS versus Chroma tradeoffs", strategy=RetrieverKind.VECTOR)
    assert result.documents
