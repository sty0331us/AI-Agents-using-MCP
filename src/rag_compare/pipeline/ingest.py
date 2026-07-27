"""Corpus loading, parent/child chunking, and index population."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from rag_compare.config import Settings, get_settings
from rag_compare.embeddings import Embedder
from rag_compare.logging_setup import get_logger
from rag_compare.models import Document, new_id
from rag_compare.stores.base import VectorStore

logger = get_logger(__name__)


@dataclass(frozen=True)
class IngestResult:
    parents: dict[str, Document]
    children: list[Document]
    upserted: int


def load_corpus(corpus_dir: Path) -> list[Document]:
    if not corpus_dir.exists():
        raise FileNotFoundError(f"corpus directory not found: {corpus_dir}")
    documents: list[Document] = []
    patterns = ("*.md", "*.txt")
    files: list[Path] = []
    for pattern in patterns:
        files.extend(sorted(corpus_dir.rglob(pattern)))
    for path in files:
        text = path.read_text(encoding="utf-8").strip()
        if not text:
            continue
        meta = _parse_front_matter_and_body(text)
        body = meta.pop("_body")
        meta["source"] = path.name
        meta.setdefault("path", str(path.relative_to(corpus_dir)))
        documents.append(Document(content=body, metadata=meta))
    if not documents:
        raise ValueError(f"no documents found under {corpus_dir}")
    logger.info("corpus_loaded", extra={"count": len(documents), "dir": str(corpus_dir)})
    return documents


def _parse_front_matter_and_body(text: str) -> dict:
    """Minimal YAML-ish front matter: key: value lines between --- fences."""
    meta: dict = {"_body": text}
    if not text.startswith("---"):
        return meta
    parts = text.split("---", 2)
    if len(parts) < 3:
        return meta
    raw_meta, body = parts[1], parts[2]
    parsed: dict = {}
    for line in raw_meta.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, value = line.split(":", 1)
        parsed[key.strip()] = value.strip().strip("\"'")
    parsed["_body"] = body.strip()
    return parsed


def chunk_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must be >= 0 and < chunk_size")
    # Prefer paragraph boundaries, then fall back to sliding windows
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    units = paragraphs if paragraphs else [text]
    chunks: list[str] = []
    buffer = ""
    for unit in units:
        candidate = f"{buffer}\n\n{unit}".strip() if buffer else unit
        if len(candidate) <= chunk_size:
            buffer = candidate
            continue
        if buffer:
            chunks.append(buffer)
        if len(unit) <= chunk_size:
            buffer = unit
            continue
        start = 0
        while start < len(unit):
            end = min(len(unit), start + chunk_size)
            chunks.append(unit[start:end].strip())
            if end >= len(unit):
                break
            start = max(0, end - overlap)
        buffer = ""
    if buffer:
        chunks.append(buffer)
    return [c for c in chunks if c]


def build_parent_child_documents(
    parents_source: Iterable[Document],
    *,
    parent_chunk_size: int,
    child_chunk_size: int,
    child_overlap: int,
) -> tuple[dict[str, Document], list[Document]]:
    parents: dict[str, Document] = {}
    children: list[Document] = []

    for source in parents_source:
        parent_parts = chunk_text(source.content, parent_chunk_size, overlap=min(100, parent_chunk_size // 5))
        for parent_body in parent_parts:
            parent = Document(
                id=new_id("parent"),
                content=parent_body,
                metadata=dict(source.metadata),
            )
            parents[parent.id] = parent
            for idx, child_body in enumerate(
                chunk_text(parent_body, child_chunk_size, child_overlap)
            ):
                child_meta = dict(source.metadata)
                child_meta.update(
                    {
                        "parent_id": parent.id,
                        "chunk_index": idx,
                    }
                )
                children.append(
                    Document(
                        id=new_id("child"),
                        content=child_body,
                        metadata=child_meta,
                        parent_id=parent.id,
                    )
                )
    return parents, children


def ingest_corpus(
    store: VectorStore,
    embedder: Embedder,
    *,
    settings: Settings | None = None,
    corpus_dir: Path | None = None,
) -> IngestResult:
    cfg = settings or get_settings()
    docs = load_corpus(corpus_dir or cfg.corpus_dir)
    parents, children = build_parent_child_documents(
        docs,
        parent_chunk_size=cfg.parent_chunk_size,
        child_chunk_size=cfg.child_chunk_size,
        child_overlap=cfg.child_chunk_overlap,
    )
    embeddings = embedder.embed_documents([child.content for child in children])
    store.clear()
    upserted = store.upsert(children, embeddings)
    logger.info(
        "ingest_complete",
        extra={
            "parents": len(parents),
            "children": len(children),
            "upserted": upserted,
        },
    )
    return IngestResult(parents=parents, children=children, upserted=upserted)
