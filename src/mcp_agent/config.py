"""Application configuration loaded from environment variables."""

from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Connection settings for local and remote MCP servers."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Local MCP (STDIO)
    local_mcp_command: str = Field(default="python", alias="LOCAL_MCP_COMMAND")
    local_mcp_args: str = Field(
        default="servers/local_stdio/server.py",
        alias="LOCAL_MCP_ARGS",
    )

    # Remote MCP (Streamable HTTP)
    remote_mcp_url: str = Field(
        default="http://localhost:8000/mcp",
        alias="REMOTE_MCP_URL",
    )
    remote_mcp_auth_token: str | None = Field(
        default=None,
        alias="REMOTE_MCP_AUTH_TOKEN",
    )

    @property
    def local_args_list(self) -> list[str]:
        """Split LOCAL_MCP_ARGS into a list of CLI arguments."""
        return [part for part in self.local_mcp_args.split() if part]

    @property
    def local_server_script(self) -> Path:
        """Absolute path to the local STDIO server script."""
        script = Path(self.local_args_list[0])
        if not script.is_absolute():
            script = REPO_ROOT / script
        return script.resolve()


def get_settings() -> Settings:
    return Settings()
