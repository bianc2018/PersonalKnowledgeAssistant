import asyncio
import pytest
import pytest_asyncio
import aiosqlite


@pytest_asyncio.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
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
async def client():
    """Yield an AsyncClient for FastAPI app integration tests."""
    from httpx import AsyncClient
    from src.main import app

    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
