"""
mcp_servers/search_server.py
══════════════════════════════════════════════════════════════════════════════
MCP SERVER 2 — Web Search Tools
══════════════════════════════════════════════════════════════════════════════

This server exposes two tools:

  • search_web     →  Uses Wikipedia's free API to fetch a plain-text
                      summary about any topic (no API key needed).
  • fetch_image    →  Uses the Pexels API to find a relevant stock photo
                      URL for a given keyword.

Why a separate MCP server?
  Keeping search logic separate from presentation logic means you can swap
  in a different search provider (Google, Bing, etc.) later without touching
  the agent or the PPT server.

Run standalone to test:
  python mcp_servers/search_server.py
"""

import os
import json
import requests
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
import asyncio
from dotenv import load_dotenv

load_dotenv()

PEXELS_API_KEY = os.getenv("PEXELS_API_KEY", "")

# ── Server setup ──────────────────────────────────────────────────────────────
app = Server("search-server")


@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="search_web",
            description="Search Wikipedia for a plain-text summary about a topic. "
                        "Use this to get real, factual content for slide bullet points. "
                        "Returns 3-5 sentences about the topic.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search term, e.g. 'life cycle of a star'"
                    }
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="fetch_image",
            description="Search Pexels for a relevant stock photo URL. "
                        "Returns an image URL string or an empty string if none found.",
            inputSchema={
                "type": "object",
                "properties": {
                    "keyword": {
                        "type": "string",
                        "description": "Image search keyword, e.g. 'nebula space stars'"
                    }
                },
                "required": ["keyword"]
            }
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:

    # ── Tool: search_web ──────────────────────────────────────────────────────
    if name == "search_web":
        query = arguments["query"]
        try:
            # Wikipedia's free REST API — no key required
            url = "https://en.wikipedia.org/api/rest_v1/page/summary/" + \
                  query.replace(" ", "_")
            response = requests.get(url, timeout=8,
                                    headers={"User-Agent": "AutoPPTAgent/1.0"})

            if response.status_code == 200:
                data = response.json()
                # Return the extract (first few paragraphs)
                extract = data.get("extract", "")
                # Trim to ~500 chars so we don't overwhelm the agent context
                if len(extract) > 600:
                    extract = extract[:600] + "..."
                return [TextContent(type="text", text=json.dumps({
                    "status": "ok",
                    "source": "Wikipedia",
                    "content": extract
                }))]
            else:
                # Wikipedia didn't find the exact page — try a search fallback
                search_url = "https://en.wikipedia.org/w/api.php"
                params = {
                    "action": "opensearch",
                    "search": query,
                    "limit": 1,
                    "format": "json"
                }
                r2 = requests.get(search_url, params=params, timeout=8)
                if r2.status_code == 200:
                    results = r2.json()
                    if results[1]:   # results[1] = list of titles
                        return [TextContent(type="text", text=json.dumps({
                            "status": "ok",
                            "source": "Wikipedia search",
                            "content": results[2][0] if results[2] else
                                       f"Found page: {results[1][0]}"
                        }))]

                return [TextContent(type="text", text=json.dumps({
                    "status": "not_found",
                    "content": ""
                }))]

        except requests.exceptions.RequestException as e:
            # Network error → graceful fallback
            return [TextContent(type="text", text=json.dumps({
                "status": "error",
                "error": str(e),
                "content": ""   # Agent will use LLM knowledge instead
            }))]

    # ── Tool: fetch_image ─────────────────────────────────────────────────────
    elif name == "fetch_image":
        keyword = arguments["keyword"]

        if not PEXELS_API_KEY:
            return [TextContent(type="text", text=json.dumps({
                "status": "no_key",
                "image_url": "",
                "message": "PEXELS_API_KEY not set. Skipping image fetch."
            }))]

        try:
            headers = {"Authorization": PEXELS_API_KEY}
            params  = {"query": keyword, "per_page": 1, "orientation": "landscape"}
            r = requests.get("https://api.pexels.com/v1/search",
                             headers=headers, params=params, timeout=8)

            if r.status_code == 200:
                data  = r.json()
                photos = data.get("photos", [])
                if photos:
                    img_url = photos[0]["src"]["large"]
                    return [TextContent(type="text", text=json.dumps({
                        "status": "ok",
                        "image_url": img_url
                    }))]

            return [TextContent(type="text", text=json.dumps({
                "status": "not_found",
                "image_url": ""
            }))]

        except requests.exceptions.RequestException as e:
            return [TextContent(type="text", text=json.dumps({
                "status": "error",
                "error": str(e),
                "image_url": ""
            }))]

    else:
        return [TextContent(type="text", text=json.dumps({
            "status": "error",
            "message": f"Unknown tool: {name}"
        }))]


# ── Entry point ───────────────────────────────────────────────────────────────
async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
