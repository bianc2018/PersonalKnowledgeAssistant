import gzip
import os
from datetime import datetime, timezone
from pathlib import Path

import aiosqlite

from src.config import get_settings


async def archive_old_attachments(db: aiosqlite.Connection) -> int:
    """Compress old attachments when total files size exceeds threshold.

    Returns number of files archived.
    """
    settings = get_settings()
    threshold_bytes = settings.storage_settings.archive_threshold_gb * 1024 * 1024 * 1024
    files_dir = settings.files_dir

    if not files_dir.exists():
        return 0

    total_size = sum(f.stat().st_size for f in files_dir.rglob("*") if f.is_file())
    if total_size <= threshold_bytes:
        return 0

    # Find oldest un-archived attachments
    rows = await db.execute(
        """
        SELECT id, storage_path FROM attachments
        WHERE storage_path NOT LIKE '%.gz'
        ORDER BY created_at ASC
        LIMIT 10
        """
    )
    archived = 0
    async for row in rows:
        original_path = Path(row[1])
        if not original_path.exists():
            continue
        gz_path = Path(str(original_path) + ".gz")
        with original_path.open("rb") as f_in:
            with gzip.open(gz_path, "wb") as f_out:
                f_out.write(f_in.read())
        original_path.unlink()
        await db.execute(
            "UPDATE attachments SET storage_path = ? WHERE id = ?",
            (str(gz_path), row[0]),
        )
        archived += 1

    await db.commit()
    return archived
