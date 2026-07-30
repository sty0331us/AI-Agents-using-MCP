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
ActivityPreference = Literal["general", "commute", "outdoor", "office"]

_TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"


class RecommendRequest(BaseModel):
    location: str = Field(min_length=1, description="City or place name")
    transport: TransportName = "local"
    activity: ActivityPreference = "general"


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
                    "default_activity": "general",
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
            activity: ActivityPreference = Form("general"),
        ) -> HTMLResponse:
            error: str | None = None
            result: dict[str, Any] | None = None
            try:
                result = await self._recommend(
                    location=location.strip(),
                    transport=transport,
                    activity=activity,
                )
            except Exception as exc:  # noqa: BLE001 — surface to UI
                error = str(exc)

            return self.templates.TemplateResponse(
                request,
                "index.html",
                {
                    "title": app.title,
                    "default_location": location,
                    "default_transport": transport,
                    "default_activity": activity,
                    "remote_mcp_url": self.remote_url or self.settings.remote_mcp_url,
                    "result": result,
                    "error": error,
                },
            )

        @app.get("/api/tools")
        async def api_tools(transport: TransportName = "local") -> JSONResponse:
            self.transport = transport
            tools = await self.list_tools()
            return JSONResponse(
                {
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
                    activity=body.activity,
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
        activity: ActivityPreference = "general",
    ) -> Any:
        if not location:
            raise ValueError("location must not be empty")
        # Host reuses inherited McpClient methods after selecting transport.
        self.transport = transport
        return await self.recommend_clothes_for_location(location, activity=activity)


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
