import json
from typing import List, Tuple

import aiosqlite


async def insert_embedding_chunks(
    db: aiosqlite.Connection,
    version_id: str,
    chunk_texts: List[str],
    embeddings: List[List[float]],
) -> List[str]:
    """Insert chunks into embedding_chunks and vec_chunks."""
    chunk_ids: List[str] = []
    import uuid

    for idx, (text, embedding) in enumerate(zip(chunk_texts, embeddings)):
        chunk_id = str(uuid.uuid4())
        chunk_ids.append(chunk_id)

        # Insert into normal table for metadata / FTS
        await db.execute(
            "INSERT INTO embedding_chunks (id, version_id, chunk_text, chunk_index) VALUES (?, ?, ?, ?)",
            (chunk_id, version_id, text, idx),
        )

        # Insert into sqlite-vec virtual table
        # sqlite-vec supports JSON array syntax for vectors
        emb_json = json.dumps(embedding)
        await db.execute(
            "INSERT INTO vec_chunks (chunk_id, embedding) VALUES (?, ?)",
            (chunk_id, emb_json),
        )

    return chunk_ids


async def search_similar(
    db: aiosqlite.Connection,
    embedding: List[float],
    top_k: int = 15,
) -> List[Tuple[str, str, str, float]]:
    """Return top-k similar chunks: (chunk_id, version_id, chunk_text, distance).

    Distance from vec_distance_l2 is lower = more similar.
    We normalize later in hybrid layer if needed.
    """
    emb_json = json.dumps(embedding)
    query = """
        SELECT
            vc.chunk_id,
            ec.version_id,
            ec.chunk_text,
            vec_distance_l2(vc.embedding, ?) as distance
        FROM vec_chunks vc
        JOIN embedding_chunks ec ON ec.id = vc.chunk_id
        ORDER BY distance
        LIMIT ?
    """
    results: List[Tuple[str, str, str, float]] = []
    async with db.execute(query, (emb_json, top_k)) as cursor:
        async for row in cursor:
            results.append((row[0], row[1], row[2], float(row[3])))
    return results


async def delete_embedding_chunks_for_version(
    db: aiosqlite.Connection, version_id: str
) -> None:
    async with db.execute(
        "SELECT id FROM embedding_chunks WHERE version_id = ?", (version_id,)
    ) as cursor:
        rows = await cursor.fetchall()
    for (chunk_id,) in rows:
        await db.execute("DELETE FROM vec_chunks WHERE chunk_id = ?", (chunk_id,))
    await db.execute("DELETE FROM embedding_chunks WHERE version_id = ?", (version_id,))
