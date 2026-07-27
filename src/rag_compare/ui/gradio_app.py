"""Gradio UI for interactive retriever strategy comparison."""

from __future__ import annotations

from typing import Any
import json

import gradio as gr

from rag_compare.config import VectorBackend, get_settings
from rag_compare.logging_setup import configure_logging
from rag_compare.models import RetrieverKind
from rag_compare.service import RagCompareService, get_service

STRATEGY_CHOICES = [k.value for k in RetrieverKind]
BACKEND_CHOICES = [b.value for b in VectorBackend]


def _format_retrieval(result) -> str:
    lines = [
        f"strategy={result.trace.strategy.value}",
        f"backend={result.trace.vector_backend.value}",
        f"latency_ms={result.latency_ms:.2f}",
        f"rewrites={result.trace.rewritten_queries}",
        f"filter={result.trace.metadata_filter}",
        f"notes={result.trace.notes}",
        "",
    ]
    for doc in result.documents:
        source = doc.document.metadata.get("source", "?")
        topic = doc.document.metadata.get("topic", "?")
        preview = doc.document.content.replace("\n", " ")[:280]
        lines.append(
            f"#{doc.rank} score={doc.score:.4f} source={source} topic={topic}\n{preview}\n"
        )
    return "\n".join(lines)


def build_ui(service: RagCompareService | None = None) -> gr.Blocks:
    svc = service or get_service()
    settings = get_settings()

    with gr.Blocks(title="RAG Retriever Comparison") as demo:
        gr.Markdown(
            """
# RAG Retriever Comparison Lab
Production-style comparison of **vector**, **multi-query**, **self-query**, and **parent-document**
retrievers on **FAISS** or **Chroma**. Ingest the sample corpus, compare strategies on the same
queries, then generate grounded answers.
"""
        )

        with gr.Row():
            backend = gr.Dropdown(BACKEND_CHOICES, value=settings.default_vector_backend.value, label="Vector backend")
            ingest_btn = gr.Button("Ingest corpus", variant="primary")
            status_box = gr.JSON(label="Service status")

        def do_ingest(selected_backend: str) -> dict[str, Any]:
            return svc.ingest(selected_backend)

        ingest_btn.click(do_ingest, inputs=[backend], outputs=[status_box])

        with gr.Tab("Compare strategies"):
            queries = gr.Textbox(
                lines=5,
                label="Queries (one per line)",
                value=(
                    "How do multi-query retrievers improve recall?\n"
                    "Compare FAISS and Chroma for production RAG\n"
                    "advanced retrieval parent document strategy\n"
                    "What metrics matter for retriever evaluation?"
                ),
            )
            top_k = gr.Slider(1, 10, value=5, step=1, label="top_k")
            compare_btn = gr.Button("Run comparison")
            report_json = gr.JSON(label="Comparison report")
            report_summary = gr.Textbox(lines=10, label="Summary")

            def do_compare(text: str, k: int):
                qlist = [line.strip() for line in text.splitlines() if line.strip()]
                labels = None
                labels_path = settings.eval_dir / "labels.json"
                if labels_path.exists():
                    labels = json.loads(labels_path.read_text(encoding="utf-8"))
                report = svc.compare(qlist, top_k=int(k), relevant_ids_by_query=labels)
                return report.model_dump(mode="json"), report.summary

            compare_btn.click(do_compare, inputs=[queries, top_k], outputs=[report_json, report_summary])

        with gr.Tab("Retrieve"):
            q1 = gr.Textbox(label="Query", value="When should I use a self-querying retriever?")
            strategy = gr.Dropdown(STRATEGY_CHOICES, value=RetrieverKind.SELF_QUERY.value, label="Strategy")
            k1 = gr.Slider(1, 10, value=5, step=1, label="top_k")
            retrieve_btn = gr.Button("Retrieve")
            retrieve_out = gr.Textbox(lines=18, label="Retrieval trace")

            def do_retrieve(query: str, strat: str, k: int) -> str:
                result = svc.retrieve(query, strategy=strat, top_k=int(k))
                return _format_retrieval(result)

            retrieve_btn.click(do_retrieve, inputs=[q1, strategy, k1], outputs=[retrieve_out])

        with gr.Tab("RAG answer"):
            q2 = gr.Textbox(label="Question", value="Explain parent document retrieval for production RAG.")
            strategy2 = gr.Dropdown(STRATEGY_CHOICES, value=RetrieverKind.PARENT_DOCUMENT.value, label="Strategy")
            k2 = gr.Slider(1, 10, value=4, step=1, label="top_k")
            answer_btn = gr.Button("Generate answer")
            answer_out = gr.Textbox(lines=8, label="Answer")
            citations_out = gr.Textbox(lines=12, label="Citations / retrieval trace")

            def do_answer(query: str, strat: str, k: int):
                result = svc.answer(query, strategy=strat, top_k=int(k))
                cites = _format_retrieval(result.retrieval)
                meta = (
                    f"total_latency_ms={result.total_latency_ms:.2f} "
                    f"generation_latency_ms={result.generation_latency_ms:.2f}\n\n"
                )
                return result.answer, meta + cites

            answer_btn.click(do_answer, inputs=[q2, strategy2, k2], outputs=[answer_out, citations_out])

        with gr.Tab("Strategy cheat-sheet"):
            gr.Markdown(
                """
| Strategy | When it wins | Watch-outs |
|---|---|---|
| **Vector** | Clean semantic questions, low latency SLOs | Weak on vocabulary mismatch |
| **Multi-query** | Ambiguous / underspecified questions needing recall | Extra LLM + search cost |
| **Self-query** | Users encode filters in language (`advanced` docs on `vector_db`) | Bad filter extraction → empty results (we soft-fallback) |
| **Parent-document** | You need precise chunk matching but broad LLM context | Parent map must stay consistent with child index |

**FAISS** — excellent in-process similarity search, simple ops for embedded services.
**Chroma** — metadata-first workflows, persistent collections, rapid prototyping to service.
"""
            )

    return demo


def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    demo = build_ui()
    demo.launch(server_name=settings.api_host, server_port=settings.gradio_port)


if __name__ == "__main__":
    main()
