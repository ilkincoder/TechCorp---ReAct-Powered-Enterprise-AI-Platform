"""Web Search Tool — searches the web and returns grounded results."""

import httpx

from ..config import SEARCH_API_KEY, SEARCH_PROVIDER
from .base import BaseTool, ToolResult


class WebSearchTool(BaseTool):
    name = "web_search"
    description = """Search the internet for current information. Use this when the knowledge base
and database don't contain the answer — for recent news, external APIs,
competitor information, or general knowledge beyond TechCorp documents."""

    async def execute(self, query: str = "", num_results: int = 5, **kwargs) -> ToolResult:
        """Search the web for the given query."""
        if not query.strip():
            return ToolResult(
                tool_name=self.name,
                success=False,
                error="Search query is empty.",
            )

        try:
            if SEARCH_PROVIDER == "duckduckgo" or not SEARCH_API_KEY:
                results = await self._search_duckduckgo(query, num_results)
            else:
                results = await self._search_tavily(query, num_results)

            return ToolResult(
                tool_name=self.name,
                success=True,
                data={
                    "query": query,
                    "results": results,
                },
                citations=[r["url"] for r in results if r.get("url")],
                metadata={"provider": SEARCH_PROVIDER, "num_results": len(results)},
            )

        except Exception as e:
            return ToolResult(
                tool_name=self.name,
                success=False,
                error=str(e),
            )

    async def _search_duckduckgo(self, query: str, num: int) -> list[dict]:
        """Free search via DuckDuckGo HTML (no API key required). Retries once on empty."""
        from html.parser import HTMLParser

        class DDGParser(HTMLParser):
            def __init__(self):
                super().__init__()
                self.results = []
                self._current = {}
                self._in_result = False
                self._in_snippet = False
                self._in_link = False
                self._tag = ""

            def handle_starttag(self, tag, attrs):
                attrs = dict(attrs)
                if tag == "a" and "result__a" in attrs.get("class", ""):
                    self._current = {"title": "", "url": attrs.get("href", ""), "snippet": ""}
                    self._in_link = True
                elif tag == "a" and "result__snippet" in attrs.get("class", ""):
                    self._in_snippet = True

            def handle_data(self, data):
                if self._in_link:
                    self._current["title"] += data.strip()
                elif self._in_snippet:
                    self._current["snippet"] += data.strip()

            def handle_endtag(self, tag):
                if tag == "a" and self._in_link:
                    self._in_link = False
                elif tag == "a" and self._in_snippet:
                    self._in_snippet = False
                    if self._current.get("title"):
                        self.results.append(self._current)
                    self._current = {}

        def _clean_urls(results):
            from urllib.parse import urlparse, parse_qs, unquote
            for r in results:
                url = r.get("url", "")
                if "duckduckgo.com/l/" in url and "uddg=" in url:
                    try:
                        parsed = urlparse(url)
                        qs = parse_qs(parsed.query)
                        real = qs.get("uddg", [""])[0]
                        if real:
                            r["url"] = unquote(real)
                    except Exception:
                        pass

        async def _fetch_and_parse():
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(
                    "https://html.duckduckgo.com/html/",
                    params={"q": query},
                    headers={"User-Agent": "TechCorp-AI-Platform/1.0"},
                )
                resp.raise_for_status()
            parser = DDGParser()
            parser.feed(resp.text)
            _clean_urls(parser.results)
            return parser.results[:num]

        results = await _fetch_and_parse()

        # Retry once on empty (transient rate limiting or HTML format change)
        if not results:
            import asyncio
            await asyncio.sleep(1)
            results = await _fetch_and_parse()

        return results

    async def _search_tavily(self, query: str, num: int) -> list[dict]:
        """Paid search via Tavily API."""
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": SEARCH_API_KEY,
                    "query": query,
                    "max_results": num,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return [
                {"title": r.get("title", ""), "url": r.get("url", ""), "snippet": r.get("content", "")}
                for r in data.get("results", [])
            ]

    def _input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query for the web",
                },
                "num_results": {
                    "type": "integer",
                    "description": "Number of results to return (default 5)",
                    "default": 5,
                },
            },
            "required": ["query"],
        }