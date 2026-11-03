import pytest

pytestmark = pytest.mark.asyncio


async def _make_project(client, auth_headers):
    resp = await client.post(
        "/api/projects",
        json={"name": "Acme", "scope_definition": {"in_scope": ["acme.example"]}},
        headers=auth_headers,
    )
    return resp.json()["id"]


SNAPSHOT_V1 = {
    "template": "executive-brief",
    "sections": [{"id": "s1", "title": "Özet", "kind": "text", "body": "İlk sürüm"}],
}
SNAPSHOT_V2 = {
    "template": "executive-brief",
    "sections": [{"id": "s1", "title": "Özet", "kind": "text", "body": "Güncellenmiş sürüm"}],
}


async def test_upsert_report_creates_then_updates_same_record(client, auth_headers):
    project_id = await _make_project(client, auth_headers)

    first = await client.put(
        "/api/reports",
        json={"project_id": project_id, "template": "executive-brief", "data_snapshot": SNAPSHOT_V1},
        headers=auth_headers,
    )
    assert first.status_code == 200
    report_id = first.json()["id"]
    assert first.json()["data_snapshot"] == SNAPSHOT_V1

    second = await client.put(
        "/api/reports",
        json={"project_id": project_id, "template": "executive-brief", "data_snapshot": SNAPSHOT_V2},
        headers=auth_headers,
    )
    assert second.status_code == 200
    # Aynı (project, template) için ikinci PUT yeni kayıt değil, günceleme
    # yapmalı (upsert) — rapor geçmişi ReportRevision'da tutulur.
    assert second.json()["id"] == report_id
    assert second.json()["data_snapshot"] == SNAPSHOT_V2

    listing = await client.get(f"/api/reports?project_id={project_id}", headers=auth_headers)
    assert len(listing.json()) == 1


async def test_upsert_report_requires_existing_project(client, auth_headers):
    resp = await client.put(
        "/api/reports",
        json={"project_id": "does-not-exist", "template": "x", "data_snapshot": SNAPSHOT_V1},
        headers=auth_headers,
    )
    assert resp.status_code == 404


async def test_revision_create_and_approve_updates_report(client, auth_headers):
    project_id = await _make_project(client, auth_headers)
    report_resp = await client.put(
        "/api/reports",
        json={"project_id": project_id, "template": "executive-brief", "data_snapshot": SNAPSHOT_V1},
        headers=auth_headers,
    )
    report_id = report_resp.json()["id"]

    revision_resp = await client.post(
        f"/api/reports/{report_id}/revisions",
        json={"content": SNAPSHOT_V2, "is_ai_draft": True},
        headers=auth_headers,
    )
    assert revision_resp.status_code == 201
    revision = revision_resp.json()
    assert revision["approved"] is False
    assert revision["is_ai_draft"] is True

    # Onaylanana kadar rapor eski halinde kalmalı.
    unchanged = await client.get(f"/api/reports?project_id={project_id}", headers=auth_headers)
    assert unchanged.json()[0]["data_snapshot"] == SNAPSHOT_V1

    approve_resp = await client.post(
        f"/api/reports/{report_id}/revisions/{revision['id']}/approve", headers=auth_headers
    )
    assert approve_resp.status_code == 200
    assert approve_resp.json()["data_snapshot"] == SNAPSHOT_V2

    # Aynı revizyon ikinci kez onaylanamaz.
    second_approve = await client.post(
        f"/api/reports/{report_id}/revisions/{revision['id']}/approve", headers=auth_headers
    )
    assert second_approve.status_code == 409


async def test_list_revisions_ordered_newest_first_with_actor(client, auth_headers):
    project_id = await _make_project(client, auth_headers)
    report_resp = await client.put(
        "/api/reports",
        json={"project_id": project_id, "template": "t1", "data_snapshot": SNAPSHOT_V1},
        headers=auth_headers,
    )
    report_id = report_resp.json()["id"]

    first = await client.post(
        f"/api/reports/{report_id}/revisions",
        json={"content": SNAPSHOT_V1, "is_ai_draft": False},
        headers=auth_headers,
    )
    second = await client.post(
        f"/api/reports/{report_id}/revisions",
        json={"content": SNAPSHOT_V2, "is_ai_draft": True},
        headers=auth_headers,
    )

    listing = await client.get(f"/api/reports/{report_id}/revisions", headers=auth_headers)
    assert listing.status_code == 200
    revisions = listing.json()
    assert len(revisions) == 2
    # En yeni en üstte.
    assert revisions[0]["id"] == second.json()["id"]
    assert revisions[1]["id"] == first.json()["id"]
    # Taslağı oluşturan kullanıcı (fixture-user@example.com) kayıtlı olmalı.
    assert revisions[0]["created_by"] == "fixture-user@example.com"
    assert revisions[0]["is_ai_draft"] is True
    assert "created_at" in revisions[0]


async def test_revision_approve_requires_matching_report(client, auth_headers):
    project_id = await _make_project(client, auth_headers)
    report_resp = await client.put(
        "/api/reports",
        json={"project_id": project_id, "template": "t1", "data_snapshot": SNAPSHOT_V1},
        headers=auth_headers,
    )
    report_id = report_resp.json()["id"]
    revision_resp = await client.post(
        f"/api/reports/{report_id}/revisions",
        json={"content": SNAPSHOT_V2, "is_ai_draft": False},
        headers=auth_headers,
    )
    revision_id = revision_resp.json()["id"]

    other_report_resp = await client.put(
        "/api/reports",
        json={"project_id": project_id, "template": "t2", "data_snapshot": SNAPSHOT_V1},
        headers=auth_headers,
    )
    other_report_id = other_report_resp.json()["id"]

    mismatched = await client.post(
        f"/api/reports/{other_report_id}/revisions/{revision_id}/approve", headers=auth_headers
    )
    assert mismatched.status_code == 404


async def test_pdf_export_requires_authentication(client):
    resp = await client.get("/api/reports/does-not-exist/pdf")
    assert resp.status_code == 401


async def test_pdf_export_404_for_missing_report(client, auth_headers):
    resp = await client.get("/api/reports/does-not-exist/pdf", headers=auth_headers)
    assert resp.status_code == 404


async def test_pdf_export_produces_real_pdf_bytes(client, auth_headers):
    project_id = await _make_project(client, auth_headers)
    report_resp = await client.put(
        "/api/reports",
        json={
            "project_id": project_id,
            "template": "executive-brief",
            "data_snapshot": {
                "template": "executive-brief",
                "sections": [
                    {"id": "cover", "title": "Kapak", "kind": "cover", "body": "Acme — Test Raporu\nTarih: 2026"},
                    {
                        "id": "findings",
                        "title": "Bulgular",
                        "kind": "findings",
                        "body": "critical:Test bulgusu",
                    },
                ],
            },
        },
        headers=auth_headers,
    )
    report_id = report_resp.json()["id"]

    pdf_resp = await client.get(f"/api/reports/{report_id}/pdf", headers=auth_headers)
    assert pdf_resp.status_code == 200
    assert pdf_resp.headers["content-type"] == "application/pdf"
    # Gerçek bir PDF dosyası her zaman bu imzayla başlar — sahte/boş bir
    # "başarı" değil, gerçekten render edilmiş bir dosya olduğunu kanıtlar.
    assert pdf_resp.content[:5] == b"%PDF-"
    assert len(pdf_resp.content) > 500
