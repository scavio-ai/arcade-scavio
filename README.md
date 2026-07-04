# arcade-scavio

[Scavio](https://scavio.dev) real-time search tools for [Arcade.dev](https://arcade.dev) and MCP — Google, Google News, Reddit, YouTube, and Amazon, with one API key. A cost-effective [Tavily alternative](https://scavio.dev/docs) and [SerpAPI alternative](https://scavio.dev/docs) for Arcade agents.

## Install

```bash
pip install arcade-scavio
```

## Tools

An `arcade-mcp-server` toolkit exposing:

| Tool | Description |
|---|---|
| `search_google` | Google SERP — real-time organic web results |
| `search_news` | Google News — recent articles on a topic |
| `search_reddit` | Reddit posts — community discussion and sentiment |
| `search_youtube` | YouTube — videos |
| `search_amazon` | Amazon — product listings |

Each tool reads the `SCAVIO_API_KEY` secret, which Arcade injects securely at call time (the client and LLM never see the value).

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

Need Walmart, TikTok, Instagram, Maps, Shopping, and more? Scavio also runs a hosted MCP server at [`mcp.scavio.dev`](https://scavio.dev/docs/mcp) with the full tool catalog.

## About Scavio

[Scavio](https://scavio.dev) is a real-time search API built for AI agents — a unified API over Google, YouTube, Amazon, Walmart, Reddit, TikTok, and Instagram that returns clean JSON. A broader, cost-effective [Tavily alternative](https://scavio.dev/docs) and [SerpAPI alternative](https://scavio.dev/docs). See the [Arcade integration docs](https://scavio.dev/docs/arcade).

## Links

- Scavio: https://scavio.dev
- Docs: https://scavio.dev/docs/arcade
- Dashboard: https://dashboard.scavio.dev
