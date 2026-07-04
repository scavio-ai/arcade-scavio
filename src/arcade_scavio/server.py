"""Scavio real-time search tools for Arcade.dev / MCP.

Exposes Scavio's search across Google, Google News, Reddit, YouTube, and Amazon
as Arcade tools. The Scavio API key is injected securely by Arcade at call time
via the SCAVIO_API_KEY secret (the client and LLM never see it).

Run standalone:
    uv run server.py            # stdio
    uv run server.py http       # HTTP+SSE

Or deploy to Arcade Cloud with `arcade deploy`.
"""

from typing import Annotated, Any

from arcade_mcp_server import Context, MCPApp
from scavio import AsyncScavioClient

app = MCPApp(name="scavio", version="0.1.0")


def _client(context: Context) -> AsyncScavioClient:
    return AsyncScavioClient(api_key=context.get_secret("SCAVIO_API_KEY"))


def _nested(data: dict[str, Any], key: str) -> list:
    inner = data.get("data")
    if isinstance(inner, dict) and isinstance(inner.get(key), list):
        return inner[key]
    return data.get(key) if isinstance(data.get(key), list) else []


@app.tool(requires_secrets=["SCAVIO_API_KEY"])
async def search_google(
    context: Context,
    query: Annotated[str, "The search query"],
    max_results: Annotated[int, "Maximum number of results"] = 10,
) -> Annotated[list[dict], "Organic results (title, link, snippet)"]:
    """Search Google in real time with Scavio and return organic results."""
    async with _client(context) as client:
        data = await client.google.search(query)
    return data.get("organic_results", [])[:max_results]


@app.tool(requires_secrets=["SCAVIO_API_KEY"])
async def search_news(
    context: Context,
    query: Annotated[str, "The news search query"],
    max_results: Annotated[int, "Maximum number of results"] = 10,
) -> Annotated[list[dict], "Google News results"]:
    """Search Google News for recent articles on a topic with Scavio."""
    async with _client(context) as client:
        data = await client.google.news(query=query)
    results = data.get("news_results") or data.get("results") or []
    return results[:max_results]


@app.tool(requires_secrets=["SCAVIO_API_KEY"])
async def search_reddit(
    context: Context,
    query: Annotated[str, "The Reddit search query"],
    max_results: Annotated[int, "Maximum number of results"] = 10,
) -> Annotated[list[dict], "Reddit posts"]:
    """Search Reddit posts for community discussion and sentiment with Scavio."""
    async with _client(context) as client:
        data = await client.reddit.search(query)
    return _nested(data, "posts")[:max_results]


@app.tool(requires_secrets=["SCAVIO_API_KEY"])
async def search_youtube(
    context: Context,
    query: Annotated[str, "The video search query"],
    max_results: Annotated[int, "Maximum number of results"] = 10,
) -> Annotated[list[dict], "YouTube videos"]:
    """Search YouTube for videos with Scavio."""
    async with _client(context) as client:
        data = await client.youtube.search(query)
    return _nested(data, "results")[:max_results]


@app.tool(requires_secrets=["SCAVIO_API_KEY"])
async def search_amazon(
    context: Context,
    query: Annotated[str, "The product search query"],
    max_results: Annotated[int, "Maximum number of results"] = 10,
) -> Annotated[list[dict], "Amazon products"]:
    """Search Amazon product listings with Scavio."""
    async with _client(context) as client:
        data = await client.amazon.search(query)
    return _nested(data, "products")[:max_results]


if __name__ == "__main__":
    app.run(transport="stdio")
