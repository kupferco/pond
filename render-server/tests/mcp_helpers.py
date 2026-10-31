from __future__ import annotations

import anyio
import httpx2

from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamable_http_client


async def _call(url: str, token: str | None, name: str, args: dict):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    async with httpx2.AsyncClient(headers=headers, timeout=180) as http:
        async with streamable_http_client(url, http_client=http) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                return await session.call_tool(name, args)


def call_tool(url: str, token: str | None, name: str, args: dict):
    return anyio.run(_call, url, token, name, args)


async def _list_tools(url: str, token: str | None):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    async with httpx2.AsyncClient(headers=headers, timeout=60) as http:
        async with streamable_http_client(url, http_client=http) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                return await session.list_tools()


def list_tools(url: str, token: str | None):
    return anyio.run(_list_tools, url, token)
