FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# PDF dışa aktarma (app/services/pdf.py) gerçek bir Chromium gerektirir.
# --with-deps, Debian paket bağımlılıklarını da kurar.
RUN playwright install --with-deps chromium

COPY app ./app
COPY migrations ./migrations
COPY alembic.ini .

EXPOSE 8000
# Konteyner her başladığında migration'lar güncellenir, sonra uygulama
# başlar — DATABASE_URL env_file'dan (.env) gelir.
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
