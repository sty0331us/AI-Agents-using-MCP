"""In-process FastMCP client — zero subprocess / network overhead."""

from __future__ import annotations

from fastmcp import Client

from clothes_recommend.mcp_tools.server_factory import create_clothes_mcp


def connect_inprocess_mcp(name: str = "clothes-recommend-inprocess") -> Client:
    """
    Return a FastMCP Client bound directly to a server object in this process.

    This is the fastest local path: no STDIO spawn, no HTTP hop.
    """
    return Client(create_clothes_mcp(name=name))
