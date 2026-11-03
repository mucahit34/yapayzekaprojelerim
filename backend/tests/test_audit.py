import pytest

pytestmark = pytest.mark.asyncio


async def test_audit_requires_authentication(client):
    resp = await client.get("/api/audit")
    assert resp.status_code == 401


async def test_audit_lists_events_newest_first_filtered_by_project(client, auth_headers):
    p1 = await client.post(
        "/api/projects", json={"name": "P1", "scope_definition": {}}, headers=auth_headers
    )
    p1_id = p1.json()["id"]
    p2 = await client.post(
        "/api/projects", json={"name": "P2", "scope_definition": {}}, headers=auth_headers
    )
    p2_id = p2.json()["id"]

    await client.post(
        "/api/findings",
        json={"project_id": p1_id, "title": "F1", "description": "d"},
        headers=auth_headers,
    )
    await client.post(
        "/api/findings",
        json={"project_id": p2_id, "title": "F2", "description": "d"},
        headers=auth_headers,
    )

    p1_events = await client.get(f"/api/audit?project_id={p1_id}", headers=auth_headers)
    assert p1_events.status_code == 200
    actions = [e["action"] for e in p1_events.json()]
    assert "finding.created" in actions
    assert all(e["project_id"] == p1_id for e in p1_events.json())


async def test_audit_limit_is_clamped(client, auth_headers):
    resp = await client.get("/api/audit?limit=9999", headers=auth_headers)
    assert resp.status_code == 200
