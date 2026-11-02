"""Parola hash'leme ve JWT tabanlı oturum doğrulama.

Bu modül eklenmeden önce backend'de HİÇBİR kimlik doğrulama katmanı
yoktu (bkz. git geçmişi / README 'Bilinen sınırlama'). `get_current_user`
dependency'si artık yüksek etkili uç noktaları (örn. görev onayı) korumak
için kullanılmalıdır.
"""
from __future__ import annotations

import datetime as dt

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.db import get_db
from app.models import User

ALGORITHM = "HS256"

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


def hash_password(plain_password: str) -> str:
    return bcrypt.hashpw(plain_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except ValueError:
        # bozuk/uyumsuz hash — doğrulama başarısız sayılır, hata fırlatılmaz
        return False


def create_access_token(user_id: str) -> str:
    settings = get_settings()
    expires_at = dt.datetime.now(dt.timezone.utc) + dt.timedelta(
        minutes=settings.access_token_expire_minutes
    )
    payload = {"sub": user_id, "exp": expires_at}
    return jwt.encode(payload, settings.app_secret_key, algorithm=ALGORITHM)


def decode_access_token(token: str) -> str | None:
    """Token geçerliyse içindeki user_id'yi (sub) döner, değilse None."""
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.app_secret_key, algorithms=[ALGORITHM])
    except jwt.PyJWTError:
        return None
    return payload.get("sub")


async def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Kimlik doğrulama gerekli veya token geçersiz.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token:
        raise unauthorized

    user_id = decode_access_token(token)
    if not user_id:
        raise unauthorized

    user = await db.get(User, user_id)
    if user is None or not user.is_active:
        raise unauthorized
    return user


async def user_exists(db: AsyncSession) -> bool:
    result = await db.execute(select(User.id).limit(1))
    return result.first() is not None


# --- Basit, süreç-içi login kaba kuvvet koruması -----------------------
# Tek-süreçli (uvicorn, çoklu worker değil) kişisel araç dağıtımı için
# yeterli: bellekte tutulur, yeniden başlatmada sıfırlanır, birden çok
# worker/instance arasında paylaşılmaz. Çok-worker/dağıtık bir kuruluma
# geçilirse Redis tabanlı bir limiter'a taşınmalı.
_MAX_FAILED_ATTEMPTS = 5
_LOCKOUT_SECONDS = 60

_failed_attempts: dict[str, int] = {}
_locked_until: dict[str, dt.datetime] = {}


def check_login_not_locked(email: str) -> None:
    locked_at = _locked_until.get(email)
    if locked_at and dt.datetime.now(dt.timezone.utc) < locked_at:
        remaining = int((locked_at - dt.datetime.now(dt.timezone.utc)).total_seconds())
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            f"Çok fazla başarısız giriş denemesi. {remaining} saniye sonra tekrar deneyin.",
        )


def record_login_failure(email: str) -> None:
    count = _failed_attempts.get(email, 0) + 1
    _failed_attempts[email] = count
    if count >= _MAX_FAILED_ATTEMPTS:
        _locked_until[email] = dt.datetime.now(dt.timezone.utc) + dt.timedelta(
            seconds=_LOCKOUT_SECONDS
        )
        _failed_attempts[email] = 0


def record_login_success(email: str) -> None:
    _failed_attempts.pop(email, None)
    _locked_until.pop(email, None)
