# arcade-scavio

[Scavio](https://scavio.dev) real-time search and page-extraction tools for [Arcade.dev](https://arcade.dev) and MCP — Google, Google News, Reddit, YouTube, Amazon, and `extract_url` (read any web page), with one API key. A cost-effective [Tavily alternative](https://scavio.dev/docs) and [SerpAPI alternative](https://scavio.dev/docs) for Arcade agents.

## Install

```bash
pip install arcade-scavio
```

## Scope: 10 endpoints, by design

This toolkit is a **curated subset** of the Scavio API, not a wrapper around all of it. It exposes **10** of Scavio's 195 endpoints — 9 across **4** of its 31 platforms, plus the core `extract` endpoint, which belongs to no platform:

| Tool | Endpoint | Platform | Credits |
|---|---|---|---|
| `extract_url` | `POST /api/v1/extract` | *(core, not a platform)* | 1 / 1 / 2 by `mode` |
| `search_google` | `POST /api/v2/google` | Google | 1 |
| `search_news` | `POST /api/v2/google/news` | Google | 1 |
| `search_reddit` | `POST /api/v1/reddit/search` | Reddit | 1 |
| `search_youtube` | `POST /api/v1/youtube/search` | YouTube | 2 |
| `get_youtube_video` | `POST /api/v1/youtube/video` | YouTube | 1 |
| `get_youtube_transcript` | `POST /api/v1/youtube/transcript` | YouTube | 8 |
| `list_youtube_comments` | `POST /api/v1/youtube/comments` | YouTube | 1 |
| `get_youtube_channel` | `POST /api/v1/youtube/channel` | YouTube | 1 |
| `search_amazon` | `POST /api/v1/amazon/search` | Amazon | 1 |

Platforms covered here: **Google (2), YouTube (5), Reddit (1), Amazon (1)**, plus `extract_url`, which is tied to no platform — it reads any URL. Not covered: Walmart, TikTok, TikTok Shop, Instagram, X, LinkedIn, eBay, Target, Home Depot, Zillow, Redfin, Booking, Airbnb, Tripadvisor, Yelp, Indeed, Glassdoor, the App Store, Google Play, SEC, Companies House, G2, Capterra, Google Ads, Meta Ad Library, Threads, Kuaishou, and the other 12 Google v2 verticals (Maps, Shopping, Flights, Hotels, Trends, AI Mode, ...). That is deliberate — a hand-picked toolkit an agent routes correctly beats a hundred near-identical tools — and it stays that way.

Each tool reads the `SCAVIO_API_KEY` secret, which Arcade injects securely at call time (the client and LLM never see the value).

## Credits

**This toolkit is not flat 1 credit.** Seven of the ten tools cost 1, `search_youtube` costs 2, `get_youtube_transcript` costs **8**, and `extract_url` is priced by the tier you ask for rather than per call.

| Tool | Credits |
|---|---|
| `search_google`, `search_news`, `search_reddit`, `get_youtube_video`, `list_youtube_comments`, `get_youtube_channel`, `search_amazon` | 1 |
| `search_youtube` | 2 |
| `get_youtube_transcript` | 8 |
| `extract_url` | **1** on `mode="normal"`, **1** on `"advanced"`, **2** on `"ultra"` |

`extract_url` bills only on a successful read: a dead link, a bot wall or a timeout costs nothing. Start on `normal`; move to `advanced` when the page builds its content in the browser, and to `ultra` only when a bot wall blocks the other two. See [the extract docs](https://scavio.dev/docs/extract).

Elsewhere in the API (not exposed here): YouTube streams 3, Instagram 2-10, LinkedIn 1-10 with a job at 30, Kuaishou 1-40 per endpoint, G2 5, Capterra 2, everything else 1. New accounts get 50 one-time signup credits — no monthly refill, no credit card.

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
