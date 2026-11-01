from fastapi import FastAPI

from app.routers import health, projects

app = FastAPI(
    title="Kişisel AI Güvenlik Asistanı",
    description=(
        "Yetkili güvenlik testi kapsamları için proje/bulgu/kanıt yönetimi "
        "ve AI destekli raporlama backend'i."
    ),
    version="0.1.0",
)

app.include_router(health.router)
app.include_router(projects.router, prefix="/api")
