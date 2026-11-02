import pytest

pytestmark = pytest.mark.asyncio


async def test_ai_draft_requires_authentication(client):
    response = await client.post(
        "/api/ai/draft",
        json={"instruction": "Kısalt", "section_text": "Uzun bir metin."},
    )
    assert response.status_code == 401


async def test_ai_draft_unavailable_without_api_key(client, auth_headers, monkeypatch):
    from app.core.config import get_settings

    get_settings.cache_clear()
    response = await client.post(
        "/api/ai/draft",
        json={"instruction": "Kısalt", "section_text": "Uzun bir metin."},
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["available"] is False
    assert "yapılandırılmamış" in body["draft"]
