import pytest

pytestmark = pytest.mark.asyncio


async def _make_project(client, auth_headers):
    resp = await client.post(
        "/api/projects",
        json={"name": "Acme", "scope_definition": {"in_scope": ["acme.example"]}},
        headers=auth_headers,
    )
    return resp.json()["id"]


async def test_create_finding_defaults_to_suspected(client, auth_headers):
    project_id = await _make_project(client, auth_headers)
    resp = await client.post(
        "/api/findings",
        json={
            "project_id": project_id,
            "title": "SSRF",
            "description": "Dahili metadata servisine erişim",
            "risk_level": "critical",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201
    body = resp.json()
    # Hiçbir bulgu doğrudan 'confirmed' olarak oluşturulamaz.
    assert body["status"] == "suspected"
    assert body["risk_level"] == "critical"


async def test_create_finding_requires_existing_project(client, auth_headers):
    resp = await client.post(
        "/api/findings",
        json={"project_id": "yok", "title": "X", "description": "Y"},
        headers=auth_headers,
    )
    assert resp.status_code == 404


async def test_create_finding_rejects_asset_from_other_project(client, auth_headers):
    project_id = await _make_project(client, auth_headers)
    other_project_id = await _make_project(client, auth_headers)
    asset_resp = await client.post(
        "/api/assets",
        json={"project_id": other_project_id, "asset_type": "domain", "identifier": "x.example"},
        headers=auth_headers,
    )
    asset_id = asset_resp.json()["id"]

    resp = await client.post(
        "/api/findings",
        json={
            "project_id": project_id,
            "asset_id": asset_id,
            "title": "X",
            "description": "Y",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 404


async def test_list_findings_filtered_by_project(client, auth_headers):
    project_id = await _make_project(client, auth_headers)
    other_project_id = await _make_project(client, auth_headers)
    await client.post(
        "/api/findings",
        json={"project_id": project_id, "title": "A", "description": "a"},
        headers=auth_headers,
    )
    await client.post(
        "/api/findings",
        json={"project_id": other_project_id, "title": "B", "description": "b"},
        headers=auth_headers,
    )

    listing = await client.get(f"/api/findings?project_id={project_id}", headers=auth_headers)
    assert listing.status_code == 200
    titles = {f["title"] for f in listing.json()}
    assert titles == {"A"}


async def test_update_finding_status_and_risk_level(client, auth_headers):
    project_id = await _make_project(client, auth_headers)
    create_resp = await client.post(
        "/api/findings",
        json={"project_id": project_id, "title": "X", "description": "Y", "risk_level": "low"},
        headers=auth_headers,
    )
    finding_id = create_resp.json()["id"]

    update_resp = await client.patch(
        f"/api/findings/{finding_id}",
        json={"status": "confirmed", "risk_level": "high"},
        headers=auth_headers,
    )
    assert update_resp.status_code == 200
    body = update_resp.json()
    assert body["status"] == "confirmed"
    assert body["risk_level"] == "high"


async def test_update_finding_not_found(client, auth_headers):
    resp = await client.patch(
        "/api/findings/yok", json={"status": "confirmed"}, headers=auth_headers
    )
    assert resp.status_code == 404


async def test_findings_require_authentication(client):
    resp = await client.get("/api/findings?project_id=x")
    assert resp.status_code == 401
