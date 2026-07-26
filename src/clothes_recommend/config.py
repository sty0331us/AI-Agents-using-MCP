"""Application configuration — local STDIO, remote HTTP, and cloud-facing options."""

from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Runtime settings for Clothes Recommend System."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    default_location: str = Field(default="Seoul", alias="DEFAULT_LOCATION")

    # Local MCP (STDIO)
    local_mcp_command: str = Field(default="python", alias="LOCAL_MCP_COMMAND")
    local_mcp_args: str = Field(
        default="servers/local_stdio/server.py",
        alias="LOCAL_MCP_ARGS",
    )

    # Remote MCP client
    remote_mcp_url: str = Field(
        default="http://localhost:8000/mcp",
        alias="REMOTE_MCP_URL",
    )
    remote_mcp_auth_token: str | None = Field(
        default=None,
        alias="REMOTE_MCP_AUTH_TOKEN",
    )
    # API Gateway / APIM keys (sent as x-api-key when set)
    remote_mcp_api_key: str | None = Field(
        default=None,
        alias="REMOTE_MCP_API_KEY",
    )

    # Remote MCP server bind (container / VM / ECS task)
    remote_mcp_host: str = Field(default="0.0.0.0", alias="REMOTE_MCP_HOST")
    remote_mcp_port: int = Field(default=8000, alias="REMOTE_MCP_PORT")
    remote_mcp_path: str = Field(default="/mcp", alias="REMOTE_MCP_PATH")
    # Required for multi-instance load balancers (no sticky session affinity)
    remote_mcp_stateless_http: bool = Field(
        default=True,
        alias="REMOTE_MCP_STATELESS_HTTP",
    )
    remote_mcp_log_level: str = Field(default="INFO", alias="REMOTE_MCP_LOG_LEVEL")
    # Comma-separated Host header allow-list (empty = FastMCP defaults)
    remote_mcp_allowed_hosts: str = Field(default="", alias="REMOTE_MCP_ALLOWED_HOSTS")
    remote_mcp_allowed_origins: str = Field(
        default="",
        alias="REMOTE_MCP_ALLOWED_ORIGINS",
    )

    @property
    def local_args_list(self) -> list[str]:
        return [part for part in self.local_mcp_args.split() if part]

    @property
    def allowed_hosts_list(self) -> list[str] | None:
        hosts = [h.strip() for h in self.remote_mcp_allowed_hosts.split(",") if h.strip()]
        return hosts or None

    @property
    def allowed_origins_list(self) -> list[str] | None:
        origins = [
            o.strip() for o in self.remote_mcp_allowed_origins.split(",") if o.strip()
        ]
        return origins or None


def get_settings() -> Settings:
    return Settings()
