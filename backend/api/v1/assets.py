"""
Asset API — read-only access to the asset master catalog.

These endpoints allow querying and creating assets.
Assets are auto-created during import but can also be manually added.
"""

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.auth import get_current_user
from backend.core.database import get_db
from backend.models.asset import Asset, AssetType, Exchange
from backend.models.user import User

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["Assets"])


# ── Schemas ────────────────────────────────────────────────────────────────────

class AssetResponse(BaseModel):
    id: str
    isin: str | None
    ticker: str
    exchange: str
    name: str
    asset_type: str
    sector: str | None
    industry: str | None
    currency: str

    model_config = {"from_attributes": True}


class AssetCreate(BaseModel):
    ticker: str
    name: str
    isin: str | None = None
    exchange: str = "NSE"
    asset_type: str = "STOCK"
    sector: str | None = None
    industry: str | None = None
    currency: str = "INR"


# ── Routes ─────────────────────────────────────────────────────────────────────

@router.get(
    "",
    response_model=list[AssetResponse],
    summary="List assets",
    description="Search or list all assets in the catalog.",
)
async def list_assets(
    q: str | None = Query(None, description="Search by ticker or name"),
    asset_type: str | None = Query(None),
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = select(Asset)
    if q:
        query = query.where(
            Asset.ticker.ilike(f"%{q}%") | Asset.name.ilike(f"%{q}%")
        )
    if asset_type:
        query = query.where(Asset.asset_type == asset_type)
    query = query.limit(limit).order_by(Asset.ticker)

    result = await db.execute(query)
    return result.scalars().all()


@router.post(
    "",
    response_model=AssetResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an asset",
)
async def create_asset(
    body: AssetCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    asset = Asset(
        ticker=body.ticker.upper(),
        name=body.name,
        isin=body.isin,
        exchange=Exchange(body.exchange),
        asset_type=AssetType(body.asset_type),
        sector=body.sector,
        industry=body.industry,
        currency=body.currency,
    )
    db.add(asset)
    await db.flush()
    await db.refresh(asset)
    logger.info("asset.created", asset_id=asset.id, ticker=asset.ticker)
    return asset


@router.get(
    "/{asset_id}",
    response_model=AssetResponse,
    summary="Get asset by ID",
)
async def get_asset(
    asset_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(select(Asset).where(Asset.id == asset_id))
    asset = result.scalar_one_or_none()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    return asset


# ── Enrichment endpoints ───────────────────────────────────────────────────────

from backend.services.market_data import MarketDataService, YahooFinanceProvider
from backend.services.asset_enrichment import AssetEnrichmentService

_market_service = MarketDataService(provider=YahooFinanceProvider())


@router.post(
    "/{asset_id}/enrich",
    response_model=AssetResponse,
    summary="Enrich an asset with market data",
    description="Fetches sector, industry, ISIN, and other details from Yahoo Finance.",
)
async def enrich_asset(
    asset_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    service = AssetEnrichmentService(db, _market_service)
    asset = await service.enrich_asset(asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    return asset


@router.post(
    "/enrich-all",
    summary="Enrich all assets missing sector/industry",
    description="Batch enrichment — fetches data for all unenriched assets.",
)
async def enrich_all_assets(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    service = AssetEnrichmentService(db, _market_service)
    count = await service.enrich_all_unenriched()
    return {"enriched": count, "message": f"Enriched {count} assets"}


@router.get(
    "/ticker/{ticker}",
    response_model=AssetResponse,
    summary="Get asset by ticker",
)
async def get_asset_by_ticker(
    ticker: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(select(Asset).where(Asset.ticker == ticker.upper()).limit(1))
    asset = result.scalar_one_or_none()
    if not asset:
        raise HTTPException(status_code=404, detail=f"Asset {ticker} not found")
    return asset
