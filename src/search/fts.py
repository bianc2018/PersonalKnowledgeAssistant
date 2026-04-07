from typing import List, Tuple

import aiosqlite


async def insert_fts_chunks(
    db: aiosqlite.Connection, chunk_ids: List[str], chunk_texts: List[str]
) -> None:
    """Insert chunks into FTS5 index.

    Since embedding_chunks_fts uses content='embedding_chunks' as external content,
    we only need to rebuild the index when rows change.
    For simplicity, we rely on the external content and rebuild/optimize when needed.
    However, because aiosqlite may not support external content auto-sync perfectly in all
    sqlite builds, we manually insert into the FTS shadow table for safety.
    """
    for chunk_id, text in zip(chunk_ids, chunk_texts):
        # Obtain rowid from embedding_chunks
        async with db.execute(
            "SELECT rowid FROM embedding_chunks WHERE id = ?", (chunk_id,)
        ) as cursor:
            row = await cursor.fetchone()
        if not row:
            continue
        rowid = row[0]
        await db.execute(
            "INSERT OR REPLACE INTO embedding_chunks_fts (rowid, chunk_text) VALUES (?, ?)",
            (rowid, text),
        )


async def delete_fts_chunks(
    db: aiosqlite.Connection, chunk_ids: List[str]
) -> None:
    for chunk_id in chunk_ids:
        async with db.execute(
            "SELECT rowid FROM embedding_chunks WHERE id = ?", (chunk_id,)
        ) as cursor:
            row = await cursor.fetchone()
        if row:
            await db.execute(
                "DELETE FROM embedding_chunks_fts WHERE rowid = ?", (row[0],)
            )


async def search_text(
    db: aiosqlite.Connection, query: str, top_k: int = 15
) -> List[Tuple[str, str, float]]:
    """Return top-k FTS matches: (chunk_id, chunk_text, bm25_rank).

    BM25 score from FTS5 is usually lower = more relevant (when using bm25).
    We return the raw bm25 value for hybrid fusion.
    """
    # Escape query quotes
    safe_query = query.replace('"', '""').strip()
    if not safe_query:
        return []

    sql = """
        SELECT
            ec.id,
            ec.chunk_text,
            bm25(embedding_chunks_fts) as rank
        FROM embedding_chunks_fts
        JOIN embedding_chunks ec ON ec.rowid = embedding_chunks_fts.rowid
        WHERE embedding_chunks_fts MATCH ?
        ORDER BY rank
        LIMIT ?
    """
    results: List[Tuple[str, str, float]] = []
    async with db.execute(sql, (safe_query, top_k)) as cursor:
        async for row in cursor:
            results.append((row[0], row[1], float(row[2])))
    return results
