from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import ai, assets, health, projects, tasks

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

app.include_router(health.router)
app.include_router(projects.router, prefix="/api")
app.include_router(assets.router, prefix="/api")
app.include_router(tasks.router, prefix="/api")
app.include_router(ai.router, prefix="/api")
