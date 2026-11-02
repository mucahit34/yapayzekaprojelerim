import pytest

pytestmark = pytest.mark.asyncio


async def test_health(client):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_create_and_list_project(client, auth_headers):
    response = await client.post(
        "/api/projects",
        json={
            "name": "Acme Lojistik",
            "description": "Dış yüzey değerlendirmesi",
            "scope_definition": {"in_scope": ["acme-portal.example"]},
        },
        headers=auth_headers,
    )
    assert response.status_code == 200
    project = response.json()
    assert project["name"] == "Acme Lojistik"

    listing = await client.get("/api/projects", headers=auth_headers)
    assert listing.status_code == 200
    assert any(p["id"] == project["id"] for p in listing.json())


async def test_task_creation_rejected_when_out_of_scope(client, auth_headers):
    project_resp = await client.post(
        "/api/projects",
        json={"name": "P1", "scope_definition": {"in_scope": ["acme-portal.example"]}},
        headers=auth_headers,
    )
    project_id = project_resp.json()["id"]

    asset_resp = await client.post(
        "/api/assets",
        json={
            "project_id": project_id,
            "asset_type": "domain",
            "identifier": "unrelated-domain.example",
        },
        headers=auth_headers,
    )
    assert asset_resp.status_code == 201
    asset_id = asset_resp.json()["id"]

    task_resp = await client.post(
        "/api/tasks",
        json={
            "project_id": project_id,
            "asset_id": asset_id,
            "title": "Port taraması",
            "agent_role": "asset_discovery",
        },
        headers=auth_headers,
    )
    assert task_resp.status_code == 403
    assert "kapsamda değil" in task_resp.json()["detail"]


async def test_task_creation_allowed_when_in_scope_and_requires_approval(client, auth_headers):
    project_resp = await client.post(
        "/api/projects",
        json={"name": "P2", "scope_definition": {"in_scope": ["acme-portal.example"]}},
        headers=auth_headers,
    )
    project_id = project_resp.json()["id"]

    asset_resp = await client.post(
        "/api/assets",
        json={
            "project_id": project_id,
            "asset_type": "domain",
            "identifier": "acme-portal.example",
        },
        headers=auth_headers,
    )
    asset_id = asset_resp.json()["id"]

    task_resp = await client.post(
        "/api/tasks",
        json={
            "project_id": project_id,
            "asset_id": asset_id,
            "title": "Port taraması",
            "agent_role": "asset_discovery",
        },
        headers=auth_headers,
    )
    assert task_resp.status_code == 201
    body = task_resp.json()
    # Kapsamda olsa bile aktif işlem varsayılan olarak onay bekler.
    assert body["status"] == "awaiting_approval"
    assert body["requires_approval"] is True


async def test_task_approval_flow(client, auth_headers):
    project_resp = await client.post(
        "/api/projects",
        json={"name": "P3", "scope_definition": {"in_scope": ["acme-portal.example"]}},
        headers=auth_headers,
    )
    project_id = project_resp.json()["id"]
    asset_resp = await client.post(
        "/api/assets",
        json={
            "project_id": project_id,
            "asset_type": "domain",
            "identifier": "acme-portal.example",
        },
        headers=auth_headers,
    )
    asset_id = asset_resp.json()["id"]
    task_resp = await client.post(
        "/api/tasks",
        json={
            "project_id": project_id,
            "asset_id": asset_id,
            "title": "Port taraması",
            "agent_role": "asset_discovery",
        },
        headers=auth_headers,
    )
    task_id = task_resp.json()["id"]

    # approved_by artık istemcinin gönderdiği serbest metinden değil,
    # token'daki kimlik doğrulanmış kullanıcıdan geliyor (query param yok).
    approve_resp = await client.post(f"/api/tasks/{task_id}/approve", headers=auth_headers)
    assert approve_resp.status_code == 200
    assert approve_resp.json()["status"] == "pending"

    # İkinci onay denemesi reddedilmeli (zaten onaylanmış/durum değişmiş).
    second_attempt = await client.post(f"/api/tasks/{task_id}/approve", headers=auth_headers)
    assert second_attempt.status_code == 409


async def test_task_approval_requires_authentication(client, auth_headers):
    project_resp = await client.post(
        "/api/projects",
        json={"name": "P4", "scope_definition": {"in_scope": ["acme-portal.example"]}},
        headers=auth_headers,
    )
    project_id = project_resp.json()["id"]
    asset_resp = await client.post(
        "/api/assets",
        json={
            "project_id": project_id,
            "asset_type": "domain",
            "identifier": "acme-portal.example",
        },
        headers=auth_headers,
    )
    asset_id = asset_resp.json()["id"]
    task_resp = await client.post(
        "/api/tasks",
        json={
            "project_id": project_id,
            "asset_id": asset_id,
            "title": "Port taraması",
            "agent_role": "asset_discovery",
        },
        headers=auth_headers,
    )
    task_id = task_resp.json()["id"]

    # Token olmadan onay denemesi reddedilmeli.
    unauth_attempt = await client.post(f"/api/tasks/{task_id}/approve")
    assert unauth_attempt.status_code == 401
