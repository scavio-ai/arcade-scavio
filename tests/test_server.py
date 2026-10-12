"""Tests for arcade-scavio.

The Scavio SDK client is replaced with a fake, so nothing here needs an API key
or a network. The point of these tests is twofold: prove the wire calls are the
ones the canonical API expects, and pin the curated surface at exactly 15 tools
so it cannot grow without the README's counts and credit table being updated too.
"""

from typing import Any

import pytest

import arcade_scavio.server as server

# The curated surface: 9 endpoints over 4 platforms, plus `extract`, which
# belongs to no platform. Keep in step with README.md.
TOOL_NAMES = {
    "Scavio.ExtractUrl",
    "Scavio.SearchGoogle",
    "Scavio.SearchNews",
    "Scavio.SearchReddit",
    "Scavio.SearchYoutube",
    "Scavio.GetYoutubeVideo",
    "Scavio.GetYoutubeTranscript",
    "Scavio.ListYoutubeComments",
    "Scavio.GetYoutubeChannel",
    "Scavio.SearchAmazon",
    # The Extract family's multi-page members.
    "Scavio.MapWebsite",
    "Scavio.CrawlWebsite",
    "Scavio.GetCrawlStatus",
    "Scavio.BatchExtract",
    "Scavio.GetBatchStatus",
}


class _Namespace:
    def __init__(self, calls: list, responses: dict):
        self._calls = calls
        self._responses = responses

    def __getattr__(self, method: str):
        async def _call(*args: Any, **kwargs: Any) -> dict:
            self._calls.append((method, args, kwargs))
            return self._responses.get(method, {"data": {}})

        return _call


class _FakeClient:
    """Stands in for AsyncScavioClient, including its async-context-manager use.

    `calls` and `responses` are CLASS state, not instance state: every tool
    builds a fresh client inside its own `async with`, so a response staged
    before a call has to survive the next construction. The `ctx` fixture
    resets both between tests.
    """

    last: "_FakeClient | None" = None
    calls: list = []
    responses: dict = {}

    def __init__(self, *_args: Any, api_key: str | None = None, **_kwargs: Any):
        self.api_key = api_key
        for ns in ("google", "youtube", "amazon", "reddit"):
            setattr(self, ns, _Namespace(_FakeClient.calls, _FakeClient.responses))
        _FakeClient.last = self

        self.extract = _FakeExtract()

    async def __aenter__(self) -> "_FakeClient":
        return self

    async def __aexit__(self, *_exc: Any) -> bool:
        return False

    def __getattr__(self, name: str):
        msg = f"curated surface: {name} is not exposed by arcade-scavio"
        raise AssertionError(msg)


class _FakeExtract:
    """client.extract: CALLABLE for one page (scavio >= 0.23), with map, crawl and
    batch methods hanging off it. It has no `extract` attribute, so a tool that
    called client.extract.extract() blows up here, which is the point.

    Status calls pop from `responses["status_queue"]` when staged, else answer a
    completed job.
    """

    async def __call__(self, url: str, **kwargs: Any) -> dict:
        _FakeClient.calls.append(("extract", (url,), kwargs))
        return _FakeClient.responses.get("extract", {"data": {}})

    def _record(self, name: str, args: tuple, kwargs: dict) -> None:
        _FakeClient.calls.append((f"extract.{name}", args, kwargs))

    async def map(self, url: str, **kwargs: Any) -> dict:
        self._record("map", (url,), kwargs)
        return {"data": {"url": url, "links": [{"url": url, "source": "page"}], "returned": 1}, "credits_used": 1}

    async def crawl(self, url: str, **kwargs: Any) -> dict:
        self._record("crawl", (url,), kwargs)
        return {"data": {"id": "crawl_1", "status": "queued"}, "credits_used": 0}

    async def batch(self, urls: list, **kwargs: Any) -> dict:
        self._record("batch", (urls,), kwargs)
        return {"data": {"id": "batch_1", "status": "queued"}, "credits_used": 0}

    async def _status(self, name: str, job_id: str, kwargs: dict) -> dict:
        self._record(name, (job_id,), kwargs)
        queue = _FakeClient.responses.get("status_queue")
        if queue:
            return queue.pop(0)
        return {"data": {"id": job_id, "status": "completed", "results": [{"url": "u", "content": "c"}], "next_cursor": None}}

    async def crawl_status(self, job_id: str, **kwargs: Any) -> dict:
        return await self._status("crawl_status", job_id, kwargs)

    async def batch_status(self, job_id: str, **kwargs: Any) -> dict:
        return await self._status("batch_status", job_id, kwargs)


class _FakeContext:
    def get_secret(self, key: str) -> str:
        assert key == "SCAVIO_API_KEY"
        return "sk_live_test"


@pytest.fixture
def ctx(monkeypatch):
    monkeypatch.setattr(server, "AsyncScavioClient", _FakeClient)
    _FakeClient.last = None
    _FakeClient.calls = []
    _FakeClient.responses = {}
    return _FakeContext()


def _last_call() -> tuple:
    assert _FakeClient.last is not None
    return _FakeClient.last.calls[-1]


# --- curated-surface guards ------------------------------------------------


def test_surface_is_exactly_fifteen_tools():
    """9 endpoints across Google (2), YouTube (5), Reddit (1), Amazon (1), plus the
    Extract family: extract, map, crawl + status, batch + status."""
    catalog = server.app._catalog
    assert catalog.get_tool_count() == 15
    assert {str(n) for n in catalog.get_tool_names()} == TOOL_NAMES


def test_uncovered_platforms_are_absent():
    """Walmart, TikTok, TikTok Shop, Instagram, X and LinkedIn are not exposed here."""
    names = " ".join(str(n) for n in server.app._catalog.get_tool_names()).lower()
    for absent in ("walmart", "tiktok", "instagram", "linkedin", "twitter"):
        assert absent not in names


def test_deprecated_youtube_metadata_alias_not_exposed():
    """/youtube/metadata is a deprecated alias of /youtube/video, not a peer tool."""
    names = {str(n) for n in server.app._catalog.get_tool_names()}
    assert "Scavio.GetYoutubeMetadata" not in names
    assert "Scavio.GetYoutubeVideo" in names


def test_every_tool_requires_the_api_key_secret():
    """Arcade injects SCAVIO_API_KEY at call time; no tool may skip the requirement."""
    catalog = server.app._catalog
    for name in catalog.get_tool_names():
        definition = catalog.get_tool_by_name(str(name)).definition
        assert [s.key for s in definition.requirements.secrets] == ["SCAVIO_API_KEY"]


def test_every_tool_has_a_description():
    """Agents route off descriptions; a blank one makes a tool unusable."""
    catalog = server.app._catalog
    for name in catalog.get_tool_names():
        assert catalog.get_tool_by_name(str(name)).definition.description


def test_app_version_matches_the_package():
    """The version is declared twice - pyproject.toml and MCPApp(version=). Pin both."""
    import pathlib
    import re

    pyproject = (pathlib.Path(__file__).resolve().parents[1] / "pyproject.toml").read_text()
    declared = re.search(r'^version = "([^"]+)"', pyproject, re.M).group(1)
    assert server.app.version == declared == "0.3.2"


# --- wire-format tests -----------------------------------------------------


async def test_search_google_reads_top_level_organic_results(ctx):
    """Google v2 returns organic_results at the top level, not under data."""
    result = await server.search_google(ctx, "ai agents", max_results=2)
    assert _last_call() == ("search", ("ai agents",), {})
    assert result == []

    _FakeClient.last.responses["search"] = {
        "organic_results": [{"title": f"r{i}", "link": f"https://x/{i}", "snippet": "s"} for i in range(5)]
    }
    assert len(await server.search_google(ctx, "ai agents", max_results=2)) == 2


async def test_search_news_sends_query_as_a_kwarg(ctx):
    await server.search_news(ctx, "openai")
    assert _last_call() == ("news", (), {"query": "openai"})


async def test_search_reddit_sends_only_the_query(ctx):
    """/reddit/search takes query + cursor only; sort and type do not exist."""
    await server.search_reddit(ctx, "serpapi alternative")
    assert _last_call() == ("search", ("serpapi alternative",), {})


async def test_search_reddit_reads_nested_results(ctx):
    """Reddit search nests its posts under data.results, not data.posts."""
    await server.search_reddit(ctx, "x")
    _FakeClient.last.responses["search"] = {"data": {"results": [{"post_id": f"t3_{i}"} for i in range(4)]}}
    assert len(await server.search_reddit(ctx, "x", max_results=3)) == 3


async def test_search_youtube_reads_nested_results(ctx):
    await server.search_youtube(ctx, "langchain")
    _FakeClient.last.responses["search"] = {"data": {"results": [{"videoId": f"v{i}"} for i in range(4)]}}
    assert len(await server.search_youtube(ctx, "langchain", max_results=2)) == 2


async def test_youtube_transcript_defaults(ctx):
    """The 8-credit endpoint: language and format default to en/text."""
    await server.get_youtube_transcript(ctx, "dQw4w9WgXcQ")
    assert _last_call() == ("transcript", ("dQw4w9WgXcQ",), {"language": "en", "format": "text"})


async def test_youtube_video_unwraps_the_data_envelope(ctx):
    await server.get_youtube_video(ctx, "dQw4w9WgXcQ")
    _FakeClient.last.responses["video"] = {"data": {"title": "t"}, "response_time": 1.2}
    assert await server.get_youtube_video(ctx, "dQw4w9WgXcQ") == {"title": "t"}


async def test_youtube_channel_accepts_a_handle(ctx):
    await server.get_youtube_channel(ctx, "@veritasium")
    assert _last_call() == ("channel", ("@veritasium",), {})


async def test_search_amazon_reads_nested_products(ctx):
    await server.search_amazon(ctx, "laptop")
    assert _last_call() == ("search", ("laptop",), {})
    _FakeClient.last.responses["search"] = {"data": {"products": [{"asin": f"B{i}"} for i in range(4)]}}
    assert len(await server.search_amazon(ctx, "laptop", max_results=2)) == 2


# --- extract (core endpoint, not a platform) -------------------------------


async def test_extract_is_a_top_level_method_not_a_namespace(ctx):
    """client.extract(url, ...), never client.extract.extract()."""
    await server.extract_url(ctx, "https://example.com/pricing")
    assert _last_call() == (
        "extract",
        ("https://example.com/pricing",),
        {"format": "markdown", "mode": "normal"},
    )


async def test_extract_defaults_are_markdown_and_normal(ctx):
    """The cheap, boilerplate-stripped read is the default an agent gets."""
    await server.extract_url(ctx, "https://example.com")
    _method, _args, kwargs = _last_call()
    assert kwargs == {"format": "markdown", "mode": "normal"}


async def test_extract_forwards_format_and_mode(ctx):
    """mode is the PRICE-BEARING param (normal 1, advanced 1, ultra 2)."""
    await server.extract_url(ctx, "https://example.com", format="text", mode="ultra")
    assert _last_call() == (
        "extract",
        ("https://example.com",),
        {"format": "text", "mode": "ultra"},
    )


async def test_extract_unwraps_the_data_envelope_and_keeps_the_page_whole(ctx):
    """Extract returns page CONTENT, not a record list; nothing may truncate it."""
    body = "x" * 50_000
    _FakeClient.responses["extract"] = {
        "data": {
            "url": "https://example.com",
            "format": "markdown",
            "mode": "normal",
            "content": body,
            "content_length": len(body),
        },
        "response_time": 812,
        "credits_used": 1,
    }
    result = await server.extract_url(ctx, "https://example.com")
    assert result["content_length"] == 50_000
    assert len(result["content"]) == 50_000
    assert "credits_used" not in result


async def test_api_key_comes_from_the_arcade_secret(ctx):
    await server.search_google(ctx, "x")
    assert _FakeClient.last.api_key == "sk_live_test"


# --- map, crawl and batch --------------------------------------------------


def _job(status: str) -> dict:
    return {"data": {"id": "crawl_1", "status": status, "results": [], "next_cursor": None}}


@pytest.fixture
def fast(monkeypatch):
    monkeypatch.setattr(server, "JOB_POLL_INTERVAL", 0.0)


async def test_map_website_calls_extract_map_and_drops_none(ctx):
    result = await server.map_website(ctx, "scavio.dev", limit=3, include_paths=["/blog/**"])
    assert _last_call() == ("extract.map", ("scavio.dev",), {"limit": 3, "include_paths": ["/blog/**"]})
    assert result["returned"] == 1
    assert "credits_used" not in result


async def test_crawl_website_waits_until_completed(ctx, fast):
    _FakeClient.responses["status_queue"] = [_job("running"), _job("completed"), _job("completed")]
    result = await server.crawl_website(ctx, "https://hono.dev/docs", max_pages=2)
    calls = _FakeClient.calls
    assert calls[0] == ("extract.crawl", ("https://hono.dev/docs",), {"max_pages": 2})
    assert calls[1] == ("extract.crawl_status", ("crawl_1",), {"limit": 1, "include_content": False})
    assert calls[-1] == ("extract.crawl_status", ("crawl_1",), {"limit": 10})
    assert len(calls) == 4
    assert result["status"] == "completed"


async def test_crawl_website_wait_zero_returns_the_queued_job(ctx):
    result = await server.crawl_website(ctx, "https://hono.dev/docs", wait_seconds=0)
    assert len(_FakeClient.calls) == 1
    assert result == {"id": "crawl_1", "status": "queued"}


async def test_crawl_website_stops_waiting_when_time_runs_out(ctx, fast, monkeypatch):
    ticks = iter(range(0, 10_000, 10))
    monkeypatch.setattr(server.time, "monotonic", lambda: float(next(ticks)))
    _FakeClient.responses["status_queue"] = [_job("running")] * 5
    result = await server.crawl_website(ctx, "https://hono.dev/docs", wait_seconds=15)
    assert result["status"] == "running"
    assert len(_FakeClient.calls) == 3  # start, one probe, final read


async def test_get_crawl_status_passes_paging_through(ctx):
    await server.get_crawl_status(ctx, "crawl_1", cursor="25", include_content=False)
    assert _last_call() == ("extract.crawl_status", ("crawl_1",), {"cursor": "25", "limit": 10, "include_content": False})


async def test_batch_extract_and_status_use_the_batch_job(ctx, fast):
    urls = ["https://example.com/", "https://hono.dev/docs"]
    result = await server.batch_extract(ctx, urls, mode="normal")
    assert _FakeClient.calls[0] == ("extract.batch", (urls,), {"mode": "normal"})
    assert all(c[0] == "extract.batch_status" for c in _FakeClient.calls[1:])
    assert result["status"] == "completed"
    await server.get_batch_status(ctx, "batch_1", status="failed")
    assert _last_call() == ("extract.batch_status", ("batch_1",), {"limit": 10, "status": "failed"})


def test_descriptions_never_name_the_fetch_method():
    banned = ("proxy", "proxies", "residential", "datacenter", "headless", "browser")
    catalog = server.app._catalog
    for name in catalog.get_tool_names():
        definition = catalog.get_tool_by_name(str(name)).definition
        text = definition.model_dump_json().lower()
        for word in banned:
            assert word not in text, (str(name), word)
