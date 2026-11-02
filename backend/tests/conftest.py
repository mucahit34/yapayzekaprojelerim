import os

# app.core.db modül yüklenirken get_settings() çağrılıyor; bu yüzden env
# değişkenleri app.* import edilmeden ÖNCE ayarlanmalı.
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("APP_SECRET_KEY", "test-only")

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.db import Base, get_db
from app.main import app


@pytest.fixture(autouse=True)
def _reset_login_rate_limit_state():
    # app.services.auth'daki _failed_attempts/_locked_until modül seviyesi
    # (süreç-içi) state'tir; testler arasında sızmaması için her testten
    # önce ve sonra temizlenir.
    from app.services import auth as auth_service

    auth_service._failed_attempts.clear()
    auth_service._locked_until.clear()
    yield
    auth_service._failed_attempts.clear()
    auth_service._locked_until.clear()


@pytest_asyncio.fixture
async def db_session():
    """Telegram servis katmanı gibi FastAPI dependency injection'ı olmadan
    doğrudan AsyncSession kullanan kodu test etmek için."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with session_factory() as session:
        yield session
    await engine.dispose()


@pytest_asyncio.fixture
async def client():
    # StaticPool: :memory: sqlite her yeni bağlantıda sıfırlanır; testler
    # boyunca tek bağlantıyı paylaşmak için gerekli.
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async def override_get_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
    await engine.dispose()


@pytest_asyncio.fixture
async def auth_headers(client):
    """Testler için bir kullanıcı kaydeder, giriş yapar ve Authorization
    header'ı döner — korumalı uç noktaları çağıran testler bunu kullanır."""
    creds = {"email": "fixture-user@example.com", "password": "yeterince-uzun-parola"}
    await client.post("/api/auth/register", json=creds)
    login_resp = await client.post(
        "/api/auth/login", data={"username": creds["email"], "password": creds["password"]}
    )
    token = login_resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
