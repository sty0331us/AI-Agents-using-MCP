"""CLI entrypoints for ingest, compare, retrieve, answer, api, and ui."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from rag_compare.config import VectorBackend, get_settings
from rag_compare.logging_setup import configure_logging, get_logger
from rag_compare.models import RetrieverKind
from rag_compare.service import RagCompareService

logger = get_logger(__name__)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="rag-compare",
        description="Production RAG retriever comparison toolkit",
    )
    parser.add_argument(
        "--vector-backend",
        choices=[b.value for b in VectorBackend],
        default=None,
        help="Override vector backend (faiss|chroma)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("ingest", help="Chunk corpus and build vector index")

    compare = sub.add_parser("compare", help="Compare all retriever strategies")
    compare.add_argument(
        "--queries-file",
        type=Path,
        default=None,
        help="Text file with one query per line (defaults to data/eval/queries.txt)",
    )
    compare.add_argument("--top-k", type=int, default=None)

    retrieve = sub.add_parser("retrieve", help="Run a single strategy")
    retrieve.add_argument("--query", required=True)
    retrieve.add_argument(
        "--strategy",
        choices=[s.value for s in RetrieverKind],
        default=RetrieverKind.VECTOR.value,
    )
    retrieve.add_argument("--top-k", type=int, default=None)

    answer = sub.add_parser("answer", help="Retrieve + generate grounded answer")
    answer.add_argument("--query", required=True)
    answer.add_argument(
        "--strategy",
        choices=[s.value for s in RetrieverKind],
        default=RetrieverKind.VECTOR.value,
    )
    answer.add_argument("--top-k", type=int, default=None)

    api = sub.add_parser("api", help="Run FastAPI server")
    api.add_argument("--host", default=None)
    api.add_argument("--port", type=int, default=None)

    sub.add_parser("ui", help="Launch Gradio comparison UI")
    return parser


def _default_queries(settings) -> list[str]:
    path = settings.eval_dir / "queries.txt"
    if path.exists():
        return [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return [
        "How do multi-query retrievers improve recall?",
        "Compare FAISS and Chroma for production RAG",
        "advanced retrieval parent document strategy",
        "What metrics matter for retriever evaluation?",
    ]


def _load_labels(settings) -> dict[str, list[str]] | None:
    path = settings.eval_dir / "labels.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    settings = get_settings()
    configure_logging(settings.log_level)
    service = RagCompareService(settings)

    if args.command == "api":
        import uvicorn
        from rag_compare.api.app import app

        uvicorn.run(
            app,
            host=args.host or settings.api_host,
            port=args.port or settings.api_port,
        )
        return 0

    if args.command == "ui":
        from rag_compare.ui.gradio_app import main as ui_main

        ui_main()
        return 0

    backend = args.vector_backend
    if args.command == "ingest":
        status = service.ingest(backend)
        print(json.dumps(status, indent=2))
        return 0

    # Remaining commands need an index
    service.ingest(backend)

    if args.command == "compare":
        if args.queries_file:
            queries = [
                line.strip()
                for line in args.queries_file.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
        else:
            queries = _default_queries(settings)
        report = service.compare(
            queries,
            top_k=args.top_k,
            relevant_ids_by_query=_load_labels(settings),
        )
        print(report.summary)
        print()
        print(json.dumps(report.model_dump(mode="json"), indent=2))
        return 0

    if args.command == "retrieve":
        result = service.retrieve(args.query, strategy=args.strategy, top_k=args.top_k)
        print(json.dumps(result.model_dump(mode="json"), indent=2))
        return 0

    if args.command == "answer":
        result = service.answer(args.query, strategy=args.strategy, top_k=args.top_k)
        print(result.answer)
        print()
        print(json.dumps(result.model_dump(mode="json"), indent=2))
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
