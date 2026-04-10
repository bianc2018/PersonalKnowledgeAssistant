import pytest


@pytest.mark.asyncio
async def test_download_attachment_happy_path(auth_client):
    original_bytes = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n>>\nendobj\ntrailer\n<<\n/Root 1 0 R\n>>\n%%EOF"
    files = {
        "file": ("test-document.pdf", original_bytes, "application/pdf"),
    }
    data = {"title": "Test PDF", "tags": ""}
    upload_resp = await auth_client.post("/api/knowledge/upload", files=files, data=data)
    assert upload_resp.status_code == 201
    item_id = upload_resp.json()["data"]["id"]

    detail_resp = await auth_client.get(f"/api/knowledge/{item_id}")
    assert detail_resp.status_code == 200
    attachments = detail_resp.json()["data"]["attachments"]
    assert len(attachments) == 1
    attachment_id = attachments[0]["id"]

    download_resp = await auth_client.get(
        f"/api/knowledge/{item_id}/attachments/{attachment_id}/download"
    )
    assert download_resp.status_code == 200
    assert download_resp.headers["content-type"] == "application/pdf"
    assert 'attachment; filename="test-document.pdf"' in download_resp.headers["content-disposition"]
    assert download_resp.content == original_bytes


@pytest.mark.asyncio
async def test_download_attachment_missing_returns_404(auth_client):
    resp = await auth_client.get(
        "/api/knowledge/nonexistent-item/attachments/nonexistent-att/download"
    )
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Attachment not found"


@pytest.mark.asyncio
async def test_download_attachment_unauthorized(client):
    resp = await client.get(
        "/api/knowledge/some-item/attachments/some-att/download"
    )
    assert resp.status_code == 401
