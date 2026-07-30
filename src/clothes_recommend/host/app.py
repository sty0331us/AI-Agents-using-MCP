"""
MCP Host (Web Client) for Clothes Recommend System.

``McpHostApp`` inherits ``McpClient`` so the host reuses the same MCP session
and JSON-RPC tool calls as the CLI/orchestrator, while adding an HTTP UI for
operators and end users.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from clothes_recommend.clients.mcp_client import McpClient
from clothes_recommend.config import get_settings

TransportName = Literal["local", "remote"]

_TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"


class RecommendRequest(BaseModel):
    location: str = Field(min_length=1, description="City or place name")
    transport: TransportName = "local"


class McpToolError(RuntimeError):
    """Raised when an MCP tool returns a soft failure payload."""


class McpHostApp(McpClient):
    """
    MCP Host web application.

    Inheritance:
        McpHostApp → McpClient → FastMCP Client (STDIO | Streamable HTTP)
                                 ↕ JSON-RPC 2.0
                               MCP servers
    """

    def __init__(
        self,
        transport: TransportName = "local",
        *,
        remote_url: str | None = None,
        auth_token: str | None = None,
        title: str = "Clothes Recommend · MCP Host",
    ) -> None:
        super().__init__(
            transport=transport,
            remote_url=remote_url,
            auth_token=auth_token,
        )
        self.settings = get_settings()
        self.templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))
        self.app = FastAPI(
            title=title,
            description=(
                "MCP Host web client. Inherits McpClient and drives clothes "
                "recommendation tools over JSON-RPC via local STDIO or remote "
                "Streamable HTTP MCP servers."
            ),
            version="1.0.0",
        )
        self._register_routes()

    def _register_routes(self) -> None:
        app = self.app

        @app.get("/", response_class=HTMLResponse)
        async def index(request: Request) -> HTMLResponse:
            return self.templates.TemplateResponse(
                request,
                "index.html",
                {
                    "title": app.title,
                    "default_location": self.settings.default_location,
                    "default_transport": self.transport,
                    "remote_mcp_url": self.remote_url or self.settings.remote_mcp_url,
                    "result": None,
                    "error": None,
                },
            )

        @app.post("/recommend", response_class=HTMLResponse)
        async def recommend_form(
            request: Request,
            location: str = Form(...),
            transport: TransportName = Form("local"),
        ) -> HTMLResponse:
            error: str | None = None
            result: dict[str, Any] | None = None
            try:
                result = await self._recommend(location=location.strip(), transport=transport)
            except Exception as exc:  # noqa: BLE001 — surface to UI
                error = str(exc)

            return self.templates.TemplateResponse(
                request,
                "index.html",
                {
                    "title": app.title,
                    "default_location": location,
                    "default_transport": transport,
                    "remote_mcp_url": self.remote_url or self.settings.remote_mcp_url,
                    "result": result,
                    "error": error,
                },
            )

        @app.get("/api/tools")
        async def api_tools(transport: TransportName = "local") -> JSONResponse:
            try:
                tools = await self.list_tools(transport=transport)
            except Exception as exc:  # noqa: BLE001
                return JSONResponse(
                    {"ok": False, "error": str(exc), "transport": transport},
                    status_code=502,
                )
            return JSONResponse(
                {
                    "ok": True,
                    "transport": transport,
                    "tools": tools,
                    "protocol": "JSON-RPC 2.0 over MCP",
                }
            )

        @app.post("/api/recommend")
        async def api_recommend(body: RecommendRequest) -> JSONResponse:
            try:
                payload = await self._recommend(
                    location=body.location.strip(),
                    transport=body.transport,
                )
            except McpToolError as exc:
                return JSONResponse(
                    {"ok": False, "error": str(exc)},
                    status_code=400,
                )
            except Exception as exc:  # noqa: BLE001
                return JSONResponse(
                    {"ok": False, "error": str(exc)},
                    status_code=502,
                )
            return JSONResponse(payload if isinstance(payload, dict) else {"data": payload})

        @app.get("/api/health")
        async def api_health() -> JSONResponse:
            return JSONResponse(
                {
                    "status": "ok",
                    "role": "mcp-host",
                    "inherits": "McpClient",
                    "default_transport": self.transport,
                }
            )

    async def _recommend(
        self,
        *,
        location: str,
        transport: TransportName,
    ) -> Any:
        if not location:
            raise ValueError("location must not be empty")
        payload = await self.recommend_clothes_for_location(
            location,
            transport=transport,
        )
        if isinstance(payload, dict) and payload.get("ok") is False:
            raise McpToolError(str(payload.get("error") or "Recommendation failed"))
        return payload


def create_host_app(
    transport: TransportName = "local",
    *,
    remote_url: str | None = None,
    auth_token: str | None = None,
) -> FastAPI:
    """Factory used by ``uvicorn clothes_recommend.host.app:app``."""
    host = McpHostApp(
        transport=transport,
        remote_url=remote_url,
        auth_token=auth_token,
    )
    return host.app


# Module-level ASGI app for uvicorn
app = create_host_app()
