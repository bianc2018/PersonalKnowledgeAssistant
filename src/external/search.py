from typing import List, Tuple

import httpx

from src.config import get_settings


async def search_web(query: str) -> List[dict]:
    """Search the web using configured independent search provider.

    Returns list of {title, url, summary} results.
    Falls back to empty list with a degradation marker when service is unavailable.
    """
    settings = get_settings()
    cfg = settings.search_config
    if cfg is None or not cfg.provider or not cfg.api_key:
        return [{"title": "【降级模式】搜索服务未配置", "url": "", "summary": ""}]

    provider = cfg.provider.lower()

    try:
        if provider == "tavily":
            return await _search_tavily(query, cfg.api_key)
        if provider in ("serpapi", "serp"):
            return await _search_serpapi(query, cfg.api_key)
    except Exception:
        return [{"title": "【降级模式】外部搜索服务暂不可用", "url": "", "summary": ""}]

    raise RuntimeError(f"Unsupported search provider: {cfg.provider}")


async def _search_tavily(query: str, api_key: str) -> List[dict]:
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            "https://api.tavily.com/search",
            json={"query": query, "api_key": api_key, "search_depth": "basic"},
        )
        resp.raise_for_status()
        data = resp.json()
        results = data.get("results", [])
        return [
            {
                "title": r.get("title", ""),
                "url": r.get("url", ""),
                "summary": r.get("content", ""),
            }
            for r in results
        ]


async def _search_serpapi(query: str, api_key: str) -> List[dict]:
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(
            "https://serpapi.com/search",
            params={
                "q": query,
                "api_key": api_key,
                "engine": "google",
                "num": 10,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        organic = data.get("organic_results", [])
        return [
            {
                "title": r.get("title", ""),
                "url": r.get("link", ""),
                "summary": r.get("snippet", ""),
            }
            for r in organic
        ]


async def fetch_url(url: str) -> Tuple[str, str | None]:
    """Fetch and extract article text from URL.

    Returns (text, error).
    """
    try:
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            resp = await client.get(
                url,
                headers={
                    "User-Agent": "PersonalKnowledgeAssistant-Bot/0.1.0"
                },
            )
            resp.raise_for_status()
            html = resp.text

        try:
            import trafilatura

            text = trafilatura.extract(html, include_comments=False)
            if text:
                return text, None
        except Exception:
            pass

        return html, None
    except Exception as e:
        return "", str(e)
