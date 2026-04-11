import hashlib
import json
import random
from typing import AsyncIterator

import httpx
from openai import AsyncOpenAI

from src.config import get_settings
from src.external.retry import retry_with_backoff


def _get_llm_client() -> AsyncOpenAI | None:
    settings = get_settings()
    cfg = settings.llm_config
    if not (cfg.base_url and cfg.model):
        return None
    return AsyncOpenAI(base_url=cfg.base_url, api_key=cfg.api_key or "not-needed")


def _get_embedding_client() -> AsyncOpenAI | None:
    settings = get_settings()
    cfg = settings.embedding_config
    if not (cfg.base_url and cfg.model):
        return None
    return AsyncOpenAI(base_url=cfg.base_url, api_key=cfg.api_key or "not-needed")


_DEGRADED_MSG = "【降级模式】当前 LLM 服务不可用，请检查配置或网络连接后重试。"


async def chat_completion(
    messages: list[dict],
    stream: bool = False,
    temperature: float = 0.7,
    tools: list[dict] | None = None,
) -> str | AsyncIterator[str]:
    client = _get_llm_client()
    if client is None:
        if stream:
            async def _stream():
                yield _DEGRADED_MSG
            return _stream()
        return _DEGRADED_MSG

    async def _call():
        return await client.chat.completions.create(
            model=get_settings().llm_config.model,
            messages=messages,
            stream=stream,
            temperature=temperature,
            tools=tools,
        )

    try:
        response = await retry_with_backoff(
            _call,
            max_retries=get_settings().retry_settings.retry_times,
            timeout=get_settings().retry_settings.timeout_seconds,
        )
    except Exception:
        if stream:
            async def _stream():
                yield _DEGRADED_MSG
            return _stream()
        return _DEGRADED_MSG

    if stream:
        async def _stream():
            async for chunk in response:
                delta = chunk.choices[0].delta.content or ""
                if delta:
                    yield delta
        return _stream()

    return response.choices[0].message.content or ""


def _fallback_embedding(text: str, dim: int = 768) -> list[float]:
    seed = int(hashlib.sha256(text.encode("utf-8")).hexdigest(), 16) % (2 ** 32)
    rng = random.Random(seed)
    return [rng.uniform(-1.0, 1.0) for _ in range(dim)]


async def get_embeddings(texts: list[str]) -> list[list[float]]:
    client = _get_embedding_client()
    if client is None:
        return [_fallback_embedding(t) for t in texts]

    async def _call():
        resp = await client.embeddings.create(
            model=get_settings().embedding_config.model,
            input=texts,
        )
        return [item.embedding for item in resp.data]

    try:
        return await retry_with_backoff(
            _call,
            max_retries=get_settings().retry_settings.retry_times,
            timeout=get_settings().retry_settings.timeout_seconds,
        )
    except Exception:
        return [_fallback_embedding(t) for t in texts]


async def is_llm_available() -> bool:
    client = _get_llm_client()
    if client is None:
        return False
    try:
        await client.models.list(timeout=5)
        return True
    except Exception:
        return False
