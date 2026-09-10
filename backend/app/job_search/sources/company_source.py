from datetime import datetime, timezone
from typing import List, Optional
import httpx

from app.core.config import settings
from app.core.logging import logger
from app.job_search.base import JobSource
from app.job_search.schemas import JobSearchQuery, RawJobListing


class CompanyCareerSource(JobSource):
    """
    Reusable adapter for official company career feeds.
    Queries public board APIs (such as Greenhouse and Lever open posting feeds)
    without web scraping or bot circumvention.
    """
    source_name = "company_careers"

    # Example companies offering official open career board endpoints
    POPULAR_COMPANIES = ["gitlab", "github", "stripe", "canonical"]

    def __init__(self, target_companies: Optional[List[str]] = None):
        self.target_companies = target_companies or self.POPULAR_COMPANIES
        self.timeout = float(settings.JOB_SEARCH_TIMEOUT_SECONDS)

    async def _fetch_greenhouse_board(self, client: httpx.AsyncClient, company: str, role_filter: str) -> List[RawJobListing]:
        """Query official Greenhouse board API."""
        url = f"https://boards-api.greenhouse.io/v1/boards/{company}/jobs"
        results: List[RawJobListing] = []
        try:
            resp = await client.get(url)
            if resp.status_code != 200:
                return []
            data = resp.json()
            jobs = data.get("jobs", [])

            filter_terms = [w.lower() for w in role_filter.split() if len(w) > 2]

            for job in jobs:
                title = job.get("title", "")
                title_lower = title.lower()

                # Basic role keyword relevance filter
                if filter_terms and not any(t in title_lower for t in filter_terms):
                    continue

                updated_at_str = job.get("updated_at")
                posted_date = None
                if updated_at_str:
                    try:
                        posted_date = datetime.fromisoformat(updated_at_str.replace("Z", "+00:00"))
                    except Exception:
                        posted_date = None

                loc = job.get("location", {}).get("name") if isinstance(job.get("location"), dict) else None

                results.append(
                    RawJobListing(
                        external_id=str(job.get("id")),
                        source=f"greenhouse:{company}",
                        title=title,
                        company=company.capitalize(),
                        location=loc,
                        remote_type="remote" if loc and "remote" in loc.lower() else None,
                        description=f"Position: {title} at {company.capitalize()}.\nLocation: {loc or 'Not specified'}.",
                        url=job.get("absolute_url"),
                        posted_at=posted_date,
                        collected_at=datetime.now(timezone.utc),
                    )
                )
        except Exception as e:
            logger.debug(f"Greenhouse board fetch failed for {company}: {e}")
        return results

    async def search(self, query: JobSearchQuery) -> List[RawJobListing]:
        """Fetch matching openings from configured public company career feeds."""
        logger.info(f"CompanyCareerSource searching career feeds for '{query.role}'")
        collected: List[RawJobListing] = []

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                for company in self.target_companies[:3]:  # Concurrency limit
                    listings = await self._fetch_greenhouse_board(client, company, query.role)
                    collected.extend(listings)
                    if len(collected) >= (query.limit or 20):
                        break
        except Exception as e:
            logger.warning(f"CompanyCareerSource error: {e}")

        logger.info(f"CompanyCareerSource retrieved {len(collected)} company listings")
        return collected
