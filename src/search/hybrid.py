import asyncio
from typing import List, Tuple

import aiosqlite

from src.search import fts, vec


async def hybrid_search(
    db: aiosqlite.Connection,
    query_embedding: List[float],
    query_text: str,
    top_k: int = 10,
) -> List[Tuple[str, str, str, float]]:
    """Run hybrid search and return Top-K chunks with hybrid score.

    Result: List of (chunk_id, version_id, chunk_text, hybrid_score)
    Ordered by hybrid_score descending (higher = better).
    """
    vec_results, fts_results = await asyncio.gather(
        vec.search_similar(db, query_embedding, top_k=15),
        fts.search_text(db, query_text, top_k=15),
    )

    # vec_results: (chunk_id, version_id, chunk_text, distance)
    # fts_results: (chunk_id, chunk_text, bm25_rank)

    # Normalization helpers
    def _normalize_scores_vec(items):
        if not items:
            return {}
        distances = [d for _, _, _, d in items]
        d_min, d_max = min(distances), max(distances)
        rng = d_max - d_min if d_max != d_min else 1.0
        return {
            cid: 1.0 - (d - d_min) / rng for cid, _, _, d in items
        }

    def _normalize_scores_fts(items):
        if not items:
            return {}
        ranks = [r for _, _, r in items]
        r_min, r_max = min(ranks), max(ranks)
        rng = r_max - r_min if r_max != r_min else 1.0
        return {
            cid: 1.0 - (r - r_min) / rng for cid, _, r in items
        }

    vec_norm = _normalize_scores_vec(vec_results)
    fts_norm = _normalize_scores_fts(fts_results)

    # Build merged info
    merged: dict[str, dict] = {}
    for cid, vid, txt, _ in vec_results:
        merged[cid] = {"version_id": vid, "chunk_text": txt}
    for cid, txt, _ in fts_results:
        if cid not in merged:
            # version_id unknown from fts alone; fetch later if needed
            merged[cid] = {"version_id": None, "chunk_text": txt}

    scored = []
    for cid, info in merged.items():
        v_score = vec_norm.get(cid, 0.0)
        f_score = fts_norm.get(cid, 0.0)
        hybrid = 0.6 * v_score + 0.4 * f_score
        scored.append((cid, info["version_id"], info["chunk_text"], hybrid))

    # Resolve missing version_ids from database if any
    missing = [(i, cid) for i, (cid, vid, _, _) in enumerate(scored) if vid is None]
    if missing:
        ids = [cid for _, cid in missing]
        placeholders = ",".join("?" * len(ids))
        async with db.execute(
            f"SELECT id, version_id FROM embedding_chunks WHERE id IN ({placeholders})",
            tuple(ids),
        ) as cursor:
            mapping = {row[0]: row[1] async for row in cursor}
        for idx, cid in missing:
            scored[idx] = (cid, mapping.get(cid), scored[idx][2], scored[idx][3])

    scored.sort(key=lambda x: x[3], reverse=True)
    return scored[:top_k]
