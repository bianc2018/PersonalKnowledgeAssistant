import asyncio
import os
import sys
from pathlib import Path

# Ensure project root is on PYTHONPATH for 'src' imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
import pytest_asyncio
import aiosqlite


@pytest_asyncio.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def db_conn(tmp_path):
    """Create a temporary in-memory SQLite database for tests."""
    db_path = tmp_path / "test.db"
    conn = await aiosqlite.connect(str(db_path))
    yield conn
    await conn.close()


@pytest_asyncio.fixture
async def client(tmp_path):
    """Yield an AsyncClient for FastAPI app integration tests using a temp DB."""
    db_path = tmp_path / "test_app.db"
    files_dir = tmp_path / "test_files"
    os.environ["DATABASE_URL"] = str(db_path)
    os.environ["FILES_DIR"] = str(files_dir)
    os.environ["LOG_DIR"] = str(tmp_path / "test_logs")
    os.environ["SECRET_KEY"] = "test-secret-key"

    # Clear any cached settings before importing app
    import src.config
    src.config.get_settings.cache_clear()

    from httpx import AsyncClient, ASGITransport
    from src.main import app
    from src.db.connection import init_db

    # Initialize DB before starting app lifespan
    await init_db(str(db_path))

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    # cleanup
    import src.config
    src.config.get_settings.cache_clear()
