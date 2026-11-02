from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import ai, assets, auth, health, projects, tasks
from app.services.auth import get_current_user

app = FastAPI(
    title="Kişisel AI Güvenlik Asistanı",
    description=(
        "Yetkili güvenlik testi kapsamları için proje/bulgu/kanıt yönetimi "
        "ve AI destekli raporlama backend'i."
    ),
    version="0.1.0",
)

# Geliştirme ortamında yalnızca localhost frontend origin'ine izin verilir.
# Üretimde bu liste dağıtım ortamına göre daraltılmalıdır.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
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
