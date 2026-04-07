import pytest
import pytest_asyncio


@pytest_asyncio.fixture
async def auth_client(client):
    await client.post("/api/system/init", json={"password": "test1234"})
    login = await client.post("/api/auth/login", json={"password": "test1234"})
    token = login.json()["token"]
    client.headers["Authorization"] = f"Bearer {token}"
    yield client


@pytest.mark.asyncio
async def test_create_research_task(auth_client):
    resp = await auth_client.post(
        "/api/research",
        json={
            "topic": "低空经济政策分析",
            "scope_description": "重点关注 2024-2025 年政策",
        },
    )
    assert resp.status_code == 202
    data = resp.json()["data"]
    assert data["status"] == "queued"
    assert data["topic"] == "低空经济政策分析"
    task_id = data["id"]

    # List tasks
    resp = await auth_client.get("/api/research")
    assert resp.status_code == 200
    items = resp.json()["data"]
    assert any(t["id"] == task_id for t in items)

    # Get detail
    resp = await auth_client.get(f"/api/research/{task_id}")
    assert resp.status_code == 200
    detail = resp.json()["data"]
    assert detail["topic"] == "低空经济政策分析"


@pytest.mark.asyncio
async def test_research_respond_not_awaiting(auth_client):
    resp = await auth_client.post(
        "/api/research",
        json={"topic": "测试决策"},
    )
    task_id = resp.json()["data"]["id"]

    resp = await auth_client.post(
        f"/api/research/{task_id}/respond",
        json={"answer": "继续"},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_research_save(auth_client):
    resp = await auth_client.post(
        "/api/research",
        json={"topic": "测试保存"},
    )
    task_id = resp.json()["data"]["id"]

    # In degraded mode worker may complete quickly; allow either pending (400) or completed (201)
    import asyncio
    await asyncio.sleep(0.5)
    status_resp = await auth_client.get(f"/api/research/{task_id}")
    task_status = status_resp.json()["data"]["status"]

    resp = await auth_client.post(f"/api/research/{task_id}/save")
    if task_status == "completed":
        assert resp.status_code == 201
    else:
        assert resp.status_code == 400
