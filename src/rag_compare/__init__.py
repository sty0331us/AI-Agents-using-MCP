"""Production RAG retriever comparison toolkit.

Compares vector-store, multi-query, self-query, and parent-document
retrieval strategies across FAISS and Chroma backends with latency,
recall, and MRR metrics suitable for production evaluation.
"""

from rag_compare.__version__ import __version__

__all__ = ["__version__"]
