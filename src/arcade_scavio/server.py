"""Scavio real-time search tools for Arcade.dev / MCP.

Exposes Scavio's search across Google, Google News, Reddit, YouTube, and Amazon
as Arcade tools, plus `extract_url` — the agent's read-this-page primitive,
which works on any URL rather than a platform — and its multi-page siblings:
`map_website`, `crawl_website` / `get_crawl_status` and `batch_extract` /
`get_batch_status`. The Scavio API key is injected
securely by Arcade at call time via the SCAVIO_API_KEY secret (the client and
LLM never see it).

Run standalone:
    uv run server.py            # stdio
    uv run server.py http       # HTTP+SSE

Or deploy to Arcade Cloud with `arcade deploy`.
"""

import asyncio
import time
from typing import Annotated, Any

from arcade_mcp_server import Context, MCPApp
from scavio import AsyncScavioClient

app = MCPApp(name="scavio", version="0.3.1")


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
        "Fetch tier, and the parameter that sets the price: 'normal' (default) is the "
        "standard fetch and costs 1 credit, 'advanced' renders JavaScript-built pages and "
        "costs 1, 'ultra' reaches the hardest pages and costs 2. Start on 'normal'",
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


# --- map, crawl and batch: the multi-page members of the Extract family -----
#
# Map answers in one call. Crawl and batch run as background jobs: the start
# tools post the job, then wait up to `wait_seconds` (default 45) for it to
# finish and return its status with the first page of results either way. A
# job still running when the wait ends keeps going server-side; read the rest
# with get_crawl_status / get_batch_status and the returned id.

JOB_TERMINAL_STATUSES = frozenset({"completed", "failed", "cancelled"})
JOB_POLL_INTERVAL = 3.0
JOB_MAX_WAIT = 300

_MODE_DOC = (
    "'normal' (default) is the standard fetch, 'advanced' renders JavaScript-built pages, "
    "'ultra' reaches the hardest pages"
)


def _clean(params: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in params.items() if v is not None}


async def _wait_for_job(
    status_fn: Any, created: dict[str, Any], wait_seconds: int, limit: int
) -> dict[str, Any]:
    """Poll a started job until it finishes or the wait runs out, then read its results."""
    job_id = (created.get("data") or {}).get("id")
    if not job_id or wait_seconds <= 0:
        return _payload(created)
    deadline = time.monotonic() + min(wait_seconds, JOB_MAX_WAIT)
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        await asyncio.sleep(min(JOB_POLL_INTERVAL, remaining))
        probe = await status_fn(job_id, limit=1, include_content=False)
        if (probe.get("data") or {}).get("status") in JOB_TERMINAL_STATUSES:
            break
    return _payload(await status_fn(job_id, limit=limit))


@app.tool(requires_secrets=["SCAVIO_API_KEY"])
async def map_website(
    context: Context,
    url: Annotated[str, "The site to map. A bare host is upgraded to https"],
    search: Annotated[str | None, "Only return URLs containing every word of this text"] = None,
    limit: Annotated[
        int | None,
        "Maximum links to return, 1-5000. Default 1000 (plan caps: Free 500, PAYG 1,000, "
        "paid plans 5,000)",
    ] = None,
    sitemap: Annotated[
        str | None,
        "'include' (default) combines the site's sitemaps with the start page's links, "
        "'only' uses sitemaps alone, 'skip' uses page links alone",
    ] = None,
    include_subdomains: Annotated[bool | None, "Also return URLs on subdomains. Default false"] = None,
    include_paths: Annotated[list[str] | None, "Path globs to keep, e.g. ['/blog/**'] (max 20)"] = None,
    exclude_paths: Annotated[list[str] | None, "Path globs to drop (max 20)"] = None,
    mode: Annotated[str | None, _MODE_DOC] = None,
) -> Annotated[dict, "{url, links: [{url, source, lastmod}], total_found, returned, truncated}"]:
    """List a website's page URLs from its sitemaps and start page, deduplicated and filtered.

    Use it to find the right pages before extracting or crawling them. Pages the
    site's robots.txt disallows are left out. Costs 1 credit in normal mode;
    advanced costs up to 2 and ultra up to 10, priced by what the call needed.
    """
    params = _clean(
        {
            "search": search,
            "limit": limit,
            "sitemap": sitemap,
            "include_subdomains": include_subdomains,
            "include_paths": include_paths,
            "exclude_paths": exclude_paths,
            "mode": mode,
        }
    )
    async with _client(context) as client:
        data = await client.extract.map(url, **params)
    return _payload(data)


@app.tool(requires_secrets=["SCAVIO_API_KEY"])
async def crawl_website(
    context: Context,
    url: Annotated[str, "Where the crawl starts. Only pages on the same site are crawled"],
    max_pages: Annotated[
        int | None,
        "Maximum pages to fetch. Default 100. Plan caps: Free 10, PAYG 100, Project 500, "
        "Bootstrap 2,000, Startup 5,000, Growth 10,000",
    ] = None,
    max_depth: Annotated[int | None, "Links away from the start page to follow, 0-10 (default 3)"] = None,
    include_paths: Annotated[list[str] | None, "Path globs to crawl, e.g. ['/docs/**'] (max 20)"] = None,
    exclude_paths: Annotated[list[str] | None, "Path globs to skip (max 20)"] = None,
    allow_subdomains: Annotated[bool | None, "Also crawl subdomains. Default false"] = None,
    format: Annotated[str | None, "'markdown' (default), 'text' or 'html' for each page"] = None,
    mode: Annotated[str | None, _MODE_DOC] = None,
    wait_seconds: Annotated[
        int, "Seconds to wait for the crawl to finish, 0-300. 0 returns the job id at once"
    ] = 45,
    limit: Annotated[int, "Pages returned in this response, 1-100"] = 10,
) -> Annotated[dict, "{id, status, pages, credits_used, results, next_cursor}"]:
    """Crawl a website from one URL and get its pages back as Markdown, text or HTML.

    Same-site pages are discovered and extracted breadth-first within the page,
    depth and path limits; robots.txt is obeyed. Starts the crawl and waits up
    to wait_seconds for it to finish. If status is still queued or running,
    call get_crawl_status with the id later. Billed per SUCCESSFUL page at
    extract's price for the mode: normal and advanced 1 credit, ultra 2
    credits. Failed and skipped pages are free, and the crawl stops cleanly if
    the balance runs out.
    """
    body = _clean(
        {
            "max_pages": max_pages,
            "max_depth": max_depth,
            "include_paths": include_paths,
            "exclude_paths": exclude_paths,
            "allow_subdomains": allow_subdomains,
            "format": format,
            "mode": mode,
        }
    )
    async with _client(context) as client:
        created = await client.extract.crawl(url, **body)
        return await _wait_for_job(client.extract.crawl_status, created, wait_seconds, limit)


@app.tool(requires_secrets=["SCAVIO_API_KEY"])
async def get_crawl_status(
    context: Context,
    id: Annotated[str, "The crawl's job id"],
    cursor: Annotated[str | None, "next_cursor from the previous response"] = None,
    limit: Annotated[int, "Pages per response, 1-100"] = 10,
    status: Annotated[str | None, "Only pages with this status: succeeded, failed or skipped"] = None,
    include_content: Annotated[bool | None, "False lists pages without their content"] = None,
) -> Annotated[dict, "{status, stopped_reason, pages, credits_used, results, next_cursor}"]:
    """Read a crawl's progress and its page results by job id, paged by cursor.

    Free. Results are kept for 3 days after the crawl finishes.
    """
    params = _clean({"cursor": cursor, "limit": limit, "status": status, "include_content": include_content})
    async with _client(context) as client:
        data = await client.extract.crawl_status(id, **params)
    return _payload(data)


@app.tool(requires_secrets=["SCAVIO_API_KEY"])
async def batch_extract(
    context: Context,
    urls: Annotated[
        list[str],
        "The pages to extract. Plan caps: Free 10, PAYG 50, Project 100, Bootstrap 500, "
        "Startup and Growth 1,000",
    ],
    format: Annotated[str | None, "'markdown' (default), 'text' or 'html' for each page"] = None,
    mode: Annotated[str | None, _MODE_DOC] = None,
    wait_seconds: Annotated[
        int, "Seconds to wait for the batch to finish, 0-300. 0 returns the job id at once"
    ] = 45,
    limit: Annotated[int, "Pages returned in this response, 1-100"] = 10,
) -> Annotated[dict, "{id, status, pages, credits_used, results, next_cursor}"]:
    """Extract a list of URLs in one job, each returned as Markdown, text or HTML.

    Starts the batch and waits up to wait_seconds for it to finish; results come
    back in input order. If status is still queued or running, call
    get_batch_status with the id later. Billed per SUCCESSFUL page at extract's
    price for the mode: normal and advanced 1 credit, ultra 2 credits. Failed
    pages are free.
    """
    async with _client(context) as client:
        created = await client.extract.batch(urls, **_clean({"format": format, "mode": mode}))
        return await _wait_for_job(client.extract.batch_status, created, wait_seconds, limit)


@app.tool(requires_secrets=["SCAVIO_API_KEY"])
async def get_batch_status(
    context: Context,
    id: Annotated[str, "The batch's job id"],
    cursor: Annotated[str | None, "next_cursor from the previous response"] = None,
    limit: Annotated[int, "Pages per response, 1-100"] = 10,
    status: Annotated[str | None, "Only pages with this status: succeeded, failed or skipped"] = None,
    include_content: Annotated[bool | None, "False lists pages without their content"] = None,
) -> Annotated[dict, "{status, pages, credits_used, results, next_cursor}"]:
    """Read a batch extract's progress and its page results by job id, paged by cursor.

    Free. Results are kept for 3 days after the batch finishes.
    """
    params = _clean({"cursor": cursor, "limit": limit, "status": status, "include_content": include_content})
    async with _client(context) as client:
        data = await client.extract.batch_status(id, **params)
    return _payload(data)


if __name__ == "__main__":
    app.run(transport="stdio")
