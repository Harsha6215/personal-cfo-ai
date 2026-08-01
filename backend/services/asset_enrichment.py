"""
Asset Enrichment Service — Story 3.2

Enriches bare Asset records (created during import with just ticker + name)
with full data from market data providers: sector, industry, ISIN, description, etc.

Usage:
    service = AssetEnrichmentService(db, market_service)
    await service.enrich_asset(asset_id)
    await service.enrich_all_unenriched()
"""

import structlog
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.asset import Asset
from backend.services.market_data import MarketDataService

logger = structlog.get_logger(__name__)


class AssetEnrichmentService:
    def __init__(self, db: AsyncSession, market_service: MarketDataService):
        self.db = db
        self.market = market_service

    async def enrich_asset(self, asset_id: str) -> Asset | None:
        """Enrich a single asset with data from market provider."""
        result = await self.db.execute(select(Asset).where(Asset.id == asset_id))
        asset = result.scalar_one_or_none()
        if not asset:
            return None

        info = await self.market.get_company_info(asset.ticker)
        if not info:
            logger.warning("enrichment.no_data", ticker=asset.ticker)
            return asset

        # Update fields (only if provider returned non-null values)
        if info.name and info.name != asset.ticker:
            asset.name = info.name
        if info.sector:
            asset.sector = info.sector
        if info.industry:
            asset.industry = info.industry
        if info.isin:
            asset.isin = info.isin
        if info.currency:
            asset.currency = info.currency

        await self.db.flush()
        logger.info("enrichment.success", ticker=asset.ticker, sector=asset.sector, industry=asset.industry)
        return asset

    async def enrich_by_ticker(self, ticker: str) -> Asset | None:
        """Find asset by ticker and enrich it."""
        result = await self.db.execute(select(Asset).where(Asset.ticker == ticker).limit(1))
        asset = result.scalar_one_or_none()
        if not asset:
            return None
        return await self.enrich_asset(asset.id)

    async def enrich_all_unenriched(self) -> int:
        """
        Find all assets missing sector/industry and enrich them.
        Returns count of assets enriched.
        """
        result = await self.db.execute(
            select(Asset).where(
                or_(Asset.sector == None, Asset.sector == "", Asset.industry == None)  # noqa: E711
            ).limit(50)  # batch size
        )
        assets = result.scalars().all()

        enriched = 0
        for asset in assets:
            try:
                updated = await self.enrich_asset(asset.id)
                if updated and updated.sector:
                    enriched += 1
            except Exception as e:
                logger.warning("enrichment.failed", ticker=asset.ticker, error=str(e))

        logger.info("enrichment.batch_complete", total=len(assets), enriched=enriched)
        return enriched
