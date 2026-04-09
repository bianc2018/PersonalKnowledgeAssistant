import json
from typing import List, Tuple

import httpx

from src.config import get_settings
from src.external.llm import chat_completion
from src.external.retry import retry_with_backoff


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
            return await retry_with_backoff(
                lambda: _search_tavily(query, cfg.api_key),
                max_retries=settings.retry_settings.retry_times,
                timeout=settings.retry_settings.timeout_seconds,
            )
        if provider in ("serpapi", "serp"):
            return await retry_with_backoff(
                lambda: _search_serpapi(query, cfg.api_key),
                max_retries=settings.retry_settings.retry_times,
                timeout=settings.retry_settings.timeout_seconds,
            )
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
    settings = get_settings()

    async def _call():
        async with httpx.AsyncClient(
            timeout=settings.retry_settings.timeout_seconds, follow_redirects=True
        ) as client:
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

    try:
        return await retry_with_backoff(
            _call,
            max_retries=settings.retry_settings.retry_times,
            timeout=settings.retry_settings.timeout_seconds,
        )
    except Exception as e:
        return "", str(e)


def _safe_json_parse(text: str):
    try:
        raw = text.strip()
        if raw.startswith("```"):
            raw = raw.split("```json", 1)[-1].split("```", 1)[0].strip()
        elif raw.startswith("`"):
            raw = raw.strip("`")
        return json.loads(raw)
    except Exception:
        return None


async def search_llm_builtin(query: str) -> List[dict]:
    """Use the configured LLM to generate structured search results.

    This implements the 'LLM builtin search' path from FR-006a.
    """
    settings = get_settings()
    prompt = f"""你是一个具备网络搜索能力的 AI 助手。请针对以下查询，返回最多 5 条结构化的搜索结果。

查询：{query}

请以 JSON 数组格式输出，每条结果包含字段 title、url、summary。只输出 JSON，不要任何其他解释文字。"""

    async def _call():
        return await chat_completion(
            [{"role": "user", "content": prompt}],
            stream=False,
            temperature=0.3,
        )

    try:
        response = await retry_with_backoff(
            _call,
            max_retries=settings.retry_settings.retry_times,
            timeout=settings.retry_settings.timeout_seconds,
        )
    except Exception:
        return []

    data = _safe_json_parse(response)
    if isinstance(data, list):
        return [
            {
                "title": str(r.get("title", "")),
                "url": str(r.get("url", "")),
                "summary": str(r.get("summary", "")),
            }
            for r in data
        ]
    return []
