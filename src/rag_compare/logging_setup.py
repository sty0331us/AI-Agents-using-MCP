"""Structured logging for API, CLI, and evaluation runs."""

from __future__ import annotations

import logging
import sys
from typing import Any


class _JsonishFormatter(logging.Formatter):
    """Compact key=value formatter that stays readable in terminals and log ships."""

    def format(self, record: logging.LogRecord) -> str:
        base = super().format(record)
        extras: dict[str, Any] = {}
        for key, value in record.__dict__.items():
            if key.startswith("_") or key in {
                "name",
                "msg",
                "args",
                "levelname",
                "levelno",
                "pathname",
                "filename",
                "module",
                "exc_info",
                "exc_text",
                "stack_info",
                "lineno",
                "funcName",
                "created",
                "msecs",
                "relativeCreated",
                "thread",
                "threadName",
                "processName",
                "process",
                "message",
                "asctime",
            }:
                continue
            extras[key] = value
        if not extras:
            return base
        kv = " ".join(f"{k}={v!r}" for k, v in sorted(extras.items()))
        return f"{base} | {kv}"


def configure_logging(level: str = "INFO") -> None:
    root = logging.getLogger()
    if root.handlers:
        root.setLevel(level.upper())
        return

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        _JsonishFormatter(
            fmt="%(asctime)s %(levelname)s [%(name)s] %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
        )
    )
    root.addHandler(handler)
    root.setLevel(level.upper())

    # Quiet noisy third-party loggers in production demos
    for noisy in ("httpx", "httpcore", "urllib3", "chromadb", "openai"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
