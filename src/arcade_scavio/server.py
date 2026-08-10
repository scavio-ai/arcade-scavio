"""Scavio real-time search tools for Arcade.dev / MCP.

Exposes Scavio's search across Google, Google News, Reddit, YouTube, and Amazon
as Arcade tools, plus `extract_url` — the agent's read-this-page primitive,
which works on any URL rather than a platform. The Scavio API key is injected
securely by Arcade at call time via the SCAVIO_API_KEY secret (the client and
LLM never see it).

Run standalone:
    uv run server.py            # stdio
    uv run server.py http       # HTTP+SSE

Or deploy to Arcade Cloud with `arcade deploy`.
"""

from typing import Annotated, Any

from arcade_mcp_server import Context, MCPApp
from scavio import AsyncScavioClient

app = MCPApp(name="scavio", version="0.2.0")


def _client(context: Context) -> AsyncScavioClient:
    return AsyncScavioClient(api_key=context.get_secret("SCAVIO_API_KEY"))


def _nested(data: dict[str, Any], key: str) -> list:
    inner = data.get("data")
    if isinstance(inner, dict) and isinstance(inner.get(key), list):
        return inner[key]
    return data.get(key) if isinstance(data.get(key), list) else []


def _payload(data: dict[str, Any]) -> dict:
    """Return the inner data object of a Scavio response envelope, or the response itself."""
    inner = data.get("data")
    return inner if isinstance(inner, dict) else data


# Registered first on purpose: `extract_url` is the read-this-page primitive an
# agent reaches for most, and it is the only tool here that is not tied to a
# platform. `extract` is a TOP-LEVEL method on the client, never a namespace --
# client.extract(url), not client.extract.extract().
@app.tool(requires_secrets=["SCAVIO_API_KEY"])
async def extract_url(
    context: Context,
    url: Annotated[str, "The page to read. http(s) only; a bare host is upgraded to https"],
    format: Annotated[
        str,
        "'markdown' (default) is a readability extraction with the page chrome stripped, "
        "'text' is that flattened to plain text, 'html' is the raw page",
    ] = "markdown",
    mode: Annotated[
        str,
        "Fetch tier, and the parameter that sets the price: 'normal' (default) is a plain "
        "fetch and costs 1 credit, 'advanced' renders the page in a browser for JS-built "
        "sites and costs 1, 'ultra' routes through residential proxies for the hardest bot "
        "walls and costs 2. Start on 'normal'",
    ] = "normal",
) -> Annotated[dict, "The page as {url, format, mode, content, content_length}"]:
    """Read any web page with Scavio and return it as clean Markdown, plain text, or raw HTML.

    Use this on any URL, including one returned by the search tools. Billing is
    tier-priced by `mode` rather than flat, and only a successful read is
    charged: a dead link, a bot wall or a timeout costs nothing.
    """
    async with _client(context) as client:
        data = await client.extract(url, format=format, mode=mode)
    return _payload(data)


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
    return _nested(data, "results")[:max_results]


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
async def get_youtube_video(
    context: Context,
    video_id: Annotated[str, "YouTube video id or a full watch URL"],
) -> Annotated[dict, "YouTube video details"]:
    """Fetch full details for a YouTube video (title, author, view count, description, captions) with Scavio."""
    async with _client(context) as client:
        data = await client.youtube.video(video_id)
    return _payload(data)


@app.tool(requires_secrets=["SCAVIO_API_KEY"])
async def get_youtube_transcript(
    context: Context,
    video_id: Annotated[str, "YouTube video id or a full watch URL"],
    language: Annotated[str, "Transcript language code"] = "en",
    format: Annotated[str, "'text' for a plain transcript, 'srt' for timed subtitles"] = "text",
) -> Annotated[dict, "YouTube video transcript"]:
    """Fetch a YouTube video's transcript or timed subtitles with Scavio."""
    async with _client(context) as client:
        data = await client.youtube.transcript(video_id, language=language, format=format)
    return _payload(data)


@app.tool(requires_secrets=["SCAVIO_API_KEY"])
async def list_youtube_comments(
    context: Context,
    video_id: Annotated[str, "YouTube video id or a full watch URL"],
    max_results: Annotated[int, "Maximum number of comments"] = 10,
) -> Annotated[list[dict], "YouTube video comments"]:
    """List comments on a YouTube video with Scavio."""
    async with _client(context) as client:
        data = await client.youtube.comments(video_id)
    return _nested(data, "comments")[:max_results]


@app.tool(requires_secrets=["SCAVIO_API_KEY"])
async def get_youtube_channel(
    context: Context,
    channel_id: Annotated[str, "YouTube channel id, @handle, or channel URL"],
) -> Annotated[dict, "YouTube channel details"]:
    """Fetch a YouTube channel's details (subscribers, video count, views, links) with Scavio."""
    async with _client(context) as client:
        data = await client.youtube.channel(channel_id)
    return _payload(data)


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
