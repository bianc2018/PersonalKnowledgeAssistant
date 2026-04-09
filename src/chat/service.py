import json
import re
import uuid
from datetime import datetime, timezone
from typing import AsyncIterator, List, Optional, Tuple

import aiosqlite

from src.chat.models import CitationOut, ConversationOut, MessageOut
from src.db.connection import get_db
from src.external.llm import chat_completion, get_embeddings
from src.profile.service import update_profile_if_needed as _update_profile_if_needed
from src.search.hybrid import hybrid_search


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def list_conversations(
    db: aiosqlite.Connection, offset: int = 0, limit: int = 20
) -> Tuple[List[ConversationOut], int]:
    async with db.execute("SELECT COUNT(*) FROM conversations") as cursor:
        row = await cursor.fetchone()
        total = row[0] if row else 0

    items: List[ConversationOut] = []
    async with db.execute(
        """
        SELECT
            c.id, c.title, c.created_at, c.updated_at,
            (SELECT COUNT(*) FROM messages WHERE conversation_id = c.id) as msg_count
        FROM conversations c
        ORDER BY c.updated_at DESC
        LIMIT ? OFFSET ?
        """,
        (limit, offset),
    ) as cursor:
        async for row in cursor:
            items.append(
                ConversationOut(
                    id=row[0],
                    title=row[1],
                    message_count=row[4],
                    created_at=datetime.fromisoformat(row[2]),
                    last_message_at=datetime.fromisoformat(row[3]),
                )
            )
    return items, total


async def create_conversation(db: aiosqlite.Connection, title: str = "新会话") -> str:
    conv_id = str(uuid.uuid4())
    now = _now()
    await db.execute(
        "INSERT INTO conversations (id, title, created_at, updated_at) VALUES (?, ?, ?, ?)",
        (conv_id, title, now, now),
    )
    await db.commit()
    return conv_id


async def get_messages(
    db: aiosqlite.Connection, conversation_id: str
) -> List[MessageOut]:
    messages: List[MessageOut] = []
    async with db.execute(
        """
        SELECT id, role, content, created_at FROM messages
        WHERE conversation_id = ? ORDER BY created_at ASC
        """,
        (conversation_id,),
    ) as cursor:
        async for row in cursor:
            msg_id = row[0]
            citations = await _get_message_citations(db, msg_id)
            messages.append(
                MessageOut(
                    id=msg_id,
                    role=row[1],
                    content=row[2],
                    citations=citations,
                    created_at=datetime.fromisoformat(row[3]),
                )
            )
    return messages


async def _get_message_citations(
    db: aiosqlite.Connection, message_id: str
) -> List[CitationOut]:
    citations: List[CitationOut] = []
    async with db.execute(
        """
        SELECT
            mc.citation_index, mc.item_id, ki.title, mc.chunk_text
        FROM message_citations mc
        JOIN knowledge_items ki ON ki.id = mc.item_id
        WHERE mc.message_id = ?
        ORDER BY mc.citation_index
        """,
        (message_id,),
    ) as cursor:
        async for row in cursor:
            citations.append(
                CitationOut(
                    citation_index=row[0],
                    item_id=row[1],
                    item_title=row[2],
                    chunk_text=row[3],
                )
            )
    return citations


async def _load_user_profile(db: aiosqlite.Connection) -> dict:
    async with db.execute(
        "SELECT interests, knowledge_levels FROM user_profiles WHERE id = 1"
    ) as cursor:
        row = await cursor.fetchone()
    if row:
        return {
            "interests": json.loads(row[0]) if row[0] else [],
            "levels": json.loads(row[1]) if row[1] else {},
        }
    return {"interests": [], "levels": {}}


def _chunk_id_to_citation_map(
    chunks: List[Tuple[str, str, str, float]]
) -> Tuple[str, dict]:
    """Build RAG prompt snippet and citation mapping.

    chunks: (chunk_id, version_id, chunk_text, score)
    Returns: (prompt_snippet, {chunk_id: index})
    """
    lines = []
    mapping = {}
    for idx, (cid, _, text, _) in enumerate(chunks, start=1):
        lines.append(f"[{idx}] {text}")
        mapping[cid] = idx
    return "\n".join(lines), mapping


async def _resolve_chunk_sources(
    db: aiosqlite.Connection, chunk_ids: List[str]
) -> dict[str, Tuple[str, str]]:
    """Map chunk_id -> (item_id, item_title)."""
    if not chunk_ids:
        return {}
    placeholders = ",".join("?" * len(chunk_ids))
    async with db.execute(
        f"""
        SELECT ec.id, kv.item_id, ki.title
        FROM embedding_chunks ec
        JOIN knowledge_versions kv ON kv.id = ec.version_id
        JOIN knowledge_items ki ON ki.id = kv.item_id
        WHERE ec.id IN ({placeholders})
        """,
        tuple(chunk_ids),
    ) as cursor:
        rows = await cursor.fetchall()
    return {row[0]: (row[1], row[2]) for row in rows}


async def send_message(
    db: aiosqlite.Connection,
    conversation_id: str,
    content: str,
) -> MessageOut:
    now = _now()
    # Insert user message
    await db.execute(
        "INSERT INTO messages (id, conversation_id, role, content, created_at) VALUES (?, ?, ?, ?, ?)",
        (str(uuid.uuid4()), conversation_id, "user", content, now),
    )
    await db.execute(
        "UPDATE conversations SET updated_at = ? WHERE id = ?",
        (now, conversation_id),
    )

    # Build profile and retrieve top chunks
    profile = await _load_user_profile(db)
    try:
        query_embedding = (await get_embeddings([content]))[0]
    except Exception:
        query_embedding = []

    if query_embedding:
        top_chunks = await hybrid_search(db, query_embedding, content, top_k=10)
    else:
        top_chunks = []

    rag_snippet, cid_map = _chunk_id_to_citation_map(top_chunks)

    system_prompt = f"""你是一位知识管理助手。请基于以下用户画像和知识库内容回答用户问题。
如果知识库中没有相关内容，请明确告知用户"当前知识库中未找到相关信息"，不要编造答案。

用户画像：
- 兴趣领域：{', '.join(profile.get('interests', []))}
- 知识水平：{json.dumps(profile.get('levels', {}), ensure_ascii=False)}

以下是从知识库中检索到的相关片段（按相关度排序，编号 [1]、[2] ...）：
{rag_snippet}

请尽量在回答中使用 [1]、[2] 等标记引用你所使用的知识片段。"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": content},
    ]

    answer = await chat_completion(messages, stream=False)

    # Parse citations
    used_indices = sorted(
        set(int(m.group(1)) for m in re.finditer(r"\[(\d+)\]", answer))
    )

    msg_id = str(uuid.uuid4())
    await db.execute(
        "INSERT INTO messages (id, conversation_id, role, content, created_at) VALUES (?, ?, ?, ?, ?)",
        (msg_id, conversation_id, "assistant", answer, now),
    )

    if used_indices and top_chunks:
        cid_list = [cid for cid, _, _, _ in top_chunks]
        sources = await _resolve_chunk_sources(db, cid_list)
        for idx in used_indices:
            if idx < 1 or idx > len(cid_list):
                continue
            cid = cid_list[idx - 1]
            item_id, title = sources.get(cid, (None, None))
            if item_id is None:
                continue
            chunk_text = next((t for c, _, t, _ in top_chunks if c == cid), "")
            await db.execute(
                "INSERT INTO message_citations (id, message_id, item_id, version_id, chunk_text, citation_index) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    str(uuid.uuid4()),
                    msg_id,
                    item_id,
                    None,
                    chunk_text,
                    idx,
                ),
            )

    await db.commit()

    await _update_profile_if_needed(db, conversation_id)

    citations = await _get_message_citations(db, msg_id)
    return MessageOut(
        id=msg_id,
        role="assistant",
        content=answer,
        citations=citations,
        created_at=datetime.fromisoformat(now),
    )


async def stream_message(
    db: aiosqlite.Connection,
    conversation_id: str,
    content: str,
) -> AsyncIterator[str]:
    now = _now()
    # Insert user message
    await db.execute(
        "INSERT INTO messages (id, conversation_id, role, content, created_at) VALUES (?, ?, ?, ?, ?)",
        (str(uuid.uuid4()), conversation_id, "user", content, now),
    )
    await db.execute(
        "UPDATE conversations SET updated_at = ? WHERE id = ?",
        (now, conversation_id),
    )

    profile = await _load_user_profile(db)
    try:
        query_embedding = (await get_embeddings([content]))[0]
    except Exception:
        query_embedding = []

    if query_embedding:
        top_chunks = await hybrid_search(db, query_embedding, content, top_k=10)
    else:
        top_chunks = []

    rag_snippet, _ = _chunk_id_to_citation_map(top_chunks)

    system_prompt = f"""你是一位知识管理助手。请基于以下用户画像和知识库内容回答用户问题。
如果知识库中没有相关内容，请明确告知用户"当前知识库中未找到相关信息"，不要编造答案。

用户画像：
- 兴趣领域：{', '.join(profile.get('interests', []))}
- 知识水平：{json.dumps(profile.get('levels', {}), ensure_ascii=False)}

以下是从知识库中检索到的相关片段（按相关度排序，编号 [1]、[2] ...）：
{rag_snippet}

请尽量在回答中使用 [1]、[2] 等标记引用你所使用的知识片段。"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": content},
    ]

    stream = await chat_completion(messages, stream=True)
    full_text = ""
    async for delta in stream:
        full_text += delta
        payload = json.dumps({"delta": delta}, ensure_ascii=False)
        yield f"event: delta\ndata: {payload}\n\n"

    # After stream ends, parse citations
    used_indices = sorted(
        set(int(m.group(1)) for m in re.finditer(r"\[(\d+)\]", full_text))
    )

    msg_id = str(uuid.uuid4())
    await db.execute(
        "INSERT INTO messages (id, conversation_id, role, content, created_at) VALUES (?, ?, ?, ?, ?)",
        (msg_id, conversation_id, "assistant", full_text, now),
    )

    citations: List[CitationOut] = []
    if used_indices and top_chunks:
        cid_list = [cid for cid, _, _, _ in top_chunks]
        sources = await _resolve_chunk_sources(db, cid_list)
        for idx in used_indices:
            if idx < 1 or idx > len(cid_list):
                continue
            cid = cid_list[idx - 1]
            item_id, title = sources.get(cid, (None, None))
            if item_id is None:
                continue
            chunk_text = next((t for c, _, t, _ in top_chunks if c == cid), "")
            await db.execute(
                "INSERT INTO message_citations (id, message_id, item_id, version_id, chunk_text, citation_index) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    str(uuid.uuid4()),
                    msg_id,
                    item_id,
                    None,
                    chunk_text,
                    idx,
                ),
            )
            citations.append(
                CitationOut(
                    citation_index=idx,
                    item_id=item_id,
                    item_title=title,
                    chunk_text=chunk_text,
                )
            )

    await db.commit()

    await _update_profile_if_needed(db, conversation_id)

    if citations:
        import json as _json
        payload = _json.dumps([c.model_dump() for c in citations], ensure_ascii=False)
        yield f'event: citation\ndata: {{"citations": {payload}}}\n\n'

    yield 'event: done\ndata: {}\n\n'
