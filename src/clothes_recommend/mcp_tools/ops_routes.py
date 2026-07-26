"""Operational HTTP routes for load balancers and container orchestrators."""

from __future__ import annotations

from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse


def register_ops_routes(mcp: FastMCP) -> FastMCP:
    """
    Attach health/readiness endpoints used by ALB, NLB, Azure App Gateway,
    Kubernetes probes, and container platform health checks.
    """

    @mcp.custom_route("/health", methods=["GET"], name="health")
    async def health(_request: Request) -> JSONResponse:
        return JSONResponse(
            {
                "status": "ok",
                "service": mcp.name,
                "role": "clothes-recommend-mcp",
            }
        )

    @mcp.custom_route("/ready", methods=["GET"], name="ready")
    async def ready(_request: Request) -> JSONResponse:
        return JSONResponse({"status": "ready", "service": mcp.name})

    return mcp
