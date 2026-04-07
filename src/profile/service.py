import json
import uuid
from datetime import datetime, timezone
from typing import Optional

import aiosqlite

from src.chat.models import MessageOut
from src.db.connection import get_db
from src.external.llm import chat_completion


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def _count_rounds(db: aiosqlite.Connection, conversation_id: str) -> int:
    async with db.execute(
        "SELECT COUNT(*) FROM messages WHERE conversation_id = ? AND role = 'user'",
        (conversation_id,),
    ) as cursor:
        row = await cursor.fetchone()
    return row[0] if row else 0


async def update_profile_if_needed(
    db: aiosqlite.Connection, conversation_id: str
) -> None:
    """Trigger profile update every ~5 rounds or on new domain."""
    rounds = await _count_rounds(db, conversation_id)
    # Simple heuristic: update every 5 user messages
    if rounds == 0 or rounds % 5 != 0:
        return

    # Fetch last 10 messages
    async with db.execute(
        """
        SELECT role, content FROM messages
        WHERE conversation_id = ?
        ORDER BY created_at DESC
        LIMIT 10
        """,
        (conversation_id,),
    ) as cursor:
        rows = await cursor.fetchall()

    dialogue = "\n".join(f"{r[0]}: {r[1]}" for r in reversed(rows))

    prompt = f"""你是一个用户画像分析助手。请基于以下近期对话，提取用户的兴趣领域（列表）和各领域的知识水平（初学者/中级/高级）。

对话记录：
{dialogue}

请只输出 JSON：{{"interests": ["领域A", "领域B"], "knowledge_levels": {{"领域A": "advanced"}}}}。不要其他内容。"""

    try:
        raw = await chat_completion(
            [{"role": "user", "content": prompt}], stream=False
        )
    except Exception:
        return

    result = _safe_json_parse(raw)
    if result is None:
        return

    interests = result.get("interests", [])
    levels = result.get("knowledge_levels", {})

    await db.execute(
        """
        INSERT INTO user_profiles (id, interests, knowledge_levels, last_updated)
        VALUES (1, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            interests = excluded.interests,
            knowledge_levels = excluded.knowledge_levels,
            last_updated = excluded.last_updated
        """,
        (json.dumps(interests, ensure_ascii=False), json.dumps(levels, ensure_ascii=False), _now()),
    )
    await db.commit()


def _safe_json_parse(text: str) -> Optional[dict]:
    try:
        raw = text.strip()
        if raw.startswith("```"):
            raw = raw.split("```json", 1)[-1].split("```", 1)[0].strip()
        return json.loads(raw)
    except Exception:
        return None
