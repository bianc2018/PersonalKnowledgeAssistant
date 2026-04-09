import difflib
import hashlib
import random
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

import aiosqlite

from src.auth.crypto import encrypt_bytes
from src.external.llm import get_embeddings
from src.knowledge.archive import archive_old_attachments
from src.knowledge.confidence import evaluate_confidence
from src.knowledge.extractor import extract_text_from_bytes, extract_text_from_url
from src.knowledge.models import (
    AttachmentOut,
    ConfidenceOut,
    KnowledgeCreate,
    KnowledgeDetail,
    KnowledgeListItem,
    KnowledgeUpdate,
    KnowledgeVersionItem,
    TagOut,
)
from src.search import fts, vec


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _compute_delta(old_text: str, new_text: str) -> float:
    if not old_text and not new_text:
        return 0.0
    if not old_text:
        return 1.0
    diff = difflib.SequenceMatcher(None, old_text, new_text).ratio()
    return round(1.0 - diff, 4)


def _sanitize_filename(filename: str) -> str:
    """Remove path traversal characters and return basename only."""
    from urllib.parse import unquote
    name = Path(unquote(filename)).name
    # Strip common risky characters
    name = name.replace("..", "").replace("/", "").replace("\\", "").strip()
    return name or "upload"


def _storage_path(item_id: str, filename: str) -> str:
    prefix = item_id.replace("-", "")
    dir_path = Path("files") / prefix[:2] / prefix[2:4] / item_id
    dir_path.mkdir(parents=True, exist_ok=True)
    safe_name = _sanitize_filename(filename)
    return str(dir_path / f"{safe_name}.enc")


async def _ensure_tags(db: aiosqlite.Connection, tag_names: List[str]) -> List[TagOut]:
    tags: List[TagOut] = []
    for name in tag_names:
        name = name.strip()
        if not name:
            continue
        await db.execute(
            "INSERT OR IGNORE INTO tags (id, name, created_at) VALUES (?, ?, ?)",
            (str(uuid.uuid4()), name, _now()),
        )
        await db.commit()
        async with db.execute(
            "SELECT id, name, color FROM tags WHERE name = ?", (name,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                tags.append(TagOut(id=row[0], name=row[1], color=row[2]))
    return tags


async def create_knowledge_text(
    db: aiosqlite.Connection,
    data: KnowledgeCreate,
) -> str:
    item_id = str(uuid.uuid4())
    version_id = str(uuid.uuid4())
    now = _now()

    tags = await _ensure_tags(db, data.tags)

    await db.execute(
        """
        INSERT INTO knowledge_items (id, title, source_type, current_version_id, is_deleted, created_at, updated_at)
        VALUES (?, ?, ?, ?, 0, ?, ?)
        """,
        (item_id, data.title or data.content[:50], data.source_type, version_id, now, now),
    )
    await db.execute(
        """
        INSERT INTO knowledge_versions (id, item_id, content_text, content_delta, created_by, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (version_id, item_id, data.content, 0.0, "user_edit", now),
    )
    for tag in tags:
        await db.execute(
            "INSERT INTO tag_links (item_id, tag_id) VALUES (?, ?)",
            (item_id, tag.id),
        )
    await _generate_chunks(db, version_id, data.content)
    await db.commit()
    return item_id


async def create_knowledge_url(
    db: aiosqlite.Connection,
    url: str,
    title: str,
    tags: List[str],
) -> str:
    text, status, error = await extract_text_from_url(url)
    item_id = str(uuid.uuid4())
    version_id = str(uuid.uuid4())
    now = _now()
    final_title = title or url

    tag_objs = await _ensure_tags(db, tags)

    await db.execute(
        """
        INSERT INTO knowledge_items (id, title, source_type, current_version_id, is_deleted, created_at, updated_at)
        VALUES (?, ?, ?, ?, 0, ?, ?)
        """,
        (item_id, final_title, "url", version_id, now, now),
    )
    await db.execute(
        """
        INSERT INTO knowledge_versions (id, item_id, content_text, content_delta, created_by, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (version_id, item_id, text, 0.0, "auto_extraction", now),
    )
    # Attachment for URL is not stored as encrypted file; content is in version.
    # Spec says URL content is extracted as text.
    for tag in tag_objs:
        await db.execute(
            "INSERT INTO tag_links (item_id, tag_id) VALUES (?, ?)",
            (item_id, tag.id),
        )
    await _generate_chunks(db, version_id, text)
    await db.commit()
    return item_id


async def create_knowledge_upload(
    db: aiosqlite.Connection,
    filename: str,
    mime_type: str,
    file_bytes: bytes,
    title: str,
    tags: List[str],
    master_key: bytes,
) -> str:
    item_id = str(uuid.uuid4())
    version_id = str(uuid.uuid4())
    now = _now()

    text, extraction_status, extraction_error = await extract_text_from_bytes(
        file_bytes, filename, mime_type
    )
    if not text and extraction_status != "success":
        text = f"{filename} {Path(filename).suffix}"

    tag_objs = await _ensure_tags(db, tags)

    storage_path = _storage_path(item_id, filename)
    encrypted = encrypt_bytes(file_bytes, master_key)
    Path(storage_path).write_bytes(encrypted)

    await db.execute(
        """
        INSERT INTO knowledge_items (id, title, source_type, current_version_id, is_deleted, created_at, updated_at)
        VALUES (?, ?, ?, ?, 0, ?, ?)
        """,
        (item_id, title or filename, "file", version_id, now, now),
    )
    await db.execute(
        """
        INSERT INTO knowledge_versions (id, item_id, content_text, content_delta, created_by, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (version_id, item_id, text, 0.0, "auto_extraction", now),
    )
    await db.execute(
        """
        INSERT INTO attachments (
            id, item_id, filename, mime_type, storage_path, size_bytes,
            extraction_status, extraction_error, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            str(uuid.uuid4()),
            item_id,
            filename,
            mime_type,
            storage_path,
            len(file_bytes),
            extraction_status,
            extraction_error,
            now,
        ),
    )
    for tag in tag_objs:
        await db.execute(
            "INSERT INTO tag_links (item_id, tag_id) VALUES (?, ?)",
            (item_id, tag.id),
        )
    await _generate_chunks(db, version_id, text)
    await db.commit()
    await archive_old_attachments(db)
    return item_id


async def get_knowledge_list(
    db: aiosqlite.Connection,
    q: str = "",
    tag_names: List[str] = None,
    include_deleted: bool = False,
    offset: int = 0,
    limit: int = 20,
) -> tuple[List[KnowledgeListItem], int]:
    tag_names = tag_names or []
    where_parts = []
    params: list = []

    if q:
        where_parts.append(
            "(ki.title LIKE ? OR kv.content_text LIKE ?)"
        )
        params.extend([f"%{q}%", f"%{q}%"])

    if not include_deleted:
        where_parts.append("ki.is_deleted = 0")

    if tag_names:
        where_parts.append(
            f"""
            ki.id IN (
                SELECT tl.item_id FROM tag_links tl
                JOIN tags t ON t.id = tl.tag_id
                WHERE t.name IN ({','.join('?' * len(tag_names))})
            )
            """
        )
        params.extend(tag_names)

    where_sql = "WHERE " + " AND ".join(where_parts) if where_parts else ""

    count_sql = f"""
        SELECT COUNT(DISTINCT ki.id)
        FROM knowledge_items ki
        LEFT JOIN knowledge_versions kv ON kv.id = ki.current_version_id
        {where_sql}
    """
    async with db.execute(count_sql, tuple(params)) as cursor:
        row = await cursor.fetchone()
        total = row[0] if row else 0

    query_sql = f"""
        SELECT
            ki.id, ki.title, ki.source_type, ki.is_deleted,
            ki.created_at, ki.updated_at,
            (SELECT COUNT(*) FROM knowledge_versions WHERE item_id = ki.id) as version_count
        FROM knowledge_items ki
        LEFT JOIN knowledge_versions kv ON kv.id = ki.current_version_id
        {where_sql}
        ORDER BY ki.updated_at DESC
        LIMIT ? OFFSET ?
    """
    items: List[KnowledgeListItem] = []
    async with db.execute(query_sql, tuple(params + [limit, offset])) as cursor:
        async for row in cursor:
            item_id = row[0]
            tags = await _get_item_tags(db, item_id)
            confidence = await _get_current_confidence(db, item_id)
            items.append(
                KnowledgeListItem(
                    id=item_id,
                    title=row[1],
                    source_type=row[2],
                    tags=tags,
                    confidence=confidence,
                    version_count=row[6],
                    is_deleted=bool(row[3]),
                    created_at=datetime.fromisoformat(row[4]),
                    updated_at=datetime.fromisoformat(row[5]),
                )
            )
    return items, total


async def get_knowledge_detail(db: aiosqlite.Connection, item_id: str) -> Optional[KnowledgeDetail]:
    async with db.execute(
        """
        SELECT id, title, source_type, current_version_id, is_deleted, created_at, updated_at
        FROM knowledge_items WHERE id = ?
        """,
        (item_id,),
    ) as cursor:
        row = await cursor.fetchone()
    if not row:
        return None

    current_version_id = row[3]
    current_version = None
    if current_version_id:
        async with db.execute(
            "SELECT id, content_text, created_at FROM knowledge_versions WHERE id = ?",
            (current_version_id,),
        ) as cursor:
            vrow = await cursor.fetchone()
            if vrow:
                current_version = {
                    "id": vrow[0],
                    "content_text": vrow[1],
                    "created_at": datetime.fromisoformat(vrow[2]),
                }

    versions: List[KnowledgeVersionItem] = []
    async with db.execute(
        "SELECT id, created_at, created_by FROM knowledge_versions WHERE item_id = ? ORDER BY created_at DESC",
        (item_id,),
    ) as cursor:
        async for vrow in cursor:
            versions.append(
                KnowledgeVersionItem(
                    id=vrow[0],
                    created_at=datetime.fromisoformat(vrow[1]),
                    created_by=vrow[2],
                )
            )

    attachments = await _get_item_attachments(db, item_id)
    tags = await _get_item_tags(db, item_id)
    confidence = await _get_current_confidence(db, item_id)

    return KnowledgeDetail(
        id=row[0],
        title=row[1],
        source_type=row[2],
        current_version=current_version,
        versions=versions,
        attachments=attachments,
        tags=tags,
        confidence=confidence,
        is_deleted=bool(row[4]),
        created_at=datetime.fromisoformat(row[5]),
        updated_at=datetime.fromisoformat(row[6]),
    )


async def update_knowledge(
    db: aiosqlite.Connection,
    item_id: str,
    data: KnowledgeUpdate,
) -> bool:
    async with db.execute(
        "SELECT current_version_id FROM knowledge_items WHERE id = ?", (item_id,)
    ) as cursor:
        row = await cursor.fetchone()
    if not row:
        return False
    current_version_id = row[0]

    now = _now()
    updates = []
    params: list = []

    if data.title is not None:
        updates.append("title = ?")
        params.append(data.title)

    if data.content is not None:
        async with db.execute(
            "SELECT content_text FROM knowledge_versions WHERE id = ?", (current_version_id,)
        ) as cursor:
            old_row = await cursor.fetchone()
        old_text = old_row[0] if old_row else ""
        delta = _compute_delta(old_text, data.content)
        new_version_id = str(uuid.uuid4())
        await db.execute(
            """
            INSERT INTO knowledge_versions (id, item_id, content_text, content_delta, created_by, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (new_version_id, item_id, data.content, delta, "user_edit", now),
        )
        await _generate_chunks(db, new_version_id, data.content)
        if delta > 0.2:
            await evaluate_confidence(db, new_version_id, data.content)
        updates.append("current_version_id = ?")
        params.append(new_version_id)

    if data.tags is not None:
        await db.execute("DELETE FROM tag_links WHERE item_id = ?", (item_id,))
        tag_objs = await _ensure_tags(db, data.tags)
        for tag in tag_objs:
            await db.execute(
                "INSERT INTO tag_links (item_id, tag_id) VALUES (?, ?)",
                (item_id, tag.id),
            )

    if updates:
        updates.append("updated_at = ?")
        params.append(now)
        sql = f"UPDATE knowledge_items SET {', '.join(updates)} WHERE id = ?"
        params.append(item_id)
        await db.execute(sql, tuple(params))

    await db.commit()
    return True


async def delete_knowledge(db: aiosqlite.Connection, item_id: str) -> bool:
    async with db.execute(
        "SELECT id FROM knowledge_items WHERE id = ?", (item_id,)
    ) as cursor:
        row = await cursor.fetchone()
    if not row:
        return False
    await db.execute(
        "UPDATE knowledge_items SET is_deleted = 1, updated_at = ? WHERE id = ?",
        (_now(), item_id),
    )
    await db.commit()
    return True


async def trigger_manual_evaluation(db: aiosqlite.Connection, item_id: str) -> bool:
    async with db.execute(
        "SELECT current_version_id FROM knowledge_items WHERE id = ?", (item_id,)
    ) as cursor:
        row = await cursor.fetchone()
    if not row or not row[0]:
        return False
    version_id = row[0]
    async with db.execute(
        "SELECT content_text FROM knowledge_versions WHERE id = ?", (version_id,)
    ) as cursor:
        vrow = await cursor.fetchone()
    if not vrow:
        return False
    await evaluate_confidence(db, version_id, vrow[0])
    return True


async def list_tags(db: aiosqlite.Connection) -> List[TagOut]:
    tags: List[TagOut] = []
    async with db.execute(
        """
        SELECT t.id, t.name, t.color, COUNT(tl.item_id) as item_count
        FROM tags t
        LEFT JOIN tag_links tl ON tl.tag_id = t.id
        GROUP BY t.id
        ORDER BY t.name
        """
    ) as cursor:
        async for row in cursor:
            tags.append(TagOut(id=row[0], name=row[1], color=row[2]))
    return tags


async def _get_item_tags(db: aiosqlite.Connection, item_id: str) -> List[TagOut]:
    tags: List[TagOut] = []
    async with db.execute(
        """
        SELECT t.id, t.name, t.color
        FROM tags t
        JOIN tag_links tl ON tl.tag_id = t.id
        WHERE tl.item_id = ?
        """,
        (item_id,),
    ) as cursor:
        async for row in cursor:
            tags.append(TagOut(id=row[0], name=row[1], color=row[2]))
    return tags


async def _get_item_attachments(db: aiosqlite.Connection, item_id: str) -> List[AttachmentOut]:
    atts: List[AttachmentOut] = []
    async with db.execute(
        """
        SELECT id, filename, mime_type, size_bytes, extraction_status, extraction_error
        FROM attachments WHERE item_id = ?
        """,
        (item_id,),
    ) as cursor:
        async for row in cursor:
            atts.append(
                AttachmentOut(
                    id=row[0],
                    filename=row[1],
                    mime_type=row[2],
                    size_bytes=row[3],
                    extraction_status=row[4],
                    extraction_error=row[5],
                )
            )
    return atts


async def _get_current_confidence(
    db: aiosqlite.Connection, item_id: str
) -> Optional[ConfidenceOut]:
    async with db.execute(
        """
        SELECT ce.score_level, ce.score_value, ce.method, ce.rationale, ce.evaluated_at
        FROM confidence_evaluations ce
        JOIN knowledge_items ki ON ki.current_version_id = ce.version_id
        WHERE ki.id = ?
        """,
        (item_id,),
    ) as cursor:
        row = await cursor.fetchone()
    if not row:
        return None
    return ConfidenceOut(
        score_level=row[0],
        score_value=row[1],
        method=row[2],
        rationale=row[3],
        evaluated_at=datetime.fromisoformat(row[4]),
    )



def _chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
    """Simple sliding-window text chunking."""
    chunks: List[str] = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunks.append(text[start:end])
        if end == len(text):
            break
        start += chunk_size - overlap
    return chunks


def _fallback_embedding(text: str, dim: int = 1536) -> List[float]:
    """Deterministic pseudo-random vector when external embedding is unavailable."""
    seed = int(hashlib.sha256(text.encode("utf-8")).hexdigest(), 16) % (2 ** 32)
    rng = random.Random(seed)
    return [rng.uniform(-1.0, 1.0) for _ in range(dim)]


async def _generate_chunks(db: aiosqlite.Connection, version_id: str, text: str) -> None:
    """Generate embedding chunks and insert into vec + fts."""
    chunks = _chunk_text(text)
    if not chunks:
        return
    try:
        embeddings = await get_embeddings(chunks)
    except Exception:
        embeddings = [_fallback_embedding(c) for c in chunks]
    chunk_ids = await vec.insert_embedding_chunks(db, version_id, chunks, embeddings)
    await fts.insert_fts_chunks(db, chunk_ids, chunks)
