"""
Lightweight DuckDuckGo web search for BlitzDev agent.
No API key needed. Used to ground answers with real, current information.
"""

import asyncio
import aiohttp
import re
from typing import List, Optional
from dataclasses import dataclass


@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str


# DuckDuckGo HTML search (no API key, no rate limit issues)
_DDG_URL = "https://html.duckduckgo.com/html/"
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
}


async def web_search(query: str, max_results: int = 5, timeout: float = 8.0) -> List[SearchResult]:
    """Search DuckDuckGo and return top results.
    
    Fast, free, no API key. Returns title + snippet for each result.
    Used to inject real-time context into LLM prompts.
    
    Args:
        query: Search query string
        max_results: Max results to return (default 5)
        timeout: Request timeout in seconds
        
    Returns:
        List of SearchResult with title, url, snippet
    """
    results: List[SearchResult] = []
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                _DDG_URL,
                data={"q": query, "b": ""},
                headers=_HEADERS,
                timeout=aiohttp.ClientTimeout(total=timeout),
            ) as resp:
                if resp.status != 200:
                    return results
                html = await resp.text()
    except (aiohttp.ClientError, asyncio.TimeoutError):
        return results
    
    # Parse results from DDG HTML response
    # Each result block: <div class="result ..."> ... </div>
    result_blocks = re.findall(
        r'<div[^>]*class="[^"]*result[^"]*results_links[^"]*"[^>]*>(.*?)</div>\s*</div>',
        html, re.DOTALL
    )
    
    if not result_blocks:
        # Fallback: try simpler pattern
        result_blocks = re.findall(
            r'<div[^>]*class="[^"]*result ".*?>(.*?)<div[^>]*class="[^"]*clear',
            html, re.DOTALL
        )
    
    for block in result_blocks[:max_results]:
        # Extract title
        title_match = re.search(r'<a[^>]*class="result__a"[^>]*>(.*?)</a>', block, re.DOTALL)
        title = _strip_html(title_match.group(1)) if title_match else ""
        
        # Extract URL
        url_match = re.search(r'<a[^>]*class="result__a"[^>]*href="([^"]*)"', block)
        url = url_match.group(1) if url_match else ""
        
        # Extract snippet
        snippet_match = re.search(r'<a[^>]*class="result__snippet"[^>]*>(.*?)</a>', block, re.DOTALL)
        if not snippet_match:
            snippet_match = re.search(r'class="result__snippet"[^>]*>(.*?)</(?:a|div)', block, re.DOTALL)
        snippet = _strip_html(snippet_match.group(1)) if snippet_match else ""
        
        if title or snippet:
            results.append(SearchResult(title=title, url=url, snippet=snippet))
    
    return results


def _strip_html(text: str) -> str:
    """Remove HTML tags and decode entities."""
    text = re.sub(r'<[^>]+>', '', text)
    text = text.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    text = text.replace("&quot;", '"').replace("&#x27;", "'").replace("&nbsp;", " ")
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def format_search_context(results: List[SearchResult]) -> str:
    """Format search results as context for LLM injection.
    
    Returns a compact string suitable for prepending to an LLM prompt.
    """
    if not results:
        return ""
    
    lines = ["WEB SEARCH RESULTS (use these for accuracy, cite sources when relevant):"]
    for i, r in enumerate(results, 1):
        lines.append(f"[{i}] {r.title}")
        if r.snippet:
            lines.append(f"    {r.snippet}")
        if r.url:
            lines.append(f"    Source: {r.url}")
    lines.append("")
    return "\n".join(lines)


def needs_web_search(prompt: str) -> bool:
    """Heuristic: does this prompt benefit from web search?
    
    Returns True for current events, factual questions, prices, news, etc.
    Returns False for creative writing, opinions, generic tasks.
    """
    p = prompt.lower()
    
    # Strong signals: needs current/real-time info
    _SEARCH_TRIGGERS = [
        "latest", "recent", "current", "today", "yesterday", "this week",
        "this month", "this year", "2024", "2025", "2026",
        "news", "update", "developments", "happening",
        "price of", "cost of", "how much does", "market",
        "who won", "who is winning", "election", "war",
        "stock", "crypto", "bitcoin", "ethereum", "solana",
        "weather", "score", "result",
        "statistics", "stats", "data on", "data about",
        "compare", "vs", "versus",
        "best", "top rated", "review of",
        "what happened", "what's happening", "what is happening",
        # Specific entities that need grounding
        "seedstr", "seedstr.io",
    ]
    
    for trigger in _SEARCH_TRIGGERS:
        if trigger in p:
            return True
    
    # Questions starting with "who is", "what is" often need facts
    if re.match(r'^(who is|what is|when did|where is|how many|how much)', p):
        return True
    
    return False
