# arcade-scavio

[Scavio](https://scavio.dev) real-time search and page-extraction tools for [Arcade.dev](https://arcade.dev) and MCP — Google, Google News, Reddit, YouTube, Amazon, `extract_url` (read any web page), and tools to map a site's URLs, crawl a whole site, and batch-extract a URL list, with one API key. A cost-effective [Tavily alternative](https://scavio.dev/docs) and [SerpAPI alternative](https://scavio.dev/docs) for Arcade agents.

## Install

```bash
pip install arcade-scavio
```

## Scope: 15 tools, by design

This toolkit is a **curated subset** of the Scavio API, not a wrapper around all of it. It exposes **15** tools — 9 endpoints across **4** of Scavio's 31 platforms, plus the core Extract family, which belongs to no platform: `extract_url` for one page, and map, crawl and batch for whole sites:

| Tool | Endpoint | Platform | Credits |
|---|---|---|---|
| `extract_url` | `POST /api/v1/extract` | *(core, not a platform)* | 1 / 1 / 2 by `mode` |
| `search_google` | `POST /api/v2/google` | Google | 1 |
| `search_news` | `POST /api/v2/google/news` | Google | 1 |
| `search_reddit` | `POST /api/v1/reddit/search` | Reddit | 1 |
| `search_youtube` | `POST /api/v1/youtube/search` | YouTube | 2 |
| `get_youtube_video` | `POST /api/v1/youtube/video` | YouTube | 1 |
| `get_youtube_transcript` | `POST /api/v1/youtube/transcript` | YouTube | 5 |
| `list_youtube_comments` | `POST /api/v1/youtube/comments` | YouTube | 1 |
| `get_youtube_channel` | `POST /api/v1/youtube/channel` | YouTube | 1 |
| `search_amazon` | `POST /api/v1/amazon/search` | Amazon | 1 |
| `map_website` | `POST /api/v1/extract/map` | *(Extract)* | 1 on `normal` (up to 2 / 10 on `advanced` / `ultra`) |
| `crawl_website` | `POST /api/v1/extract/crawl` | *(Extract)* | per successful page, 1 / 1 / 2 by `mode` |
| `get_crawl_status` | `GET /api/v1/extract/crawl/{id}` | *(Extract)* | free |
| `batch_extract` | `POST /api/v1/extract/batch` | *(Extract)* | per successful page, 1 / 1 / 2 by `mode` |
| `get_batch_status` | `GET /api/v1/extract/batch/{id}` | *(Extract)* | free |

Platforms covered here: **Google (2), YouTube (5), Reddit (1), Amazon (1)**, plus `extract_url`, which is tied to no platform — it reads any URL. Not covered: Walmart, TikTok, TikTok Shop, Instagram, X, LinkedIn, eBay, Target, Home Depot, Zillow, Redfin, Booking, Airbnb, Tripadvisor, Yelp, Indeed, Glassdoor, the App Store, Google Play, SEC, Companies House, G2, Capterra, Google Ads, Meta Ad Library, Threads, Kuaishou, and the other 12 Google v2 verticals (Maps, Shopping, Flights, Hotels, Trends, AI Mode, ...). That is deliberate — a hand-picked toolkit an agent routes correctly beats a hundred near-identical tools — and it stays that way.

### Map, crawl and batch

`map_website` answers in one call with a site's page URLs, gathered from its sitemaps and start page. `crawl_website` and `batch_extract` start a background job, **wait up to `wait_seconds` (default 45, max 300)** for it to finish, and return the job's `id`, `status`, `pages`, `credits_used`, up to `limit` page results (default 10) and `next_cursor`. Arcade tools are request/response, so a job that is still `queued` or `running` when the wait ends keeps going server-side; read it, and any further pages, with `get_crawl_status` / `get_batch_status` and the `id`. Set `wait_seconds=0` to get the id back at once, which suits a platform with a short tool-call timeout.

Crawl and batch bill **per successful page** at extract's price for the mode (normal and advanced 1 credit, ultra 2); failed and skipped pages are free, and a job stops cleanly with `stopped_reason: "insufficient_credits"` if the balance runs out. Reading a job is free. Crawl and map obey the site's robots.txt; results are kept for 3 days. Plan limits (pages per crawl / active jobs / URLs per batch): Free 10/1/10, PAYG 100/1/50, Project 500/2/100, Bootstrap 2,000/3/500, Startup 5,000/5/1,000, Growth 10,000/10/1,000. Cancellation, webhooks and idempotency keys exist on the [REST API](https://scavio.dev/docs/extract) and in the `scavio` SDK, but are not tools here.

Each tool reads the `SCAVIO_API_KEY` secret, which Arcade injects securely at call time (the client and LLM never see the value).

## Credits

**This toolkit is not flat 1 credit.** Seven of the search tools cost 1, `search_youtube` costs 2, `get_youtube_transcript` costs **5**, and `extract_url` is priced by the tier you ask for rather than per call.

| Tool | Credits |
|---|---|
| `search_google`, `search_news`, `search_reddit`, `get_youtube_video`, `list_youtube_comments`, `get_youtube_channel`, `search_amazon` | 1 |
| `search_youtube` | 2 |
| `get_youtube_transcript` | 5 |
| `extract_url` | **1** on `mode="normal"`, **1** on `"advanced"`, **2** on `"ultra"` |
| `map_website` | **1** on `normal`; up to 2 on `advanced`, up to 10 on `ultra` |
| `crawl_website`, `batch_extract` | per successful page: **1** on `normal` or `advanced`, **2** on `ultra` |
| `get_crawl_status`, `get_batch_status` | free |

`extract_url` bills only on a successful read: a dead link, a bot wall or a timeout costs nothing. Start on `normal`; move to `advanced` when the page builds its content with JavaScript, and to `ultra` only for the hardest pages. See [the extract docs](https://scavio.dev/docs/extract).

Elsewhere in the API (not exposed here): YouTube streams 3, Instagram 1-2 (up to 10), LinkedIn 1-10 with a job at 30, Kuaishou 1-40 per endpoint, G2 5, Capterra 2, everything else 1. New accounts get 50 one-time signup credits — no monthly refill, no credit card.

## Run standalone

```bash
export SCAVIO_API_KEY=sk_live_...   # get one at https://dashboard.scavio.dev
python -m arcade_scavio.server          # stdio
python -m arcade_scavio.server http     # HTTP+SSE
```

## Deploy to Arcade Cloud

```bash
arcade login
arcade deploy
```

Arcade discovers the `SCAVIO_API_KEY` secret and hosts it encrypted; the Arcade Engine fulfils authorized tool calls for your users.

## Every endpoint via MCP

Need Walmart, TikTok, TikTok Shop, Instagram, X, LinkedIn, eBay, Zillow, Booking, Indeed, the App Store, SEC filings, Maps, Shopping, Flights or Hotels? Scavio runs a hosted MCP server at `https://mcp.scavio.dev/mcp` that exposes **191 tools** across all 195 endpoints, authenticated with an `x-api-key` header — no install, no toolkit to deploy. See the [MCP docs](https://scavio.dev/docs/mcp).

## About Scavio

[Scavio](https://scavio.dev) is a real-time search API built for AI agents — a unified API over **Google, YouTube, Amazon, Walmart, Reddit, TikTok, TikTok Shop, Instagram, X, LinkedIn, eBay, Target, Home Depot, Zillow, Redfin, Booking, Airbnb, Tripadvisor, Yelp, Indeed, Glassdoor, the App Store, Google Play, SEC, Companies House, G2, Capterra, Google Ads, Meta Ad Library, Threads and Kuaishou** that returns clean JSON, plus `extract` to read any URL. 195 live endpoints across 31 platforms, one key. A broader, cost-effective [Tavily alternative](https://scavio.dev/docs) and [SerpAPI alternative](https://scavio.dev/docs). See the [Arcade integration docs](https://scavio.dev/docs/arcade).

## Development

```bash
pip install -e ".[dev]"
pytest
```

## Links

- Scavio: https://scavio.dev
- Docs: https://scavio.dev/docs/arcade
- Dashboard: https://dashboard.scavio.dev
