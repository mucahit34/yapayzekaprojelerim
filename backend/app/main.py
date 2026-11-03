from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.routers import ai, assets, auth, health, projects, reports, tasks
from app.services.auth import get_current_user
from app.services.pdf import shutdown_pdf_renderer


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield
    # PDF servisi istekler arasında paylaşılan bir Chromium süreci tutar
    # (bkz. app/services/pdf.py); süreç kapanırken düzgün kapatılmalı.
    await shutdown_pdf_renderer()


app = FastAPI(
    title="Kişisel AI Güvenlik Asistanı",
    description=(
        "Yetkili güvenlik testi kapsamları için proje/bulgu/kanıt yönetimi "
        "ve AI destekli raporlama backend'i."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

# İzinli origin'ler CORS_ALLOWED_ORIGINS ortam değişkeninden gelir
# (varsayılan: yalnızca yerel Vite dev server). docker-compose'daki
# dockerized frontend farklı bir portta (8081) olduğu için o servis
# bu değişkeni override eder — bkz. docker-compose.yml.
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# /health ve /auth (register/login) kimlik doğrulaması gerektirmez.
# Veri değiştiren ve AI çağrısı yapan diğer her şey get_current_user
# arkasında — bkz. app/services/auth.py ve README 'Bilinen sınırlama'.
_auth_required = [Depends(get_current_user)]

app.include_router(health.router)
app.include_router(auth.router, prefix="/api")
app.include_router(projects.router, prefix="/api", dependencies=_auth_required)
app.include_router(assets.router, prefix="/api", dependencies=_auth_required)
app.include_router(tasks.router, prefix="/api", dependencies=_auth_required)
app.include_router(ai.router, prefix="/api", dependencies=_auth_required)
app.include_router(reports.router, prefix="/api", dependencies=_auth_required)
