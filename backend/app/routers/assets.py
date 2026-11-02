from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.models import Asset, Project

router = APIRouter(prefix="/assets", tags=["assets"])


class AssetCreate(BaseModel):
    project_id: str
    asset_type: str
    identifier: str
    in_scope: bool = True
    notes: str | None = None


class AssetOut(BaseModel):
    id: str
    project_id: str
    asset_type: str
    identifier: str
    in_scope: bool

    model_config = ConfigDict(from_attributes=True)


@router.post("", response_model=AssetOut, status_code=201)
async def create_asset(payload: AssetCreate, db: AsyncSession = Depends(get_db)) -> Asset:
    project = await db.get(Project, payload.project_id)
    if project is None:
        raise HTTPException(404, "Proje bulunamadı.")
    asset = Asset(**payload.model_dump())
    db.add(asset)
    await db.commit()
    await db.refresh(asset)
    return asset


@router.get("", response_model=list[AssetOut])
async def list_assets(project_id: str, db: AsyncSession = Depends(get_db)) -> list[Asset]:
    result = await db.execute(select(Asset).where(Asset.project_id == project_id))
    return list(result.scalars().all())
