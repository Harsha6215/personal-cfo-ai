"""
News API — financial news from Google News RSS.
"""

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from backend.core.auth import get_current_user
from backend.models.user import User
from backend.services.market_data.news import fetch_news

router = APIRouter(tags=["News"])


class NewsArticleResponse(BaseModel):
    title: str
    url: str
    source: str
    published: str
    summary: str | None = None


@router.get(
    "",
    response_model=list[NewsArticleResponse],
    summary="Get financial news",
    description="Fetches latest news from Google News RSS. Filter by ticker or topic.",
)
async def get_news(
    q: str = Query(..., description="Search query (ticker, company, or topic)"),
    limit: int = Query(10, le=30),
    user: User = Depends(get_current_user),
):
    articles = await fetch_news(q, limit)
    return [
        NewsArticleResponse(
            title=a.title,
            url=a.url,
            source=a.source,
            published=a.published,
            summary=a.summary,
        )
        for a in articles
    ]
