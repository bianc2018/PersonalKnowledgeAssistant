import sqlite3
from contextlib import asynccontextmanager
from pathlib import Path

import aiosqlite

from src.config import get_settings


async def _init_connection(conn: aiosqlite.Connection) -> None:
    """Enable WAL mode and load extensions."""
    await conn.execute("PRAGMA journal_mode=WAL")
    await conn.execute("PRAGMA foreign_keys=ON")

    try:
        import sqlite_vec

        await conn.enable_load_extension(True)
        await conn.load_extension(sqlite_vec.loadable_path())
    except Exception:
        # sqlite-vec may already be statically linked in some builds.
        pass


async def init_db(db_path: str | None = None, embedding_dim: int = 1536) -> aiosqlite.Connection:
    """Initialize database schema and virtual tables."""
    settings = get_settings()
    path = db_path or settings.database_url
    Path(path).parent.mkdir(parents=True, exist_ok=True)

    conn = await aiosqlite.connect(path)
    await _init_connection(conn)

    schema_path = Path(__file__).with_name("schema.sql")
    if schema_path.exists():
        async with conn.executescript(schema_path.read_text("utf-8")):
            pass

    # Recreate virtual tables if schema changed (safe for MVP lifecycle)
    await conn.execute("DROP TABLE IF EXISTS vec_chunks")
    await conn.execute("DROP TABLE IF EXISTS vec_chunks_fts")
    await conn.execute("DROP TABLE IF EXISTS embedding_chunks_fts")

    # Create sqlite-vec virtual table for embeddings only
    await conn.execute(
        f"""
        CREATE VIRTUAL TABLE IF NOT EXISTS vec_chunks USING vec0(
            chunk_id TEXT PRIMARY KEY,
            embedding FLOAT[{embedding_dim}]
        )
        """
    )

    # Create FTS5 virtual table backed by embedding_chunks
    await conn.execute(
        """
        CREATE VIRTUAL TABLE IF NOT EXISTS embedding_chunks_fts USING fts5(
            chunk_text,
            content='embedding_chunks',
            content_rowid='rowid'
        )
        """
    )

    await conn.commit()
    return conn


@asynccontextmanager
async def get_db_connection(db_path: str | None = None):
    """Yield a managed database connection."""
    settings = get_settings()
    path = db_path or settings.database_url
    conn = await aiosqlite.connect(path)
    await _init_connection(conn)
    try:
        yield conn
    finally:
        await conn.close()


async def get_db() -> aiosqlite.Connection:
    """Dependency for FastAPI routes."""
    settings = get_settings()
    conn = await aiosqlite.connect(settings.database_url)
    await _init_connection(conn)
    return conn
