import pytest

pytestmark = pytest.mark.asyncio

CREDS = {"email": "mucahit@example.com", "password": "cok-guvenli-parola"}


async def test_register_then_login(client):
    register_resp = await client.post("/api/auth/register", json=CREDS)
    assert register_resp.status_code == 201
    assert register_resp.json()["email"] == CREDS["email"]

    login_resp = await client.post(
        "/api/auth/login",
        data={"username": CREDS["email"], "password": CREDS["password"]},
    )
    assert login_resp.status_code == 200
    body = login_resp.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]


async def test_register_rejects_second_user(client):
    await client.post("/api/auth/register", json=CREDS)
    second = await client.post(
        "/api/auth/register", json={"email": "other@example.com", "password": "baska-parola-123"}
    )
    assert second.status_code == 403


async def test_register_rejects_short_password(client):
    resp = await client.post(
        "/api/auth/register", json={"email": "a@example.com", "password": "kisa"}
    )
    assert resp.status_code == 400


async def test_login_wrong_password_rejected(client):
    await client.post("/api/auth/register", json=CREDS)
    resp = await client.post(
        "/api/auth/login", data={"username": CREDS["email"], "password": "yanlis-parola"}
    )
    assert resp.status_code == 401


async def test_protected_endpoint_requires_token(client):
    resp = await client.get("/api/projects")
    assert resp.status_code == 401


async def test_protected_endpoint_rejects_garbage_token(client):
    resp = await client.get(
        "/api/projects", headers={"Authorization": "Bearer not-a-real-token"}
    )
    assert resp.status_code == 401


async def test_login_lockout_after_repeated_failures(client):
    await client.post("/api/auth/register", json=CREDS)

    for _ in range(5):
        resp = await client.post(
            "/api/auth/login", data={"username": CREDS["email"], "password": "yanlis"}
        )
        assert resp.status_code == 401

    # 5. başarısız denemeden sonra hesap geçici olarak kilitlenmeli —
    # doğru parola gönderilse bile.
    locked_resp = await client.post(
        "/api/auth/login", data={"username": CREDS["email"], "password": CREDS["password"]}
    )
    assert locked_resp.status_code == 429


async def test_protected_endpoint_works_with_valid_token(client):
    await client.post("/api/auth/register", json=CREDS)
    login_resp = await client.post(
        "/api/auth/login",
        data={"username": CREDS["email"], "password": CREDS["password"]},
    )
    token = login_resp.json()["access_token"]

    resp = await client.get(
        "/api/projects", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200
