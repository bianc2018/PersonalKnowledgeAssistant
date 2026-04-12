import pytest


@pytest.mark.asyncio
async def test_system_status_uninitialized(client):
    resp = await client.get("/api/system/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["initialized"] is False


@pytest.mark.asyncio
async def test_system_init_and_login(client):
    # Init system with password enabled
    resp = await client.post("/api/system/init", json={"password": "test1234", "password_enabled": True})
    assert resp.status_code == 201
    assert "初始化完成" in resp.json()["message"]

    # Check status
    resp = await client.get("/api/system/status")
    assert resp.status_code == 200
    assert resp.json()["initialized"] is True
    assert resp.json()["password_enabled"] is True

    # Login
    resp = await client.post("/api/auth/login", json={"password": "test1234"})
    assert resp.status_code == 200
    token = resp.json()["data"]["token"]
    assert token

    # Wrong password
    resp = await client.post("/api/auth/login", json={"password": "wrongpass"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_system_config_protected(client):
    # Should be 401 without token
    resp = await client.get("/api/system/config")
    assert resp.status_code == 401

    # Init and login
    await client.post("/api/system/init", json={"password": "test1234", "password_enabled": True})
    login_resp = await client.post("/api/auth/login", json={"password": "test1234"})
    token = login_resp.json()["data"]["token"]

    headers = {"Authorization": f"Bearer {token}"}
    resp = await client.get("/api/system/config", headers=headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "llm_config" in data

    # Update config
    resp = await client.put(
        "/api/system/config",
        headers=headers,
        json={"llm_config": {"base_url": "http://test", "api_key": "sk-test", "model": "gpt-4"}},
    )
    assert resp.status_code == 200
    cfg = resp.json()["data"]
    assert cfg["llm_config"]["base_url"] == "http://test"


@pytest.mark.asyncio
async def test_init_weak_password_rejected(client):
    # Too short
    resp = await client.post("/api/system/init", json={"password": "short1", "password_enabled": True})
    assert resp.status_code == 422

    # No digit
    resp = await client.post("/api/system/init", json={"password": "nodigits", "password_enabled": True})
    assert resp.status_code == 422

    # No letter
    resp = await client.post("/api/system/init", json={"password": "12345678", "password_enabled": True})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_system_init_no_password_and_status(client):
    resp = await client.post("/api/system/init", json={"password_enabled": False})
    assert resp.status_code == 201
    assert "初始化完成" in resp.json()["message"]

    resp = await client.get("/api/system/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["initialized"] is True
    assert data["password_enabled"] is False


@pytest.mark.asyncio
async def test_no_auth_login_and_bypass(client):
    await client.post("/api/system/init", json={"password_enabled": False})

    resp = await client.post("/api/auth/login", json={})
    assert resp.status_code == 200
    assert resp.json()["data"]["token"] == "no-auth"

    # Access protected route without Authorization header
    resp = await client.get("/api/system/config")
    assert resp.status_code == 200
    assert "llm_config" in resp.json()["data"]


@pytest.mark.asyncio
async def test_init_password_enabled_missing_password_rejected(client):
    resp = await client.post("/api/system/init", json={"password_enabled": True})
    assert resp.status_code == 400
