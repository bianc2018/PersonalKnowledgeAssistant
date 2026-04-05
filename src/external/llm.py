import json
from typing import AsyncIterator

import httpx
from openai import AsyncOpenAI

from src.config import get_settings


def _get_llm_client() -> AsyncOpenAI | None:
    settings = get_settings()
    cfg = settings.llm_config
    if not (cfg.base_url and cfg.api_key and cfg.model):
        return None
    return AsyncOpenAI(base_url=cfg.base_url, api_key=cfg.api_key)


def _get_embedding_client() -> AsyncOpenAI | None:
    settings = get_settings()
    cfg = settings.embedding_config
    if not (cfg.base_url and cfg.api_key and cfg.model):
        return None
    return AsyncOpenAI(base_url=cfg.base_url, api_key=cfg.api_key)


async def chat_completion(
    messages: list[dict],
    stream: bool = False,
    temperature: float = 0.7,
    tools: list[dict] | None = None,
) -> str | AsyncIterator[str]:
    client = _get_llm_client()
    if client is None:
        raise RuntimeError("LLM not configured")

    response = await client.chat.completions.create(
        model=get_settings().llm_config.model,
        messages=messages,
        stream=stream,
        temperature=temperature,
        tools=tools,
    )

    if stream:
        async def _stream():
            async for chunk in response:
                delta = chunk.choices[0].delta.content or ""
                if delta:
                    yield delta
        return _stream()

    return response.choices[0].message.content or ""


async def get_embeddings(texts: list[str]) -> list[list[float]]:
    client = _get_embedding_client()
    if client is None:
        raise RuntimeError("Embedding client not configured")

    response = await client.embeddings.create(
        model=get_settings().embedding_config.model,
        input=texts,
    )
    return [item.embedding for item in response.data]


async def is_llm_available() -> bool:
    client = _get_llm_client()
    if client is None:
        return False
    try:
        await client.models.list(timeout=5)
        return True
    except Exception:
        return False
