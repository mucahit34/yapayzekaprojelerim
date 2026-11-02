"""Kimlik doğrulama uç noktaları.

Bu kişisel asistan tek kullanıcı için tasarlandığı için `/register`
yalnızca veritabanında HİÇ kullanıcı yokken çalışır (ilk kurulum).
Ondan sonra 403 döner — yeni kullanıcı eklemek için doğrudan veritabanı
erişimi (veya ileride eklenecek bir 'davet' akışı) gerekir."""
from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, ConfigDict, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.models import User
from app.services.audit import record_audit_event
from app.services.auth import (
    check_login_not_locked,
    create_access_token,
    hash_password,
    record_login_failure,
    record_login_success,
    user_exists,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])

# user_exists() kontrolü ile User satırının eklenmesi arasında bir TOCTOU
# penceresi var; bu kilit tek süreç içinde eşzamanlı iki /register
# isteğinin ikisinin de "kullanıcı yok" görmesini engeller. Çoklu worker/
# instance dağıtımında bu yeterli değildir — o durumda DB seviyesinde bir
# singleton kısıtı (örn. tekil bir satırda unique constraint) gerekir.
_register_lock = asyncio.Lock()


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    display_name: str | None = None


class UserOut(BaseModel):
    id: str
    email: str
    display_name: str | None

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


@router.post("/register", response_model=UserOut, status_code=201)
async def register(payload: RegisterRequest, db: AsyncSession = Depends(get_db)) -> User:
    if len(payload.password) < 10:
        raise HTTPException(400, "Parola en az 10 karakter olmalı.")

    async with _register_lock:
        if await user_exists(db):
            raise HTTPException(
                403,
                "Zaten bir kullanıcı kayıtlı. Bu kişisel asistan tek kullanıcı için "
                "tasarlandı; yeni bir hesap eklemek için doğrudan veritabanı erişimi "
                "gerekir.",
            )
        user = User(
            email=payload.email,
            hashed_password=hash_password(payload.password),
            display_name=payload.display_name,
        )
        db.add(user)
        await record_audit_event(db, actor=payload.email, action="auth.user_registered")
        await db.commit()
        await db.refresh(user)
        return user


@router.post("/login", response_model=TokenResponse)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)
) -> TokenResponse:
    check_login_not_locked(form_data.username)

    result = await db.execute(select(User).where(User.email == form_data.username))
    user = result.scalar_one_or_none()

    if user is None or not user.is_active or not verify_password(
        form_data.password, user.hashed_password
    ):
        record_login_failure(form_data.username)
        await record_audit_event(db, actor=form_data.username, action="auth.login_failed")
        await db.commit()
        raise HTTPException(401, "Geçersiz e-posta veya parola.")

    record_login_success(user.email)
    await record_audit_event(db, actor=user.email, action="auth.login_succeeded")
    await db.commit()
    return TokenResponse(access_token=create_access_token(user.id))
