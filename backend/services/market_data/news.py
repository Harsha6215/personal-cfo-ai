"""
News Intelligence Service — fetches financial news from RSS feeds.

Sources: Google News RSS (finance), filtered by ticker/company name.
"""

import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime
from html import unescape
import re

import httpx
import structlog

logger = structlog.get_logger(__name__)


@dataclass
class NewsArticle:
    title: str
    url: str
    source: str
    published: str
    summary: str | None = None


async def fetch_news(query: str, limit: int = 10) -> list[NewsArticle]:
    """
    Fetch news articles from Google News RSS for a given query.

    Args:
        query: Search term (ticker, company name, or topic)
        limit: Max number of articles to return

    Returns:
        List of NewsArticle objects
    """
    try:
        # Google News RSS URL
        url = f"https://news.google.com/rss/search?q={query}+stock+india&hl=en-IN&gl=IN&ceid=IN:en"

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url)
            response.raise_for_status()

        # Parse RSS XML
        root = ET.fromstring(response.text)
        channel = root.find("channel")
        if channel is None:
            return []

        articles: list[NewsArticle] = []
        items = channel.findall("item")

        for item in items[:limit]:
            title_el = item.find("title")
            link_el = item.find("link")
            pub_date_el = item.find("pubDate")
            source_el = item.find("source")
            desc_el = item.find("description")

            title = title_el.text if title_el is not None else ""
            url = link_el.text if link_el is not None else ""
            published = pub_date_el.text if pub_date_el is not None else ""
            source = source_el.text if source_el is not None else "Google News"

            # Clean HTML from description
            summary = None
            if desc_el is not None and desc_el.text:
                summary = re.sub(r"<[^>]+>", "", unescape(desc_el.text))[:200]

            if title and url:
                articles.append(NewsArticle(
                    title=title,
                    url=url,
                    source=source,
                    published=published,
                    summary=summary,
                ))

        logger.info("news.fetched", query=query, count=len(articles))
        return articles

    except Exception as e:
        logger.warning("news.error", query=query, error=str(e))
        return []
