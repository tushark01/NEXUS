"""Web search skill — searches the web via HTTP APIs."""

from __future__ import annotations

from typing import Any

import httpx

from nexus.security.capabilities import Capability
from nexus.skills.base import BaseSkill, ParameterDef, SkillManifest, SkillResult


class WebSearchSkill(BaseSkill):
    """Search the web for information."""

    manifest = SkillManifest(
        name="web_search",
        description="Search the web for up-to-date information on any topic",
        capabilities_required=[Capability.NETWORK_HTTP],
        parameters={
            "query": ParameterDef(
                type="string",
                description="The search query",
                required=True,
            ),
            "max_results": ParameterDef(
                type="integer",
                description="Maximum number of results to return",
                required=False,
                default=5,
            ),
        },
    )

    async def execute(self, params: dict[str, Any]) -> SkillResult:
        query = params.get("query", "")
        max_results = params.get("max_results", 5)

        if not query:
            return SkillResult(success=False, error="Query is required")

        # Use DuckDuckGo HTML search (no API key needed)
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(
                    "https://html.duckduckgo.com/html/",
                    params={"q": query},
                    headers={"User-Agent": "NEXUS/0.1"},
                    follow_redirects=True,
                )
                response.raise_for_status()

                # Simple HTML parsing — extract result snippets
                results = self._parse_results(response.text, max_results)

                if results:
                    formatted = "\n\n".join(
                        f"**{r['title']}**\n{r['snippet']}" for r in results
                    )
                    return SkillResult(
                        success=True,
                        output=formatted,
                        metadata={"result_count": len(results)},
                    )
                return SkillResult(
                    success=True,
                    output="No results found.",
                    metadata={"result_count": 0},
                )

        except httpx.HTTPError as e:
            return SkillResult(success=False, error=f"Search failed: {e}")

    def _parse_results(self, html: str, max_results: int) -> list[dict[str, str]]:
        """Extract search results from DuckDuckGo HTML response."""
        results: list[dict[str, str]] = []

        # Simple parsing without BeautifulSoup dependency
        parts = html.split('class="result__a"')
        for part in parts[1 : max_results + 1]:
            title = ""
            snippet = ""

            # Extract title
            title_end = part.find("</a>")
            if title_end > 0:
                title_text = part[:title_end]
                # Strip HTML tags
                title = self._strip_tags(title_text).strip()

            # Extract snippet
            snippet_start = part.find('class="result__snippet"')
            if snippet_start > 0:
                snippet_part = part[snippet_start:]
                snippet_tag_end = snippet_part.find(">")
                snippet_close = snippet_part.find("</")
                if snippet_tag_end > 0 and snippet_close > snippet_tag_end:
                    snippet = self._strip_tags(
                        snippet_part[snippet_tag_end + 1 : snippet_close]
                    ).strip()

            if title:
                results.append({"title": title, "snippet": snippet})

        return results

    def _strip_tags(self, html: str) -> str:
        """Remove HTML tags from a string."""
        import re

        return re.sub(r"<[^>]+>", "", html)
