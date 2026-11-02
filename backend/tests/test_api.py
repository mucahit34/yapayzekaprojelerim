import pytest

pytestmark = pytest.mark.asyncio


async def test_health(client):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_create_and_list_project(client):
    response = await client.post(
        "/api/projects",
        json={
            "name": "Acme Lojistik",
            "description": "Dış yüzey değerlendirmesi",
            "scope_definition": {"in_scope": ["acme-portal.example"]},
        },
    )
    assert response.status_code == 200
    project = response.json()
    assert project["name"] == "Acme Lojistik"

    listing = await client.get("/api/projects")
    assert listing.status_code == 200
    assert any(p["id"] == project["id"] for p in listing.json())


async def test_task_creation_rejected_when_out_of_scope(client):
    project_resp = await client.post(
        "/api/projects",
        json={"name": "P1", "scope_definition": {"in_scope": ["acme-portal.example"]}},
    )
    project_id = project_resp.json()["id"]

    asset_resp = await client.post(
        "/api/assets",
        json={
            "project_id": project_id,
            "asset_type": "domain",
            "identifier": "unrelated-domain.example",
        },
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
    )
    assert task_resp.status_code == 403
    assert "kapsamda değil" in task_resp.json()["detail"]


async def test_task_creation_allowed_when_in_scope_and_requires_approval(client):
    project_resp = await client.post(
        "/api/projects",
        json={"name": "P2", "scope_definition": {"in_scope": ["acme-portal.example"]}},
    )
    project_id = project_resp.json()["id"]

    asset_resp = await client.post(
        "/api/assets",
        json={
            "project_id": project_id,
            "asset_type": "domain",
            "identifier": "acme-portal.example",
        },
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
    )
    assert task_resp.status_code == 201
    body = task_resp.json()
    # Kapsamda olsa bile aktif işlem varsayılan olarak onay bekler.
    assert body["status"] == "awaiting_approval"
    assert body["requires_approval"] is True


async def test_task_approval_flow(client):
    project_resp = await client.post(
        "/api/projects",
        json={"name": "P3", "scope_definition": {"in_scope": ["acme-portal.example"]}},
    )
    project_id = project_resp.json()["id"]
    asset_resp = await client.post(
        "/api/assets",
        json={
            "project_id": project_id,
            "asset_type": "domain",
            "identifier": "acme-portal.example",
        },
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
    )
    task_id = task_resp.json()["id"]

    approve_resp = await client.post(f"/api/tasks/{task_id}/approve?approved_by=mucahit")
    assert approve_resp.status_code == 200
    assert approve_resp.json()["status"] == "pending"

    # İkinci onay denemesi reddedilmeli (zaten onaylanmış/durum değişmiş).
    second_attempt = await client.post(f"/api/tasks/{task_id}/approve?approved_by=mucahit")
    assert second_attempt.status_code == 409
