"""Application configuration."""

from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Runtime settings for Clothes Recommend System MCP connections."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    default_location: str = Field(default="Seoul", alias="DEFAULT_LOCATION")

    local_mcp_command: str = Field(default="python", alias="LOCAL_MCP_COMMAND")
    local_mcp_args: str = Field(
        default="servers/local_stdio/server.py",
        alias="LOCAL_MCP_ARGS",
    )

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
        return [part for part in self.local_mcp_args.split() if part]


def get_settings() -> Settings:
    return Settings()
