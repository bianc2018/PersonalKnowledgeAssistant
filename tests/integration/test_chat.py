import pytest
import pytest_asyncio


@pytest_asyncio.fixture
async def auth_client(client):
    await client.post("/api/system/init", json={"password": "test1234"})
    login = await client.post("/api/auth/login", json={"password": "test1234"})
    token = login.json()["data"]["token"]
    client.headers["Authorization"] = f"Bearer {token}"
    yield client


@pytest.mark.asyncio
async def test_chat_conversation_crud(auth_client):
    # Create conversation
    resp = await auth_client.post("/api/chat/conversations")
    assert resp.status_code == 201
    conv_id = resp.json()["data"]["id"]

    # List conversations
    resp = await auth_client.get("/api/chat/conversations")
    assert resp.status_code == 200
    assert any(c["id"] == conv_id for c in resp.json()["data"])

    # Send message (non-stream, no LLM configured -> degraded mode)
    resp = await auth_client.post(
        f"/api/chat/conversations/{conv_id}/messages",
        json={"content": "你好", "stream": False},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "assistant" == data["role"]
    assert "降级模式" in data["content"] or len(data["content"]) > 0

    # Get messages
    resp = await auth_client.get(f"/api/chat/conversations/{conv_id}/messages")
    assert resp.status_code == 200
    messages = resp.json()["data"]
    assert len(messages) == 2  # user + assistant


@pytest.mark.asyncio
async def test_chat_stream(auth_client):
    resp = await auth_client.post("/api/chat/conversations")
    conv_id = resp.json()["data"]["id"]

    resp = await auth_client.post(
        f"/api/chat/conversations/{conv_id}/messages",
        json={"content": "测试流式", "stream": True},
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/event-stream")
    body = resp.text
    assert "event: delta" in body or "event: done" in body
