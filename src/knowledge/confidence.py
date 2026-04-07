import uuid
from datetime import datetime, timezone
from typing import Optional

import aiosqlite

from src.config import get_settings
from src.external.llm import chat_completion


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def evaluate_confidence(
    db: aiosqlite.Connection, version_id: str, content_text: str
) -> Optional[str]:
    """Run confidence evaluation for a knowledge version and store the result."""
    settings = get_settings()
    privacy = settings.privacy_settings
    use_web = privacy.allow_web_search

    method = "commonsense_reasoning"
    search_context = ""
    if use_web:
        try:
            from src.external.search import search_web

            results = await search_web(content_text[:200])
            snippets = [r.get("summary", "") for r in results[:3]]
            search_context = "\n".join(snippets)
            method = "hybrid"
        except Exception:
            pass

    search_part = f"网络交叉验证摘要：\n{search_context}" if search_context else ""
    prompt = f"""你是一个事实核查助手。请对以下知识内容的置信度进行评估。

知识内容：
{content_text}

{search_part}

请输出 JSON 格式：{{"score_level": "high|medium|low", "score_value": 0.0~1.0, "rationale": "评估依据"}}。
只输出 JSON。"""

    try:
        raw = await chat_completion(
            [{"role": "user", "content": prompt}], stream=False
        )
    except Exception:
        return None

    result = _safe_json_parse(raw)
    if result is None:
        return None

    score_level = result.get("score_level", "medium")
    score_value = result.get("score_value")
    rationale = result.get("rationale", "")

    eval_id = str(uuid.uuid4())
    await db.execute(
        """
        INSERT INTO confidence_evaluations (id, version_id, score_level, score_value, method, rationale, evaluated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(version_id) DO UPDATE SET
            score_level=excluded.score_level,
            score_value=excluded.score_value,
            method=excluded.method,
            rationale=excluded.rationale,
            evaluated_at=excluded.evaluated_at
        """,
        (eval_id, version_id, score_level, score_value, method, rationale, _now()),
    )
    await db.commit()
    return eval_id


def _safe_json_parse(text: str) -> Optional[dict]:
    try:
        import json

        raw = text.strip()
        if raw.startswith("```"):
            raw = raw.split("```json", 1)[-1].split("```", 1)[0].strip()
        elif raw.startswith("`"):
            raw = raw.strip("`")
        return json.loads(raw)
    except Exception:
        return None
