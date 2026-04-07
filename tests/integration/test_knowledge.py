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
async def test_create_text_knowledge(auth_client):
    resp = await auth_client.post(
        "/api/knowledge",
        json={
            "title": "测试知识",
            "content": "这是一条测试知识内容，用于验证系统功能。",
            "source_type": "text",
            "tags": ["测试", "demo"],
        },
    )
    assert resp.status_code == 201
    data = resp.json()["data"]
    assert data["title"] == "测试知识"
    assert data["source_type"] == "text"
    assert len(data["tags"]) == 2


@pytest.mark.asyncio
async def test_list_and_search_knowledge(auth_client):
    await auth_client.post(
        "/api/knowledge",
        json={
            "title": "低空经济",
            "content": "低空经济政策分析内容",
            "source_type": "text",
            "tags": ["policy"],
        },
    )
    resp = await auth_client.get("/api/knowledge?q=低空")
    assert resp.status_code == 200
    data = resp.json()
    assert data["pagination"]["total"] >= 1
    assert any("低空" in item["title"] for item in data["data"])


@pytest.mark.asyncio
async def test_update_and_delete_knowledge(auth_client):
    create_resp = await auth_client.post(
        "/api/knowledge",
        json={
            "title": "待更新",
            "content": "原始内容需要超过五个字的长度要求。",
            "source_type": "text",
        },
    )
    item_id = create_resp.json()["data"]["id"]

    # Update
    resp = await auth_client.patch(
        f"/api/knowledge/{item_id}",
        json={"title": "已更新", "content": "这是完全不同的新内容，用来触发版本变更。"},
    )
    assert resp.status_code == 200
    detail = resp.json()["data"]
    assert detail["title"] == "已更新"
    assert len(detail["versions"]) == 2

    # Delete
    resp = await auth_client.delete(f"/api/knowledge/{item_id}")
    assert resp.status_code == 204

    # Verify soft delete
    resp = await auth_client.get(f"/api/knowledge/{item_id}")
    assert resp.status_code == 200
    assert resp.json()["data"]["is_deleted"] is True


@pytest.mark.asyncio
async def test_knowledge_tags(auth_client):
    await auth_client.post(
        "/api/knowledge",
        json={
            "title": "Tag Test",
            "content": "内容长度要超过五个字才能通过校验。",
            "source_type": "text",
            "tags": ["unique_tag"],
        },
    )
    resp = await auth_client.get("/api/knowledge/tags")
    assert resp.status_code == 200
    tags = resp.json()["data"]
    assert any(t["name"] == "unique_tag" for t in tags)


@pytest.mark.asyncio
async def test_content_too_short_rejected(auth_client):
    resp = await auth_client.post(
        "/api/knowledge",
        json={"title": "短", "content": "太短", "source_type": "text"},
    )
    assert resp.status_code == 422
