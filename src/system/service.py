import gzip
import io
import json
import os
import shutil
import uuid
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import aiosqlite

from src.auth.crypto import (
    decrypt_bytes,
    derive_master_key,
    encrypt_bytes,
    verify_password,
)
from src.config import get_settings


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def load_config(db: aiosqlite.Connection) -> dict:
    async with db.execute(
        "SELECT llm_config, embedding_config, search_config, privacy_settings, retry_settings, storage_settings, log_settings FROM system_config WHERE id = 1"
    ) as cursor:
        row = await cursor.fetchone()
    if not row:
        return {}
    return {
        "llm_config": json.loads(row[0]) if row[0] else {},
        "embedding_config": json.loads(row[1]) if row[1] else {},
        "search_config": json.loads(row[2]) if row[2] else None,
        "privacy_settings": json.loads(row[3]) if row[3] else {},
        "retry_settings": json.loads(row[4]) if row[4] else {},
        "storage_settings": json.loads(row[5]) if row[5] else {},
        "log_settings": json.loads(row[6]) if row[6] else {},
    }


async def update_config(db: aiosqlite.Connection, updates: dict) -> dict:
    current = await load_config(db)
    for key in updates:
        if key in current and isinstance(updates[key], dict):
            current[key].update(updates[key])
        else:
            current[key] = updates[key]

    await db.execute(
        """
        UPDATE system_config SET
            llm_config = ?,
            embedding_config = ?,
            search_config = ?,
            privacy_settings = ?,
            retry_settings = ?,
            storage_settings = ?,
            log_settings = ?,
            updated_at = ?
        WHERE id = 1
        """,
        (
            json.dumps(current.get("llm_config", {}), ensure_ascii=False),
            json.dumps(current.get("embedding_config", {}), ensure_ascii=False),
            json.dumps(current.get("search_config"), ensure_ascii=False) if current.get("search_config") is not None else None,
            json.dumps(current.get("privacy_settings", {}), ensure_ascii=False),
            json.dumps(current.get("retry_settings", {}), ensure_ascii=False),
            json.dumps(current.get("storage_settings", {}), ensure_ascii=False),
            json.dumps(current.get("log_settings", {}), ensure_ascii=False),
            _now(),
        ),
    )
    await db.commit()
    return current


async def export_backup(db: aiosqlite.Connection, password: str) -> bytes:
    async with db.execute(
        "SELECT password_hash, salt FROM system_config WHERE id = 1"
    ) as cursor:
        row = await cursor.fetchone()
    if not row or not verify_password(password, row[0]):
        raise ValueError("Incorrect password")
    salt = row[1]
    master_key = derive_master_key(password, salt)

    # Build metadata
    async with db.execute(
        "SELECT id, title, source_type, current_version_id, is_deleted, created_at, updated_at FROM knowledge_items"
    ) as cursor:
        items = []
        async for r in cursor:
            items.append(
                {
                    "id": r[0],
                    "title": r[1],
                    "source_type": r[2],
                    "current_version_id": r[3],
                    "is_deleted": bool(r[4]),
                    "created_at": r[5],
                    "updated_at": r[6],
                }
            )

    async with db.execute(
        "SELECT id, item_id, content_text, content_delta, created_by, created_at FROM knowledge_versions"
    ) as cursor:
        versions = []
        async for r in cursor:
            versions.append(
                {
                    "id": r[0],
                    "item_id": r[1],
                    "content_text": r[2],
                    "content_delta": r[3],
                    "created_by": r[4],
                    "created_at": r[5],
                }
            )

    async with db.execute(
        "SELECT id, item_id, filename, mime_type, storage_path, size_bytes, extraction_status, extraction_error, created_at FROM attachments"
    ) as cursor:
        attachments = []
        async for r in cursor:
            attachments.append(
                {
                    "id": r[0],
                    "item_id": r[1],
                    "filename": r[2],
                    "mime_type": r[3],
                    "storage_path": r[4],
                    "size_bytes": r[5],
                    "extraction_status": r[6],
                    "extraction_error": r[7],
                    "created_at": r[8],
                }
            )

    async with db.execute("SELECT id, name, color, created_at FROM tags") as cursor:
        tags = [{"id": r[0], "name": r[1], "color": r[2], "created_at": r[3]} async for r in cursor]

    async with db.execute("SELECT item_id, tag_id FROM tag_links") as cursor:
        tag_links = [{"item_id": r[0], "tag_id": r[1]} async for r in cursor]

    async with db.execute("SELECT id, version_id, score_level, score_value, method, rationale, evaluated_at FROM confidence_evaluations") as cursor:
        confidences = []
        async for r in cursor:
            confidences.append(
                {
                    "id": r[0],
                    "version_id": r[1],
                    "score_level": r[2],
                    "score_value": r[3],
                    "method": r[4],
                    "rationale": r[5],
                    "evaluated_at": r[6],
                }
            )

    async with db.execute("SELECT embedding_config FROM system_config WHERE id = 1") as cursor:
        emb_cfg_raw = await cursor.fetchone()
    embedding_model = json.loads(emb_cfg_raw[0]).get("model", "") if emb_cfg_raw and emb_cfg_raw[0] else ""

    metadata = {
        "version": "1.0",
        "export_at": _now(),
        "embedding_model": embedding_model,
        "items": items,
        "versions": versions,
        "attachments": attachments,
        "tags": tags,
        "tag_links": tag_links,
        "confidence_evaluations": confidences,
    }

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("metadata.json", json.dumps(metadata, ensure_ascii=False, indent=2))
        for att in attachments:
            path = Path(att["storage_path"])
            if path.exists():
                arcname = path.as_posix()
                zf.write(path, arcname)

    encrypted = encrypt_bytes(zip_buffer.getvalue(), master_key)
    return encrypted


async def import_backup(
    db: aiosqlite.Connection, file_bytes: bytes, password: str
) -> dict:
    async with db.execute(
        "SELECT password_hash, salt FROM system_config WHERE id = 1"
    ) as cursor:
        row = await cursor.fetchone()
    if not row or not verify_password(password, row[0]):
        raise ValueError("Incorrect password")
    salt = row[1]
    master_key = derive_master_key(password, salt)

    try:
        zip_bytes = decrypt_bytes(file_bytes, master_key)
    except Exception as e:
        raise ValueError(f"Decryption failed: {e}")

    zip_buffer = io.BytesIO(zip_bytes)
    try:
        with zipfile.ZipFile(zip_buffer, "r") as zf:
            metadata_bytes = zf.read("metadata.json")
    except Exception as e:
        raise ValueError(f"Invalid backup file: {e}")

    metadata = json.loads(metadata_bytes)
    if metadata.get("version") != "1.0":
        raise ValueError("Unsupported backup version")

    # Get current embedding model
    async with db.execute("SELECT embedding_config FROM system_config WHERE id = 1") as cursor:
        emb_raw = await cursor.fetchone()
    current_emb_model = json.loads(emb_raw[0]).get("model", "") if emb_raw and emb_raw[0] else ""
    need_recompute = current_emb_model != metadata.get("embedding_model", "")

    skipped_files = []
    imported_items = 0

    # Simple strategy: insert items and versions, skip duplicates by id
    for item in metadata.get("items", []):
        try:
            await db.execute(
                """
                INSERT INTO knowledge_items (id, title, source_type, current_version_id, is_deleted, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    title=excluded.title,
                    current_version_id=excluded.current_version_id,
                    is_deleted=excluded.is_deleted,
                    updated_at=excluded.updated_at
                """,
                (
                    item["id"],
                    item["title"],
                    item["source_type"],
                    item.get("current_version_id"),
                    int(item.get("is_deleted", False)),
                    item["created_at"],
                    item["updated_at"],
                ),
            )
        except Exception:
            pass

    for ver in metadata.get("versions", []):
        try:
            await db.execute(
                """
                INSERT INTO knowledge_versions (id, item_id, content_text, content_delta, created_by, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    content_text=excluded.content_text,
                    content_delta=excluded.content_delta,
                    created_by=excluded.created_by
                """,
                (
                    ver["id"],
                    ver["item_id"],
                    ver["content_text"],
                    ver["content_delta"],
                    ver["created_by"],
                    ver["created_at"],
                ),
            )
        except Exception:
            pass

    for tag in metadata.get("tags", []):
        try:
            await db.execute(
                "INSERT INTO tags (id, name, color, created_at) VALUES (?, ?, ?, ?) ON CONFLICT(id) DO UPDATE SET name=excluded.name, color=excluded.color",
                (tag["id"], tag["name"], tag.get("color"), tag["created_at"]),
            )
        except Exception:
            pass

    for tl in metadata.get("tag_links", []):
        try:
            await db.execute(
                "INSERT INTO tag_links (item_id, tag_id) VALUES (?, ?) ON CONFLICT DO NOTHING",
                (tl["item_id"], tl["tag_id"]),
            )
        except Exception:
            pass

    for ce in metadata.get("confidence_evaluations", []):
        try:
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
                (
                    ce["id"],
                    ce["version_id"],
                    ce["score_level"],
                    ce.get("score_value"),
                    ce["method"],
                    ce["rationale"],
                    ce["evaluated_at"],
                ),
            )
        except Exception:
            pass

    for att in metadata.get("attachments", []):
        try:
            await db.execute(
                """
                INSERT INTO attachments (id, item_id, filename, mime_type, storage_path, size_bytes, extraction_status, extraction_error, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    storage_path=excluded.storage_path,
                    size_bytes=excluded.size_bytes,
                    extraction_status=excluded.extraction_status,
                    extraction_error=excluded.extraction_error
                """,
                (
                    att["id"],
                    att["item_id"],
                    att["filename"],
                    att["mime_type"],
                    att["storage_path"],
                    att["size_bytes"],
                    att["extraction_status"],
                    att.get("extraction_error"),
                    att["created_at"],
                ),
            )
        except Exception:
            pass

    await db.commit()

    # Recreate embeddings lazily if needed
    if need_recompute:
        await db.execute("DELETE FROM embedding_chunks")
        await db.execute("DELETE FROM vec_chunks")
        await db.execute("DELETE FROM embedding_chunks_fts")
        await db.commit()

    imported_items = len(metadata.get("items", []))
    return {
        "imported_items": imported_items,
        "skipped_files": skipped_files,
        "message": f"导入完成。共导入 {imported_items} 条知识。"
        + (" 已清除旧向量，将在检索时自动重算。" if need_recompute else ""),
    }


async def reset_system(db: aiosqlite.Connection, password: str) -> None:
    async with db.execute(
        "SELECT password_hash FROM system_config WHERE id = 1"
    ) as cursor:
        row = await cursor.fetchone()
    if not row or not verify_password(password, row[0]):
        raise ValueError("Incorrect password")

    tables = [
        "knowledge_items",
        "knowledge_versions",
        "attachments",
        "tags",
        "tag_links",
        "embedding_chunks",
        "confidence_evaluations",
        "conversations",
        "messages",
        "message_citations",
        "user_profiles",
        "research_tasks",
        "research_sections",
        "research_citations",
    ]
    for t in tables:
        await db.execute(f"DELETE FROM {t}")

    await db.execute(
        """
        UPDATE system_config SET
            initialized = 0,
            password_hash = NULL,
            salt = NULL,
            llm_config = '{}',
            embedding_config = '{}',
            search_config = NULL,
            updated_at = ?
        WHERE id = 1
        """,
        (_now(),),
    )
    await db.commit()

    # Remove files
    files_dir = get_settings().files_dir
    if files_dir.exists():
        shutil.rmtree(files_dir)
        files_dir.mkdir(parents=True, exist_ok=True)


async def archive_old_attachments() -> int:
    settings = get_settings()
    threshold_gb = settings.storage_settings.archive_threshold_gb
    files_dir = settings.files_dir
    if not files_dir.exists():
        return 0

    total_bytes = sum(f.stat().st_size for f in files_dir.rglob("*") if f.is_file())
    if total_bytes < threshold_gb * 1024 * 1024 * 1024:
        return 0

    # Gzip oldest 20% of .enc files
    all_files = sorted(
        [f for f in files_dir.rglob("*.enc") if f.is_file()],
        key=lambda p: p.stat().st_mtime,
    )
    to_archive = all_files[: max(1, len(all_files) // 5)]
    archived = 0
    for f in to_archive:
        if f.suffix == ".gz":
            continue
        gz_path = f.with_suffix(".enc.gz")
        with open(f, "rb") as src:
            with gzip.open(gz_path, "wb") as dst:
                shutil.copyfileobj(src, dst)
        f.unlink()
        archived += 1
    return archived


async def cleanup_old_versions(db: aiosqlite.Connection) -> int:
    settings = get_settings()
    policy = settings.storage_settings.version_retention_policy
    if not policy:
        return 0
    ptype = policy.get("type")
    value = policy.get("value")
    if not ptype or value is None:
        return 0

    removed = 0
    if ptype == "count":
        async with db.execute("SELECT DISTINCT item_id FROM knowledge_versions") as cursor:
            items = [r[0] async for r in cursor]
        for item_id in items:
            async with db.execute(
                """
                SELECT id FROM knowledge_versions
                WHERE item_id = ? ORDER BY created_at DESC LIMIT -1 OFFSET ?
                """,
                (item_id, value),
            ) as cursor:
                to_delete = [r[0] async for r in cursor]
            if to_delete:
                placeholders = ",".join("?" * len(to_delete))
                await db.execute(
                    f"DELETE FROM knowledge_versions WHERE id IN ({placeholders})",
                    to_delete,
                )
                removed += len(to_delete)
    elif ptype == "days":
        cutoff = (datetime.now(timezone.utc) - timedelta(days=value)).isoformat()
        await db.execute("DELETE FROM knowledge_versions WHERE created_at < ?", (cutoff,))
        # aiosqlite total_changes may wrap across awaits; count deletions separately
        removed = getattr(db, "_last_row_count", 0)
    elif ptype == "gb":
        threshold_bytes = value * 1024 * 1024 * 1024
        async with db.execute(
            "SELECT id, LENGTH(content_text) as sz FROM knowledge_versions ORDER BY created_at"
        ) as cursor:
            rows = [(r[0], r[1]) async for r in cursor]
        total = sum(sz for _, sz in rows)
        if total > threshold_bytes:
            to_free = total - threshold_bytes
            freed = 0
            to_delete = []
            for vid, sz in rows:
                if freed >= to_free:
                    break
                to_delete.append(vid)
                freed += sz
            if to_delete:
                placeholders = ",".join("?" * len(to_delete))
                await db.execute(
                    f"DELETE FROM knowledge_versions WHERE id IN ({placeholders})",
                    to_delete,
                )
                removed = len(to_delete)

    await db.commit()
    return removed


async def cleanup_old_logs() -> int:
    settings = get_settings()
    retention_days = settings.log_settings.retention_days
    log_dir = settings.log_dir
    if not log_dir.exists():
        return 0

    import time
    now = time.time()
    cutoff = now - retention_days * 86400
    removed = 0
    for f in log_dir.rglob("*.log"):
        if f.is_file() and f.stat().st_mtime < cutoff:
            f.unlink()
            removed += 1
    return removed
