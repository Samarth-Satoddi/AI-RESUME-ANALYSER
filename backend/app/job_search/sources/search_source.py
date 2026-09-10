from datetime import datetime, timezone
from typing import List, Optional
import httpx

from app.core.config import settings
from app.core.logging import logger
from app.job_search.base import JobSource
from app.job_search.schemas import JobSearchQuery, RawJobListing


class SearchProviderJobSource(JobSource):
    """
    Adapter for legitimate search engines (e.g. Google Custom Search, SerpAPI, Bing Web Search)
    configured via environment credentials. Never attempts unauthorized crawling or bot bypass.
    """
    source_name = "search_provider"

    def __init__(self, search_url: Optional[str] = None, api_key: Optional[str] = None):
        self.search_url = search_url or "https://api.searchprovider.example/v1/jobs"
        self.api_key = api_key or settings.JOB_SEARCH_API_KEY
        self.timeout = float(settings.JOB_SEARCH_TIMEOUT_SECONDS)

    async def search(self, query: JobSearchQuery) -> List[RawJobListing]:
        """
        Search for jobs via search API. If no valid search provider credentials exist,
        safely reports unavailable without fabricating results.
        """
        if not self.api_key or "example" in self.search_url:
            logger.info("SearchProviderJobSource unconfigured or using placeholder endpoint; skipping.")
            return []

        logger.info(f"SearchProviderJobSource querying search provider for '{query.role}' in '{query.location}'")
        search_query_str = f"{query.role} jobs {query.location or ''}".strip()

        params = {
            "q": search_query_str,
            "api_key": self.api_key,
            "num": min(query.limit or 20, 30),
        }

        results: List[RawJobListing] = []

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(self.search_url, params=params)
                if resp.status_code != 200:
                    logger.warning(f"SearchProviderJobSource received status {resp.status_code}")
                    return []

                data = resp.json()
                items = data.get("organic_results", []) or data.get("jobs", [])

                for item in items:
                    results.append(
                        RawJobListing(
                            external_id=str(item.get("id") or item.get("position", "")),
                            source="web_search",
                            title=item.get("title", ""),
                            company=item.get("company_name") or item.get("source"),
                            location=item.get("location") or query.location,
                            remote_type="remote" if "remote" in item.get("title", "").lower() else None,
                            description=item.get("snippet") or item.get("description", ""),
                            url=item.get("link") or item.get("url"),
                            posted_at=None,
                            collected_at=datetime.now(timezone.utc),
                        )
                    )

            logger.info(f"SearchProviderJobSource returned {len(results)} search snippets")
        except Exception as e:
            logger.warning(f"SearchProviderJobSource error: {e}")

        return results
