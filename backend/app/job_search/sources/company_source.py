from datetime import datetime, timezone
import html
import re
from typing import List, Optional
import httpx

from app.core.config import settings
from app.core.logging import logger
from app.job_search.base import JobSource
from app.job_search.schemas import JobSearchQuery, RawJobListing


class GreenhouseJobSource(JobSource):
    """
    Adapter for official Greenhouse Job Board public API.
    Queries official Greenhouse boards (such as Canonical, GitLab, Stripe)
    fetching complete job descriptions via '?content=true' without scraping or bot circumvention.
    Endpoint: https://boards-api.greenhouse.io/v1/boards/{company}/jobs?content=true
    """
    source_name = "greenhouse"

    # Leading tech employers with active, open Greenhouse boards
    POPULAR_COMPANIES = ["canonical", "gitlab", "stripe"]

    def __init__(self, target_companies: Optional[List[str]] = None):
        self.target_companies = target_companies or self.POPULAR_COMPANIES
        self.timeout = float(settings.JOB_SEARCH_TIMEOUT_SECONDS)

    async def _fetch_greenhouse_board(self, client: httpx.AsyncClient, company: str, query: JobSearchQuery) -> List[RawJobListing]:
        """Query official Greenhouse board API with full job content."""
        url = f"https://boards-api.greenhouse.io/v1/boards/{company}/jobs?content=true"
        results: List[RawJobListing] = []
        try:
            resp = await client.get(url, headers={"User-Agent": "AI-Resume-Analyzer-JobAgent/1.0"})
            if resp.status_code != 200:
                logger.warning(f"Greenhouse board for '{company}' returned status {resp.status_code}")
                return []

            data = resp.json()
            jobs = data.get("jobs", [])

            filter_terms = [w.lower() for w in query.role.split() if len(w) > 2]

            for job in jobs:
                title = job.get("title", "")
                title_lower = title.lower()

                # Filter by keyword relevance
                if filter_terms and not any(t in title_lower for t in filter_terms):
                    continue

                # Location filter if specified
                loc = job.get("location", {}).get("name") if isinstance(job.get("location"), dict) else None
                is_remote = bool(loc and ("remote" in loc.lower() or "worldwide" in loc.lower() or "home based" in loc.lower()))
                if query.remote and not is_remote:
                    continue

                updated_at_str = job.get("updated_at")
                posted_date = None
                if updated_at_str:
                    try:
                        posted_date = datetime.fromisoformat(updated_at_str.replace("Z", "+00:00"))
                    except Exception:
                        posted_date = None

                # Clean complete HTML description to structured text
                raw_html = job.get("content") or ""
                decoded_html = html.unescape(raw_html)
                clean_desc = re.sub(r"<[^>]+>", " ", decoded_html)
                clean_desc = re.sub(r"\s+", " ", clean_desc).strip()
                if not clean_desc:
                    clean_desc = f"Position: {title} at {company.capitalize()}.\nLocation: {loc or 'Not specified'}."

                job_id = str(job.get("id"))
                original_url = job.get("absolute_url") or f"https://job-boards.greenhouse.io/{company}/jobs/{job_id}"

                results.append(
                    RawJobListing(
                        external_id=f"{company}-{job_id}",
                        source="greenhouse",
                        title=title,
                        company=company.capitalize(),
                        location=loc or ("Remote" if is_remote else "Worldwide"),
                        remote_type="remote" if is_remote else None,
                        employment_type="full-time",
                        salary_min=None,
                        salary_max=None,
                        currency=None,
                        description=clean_desc,
                        url=original_url,
                        posted_at=posted_date,
                        collected_at=datetime.now(timezone.utc),
                    )
                )

                if len(results) >= (query.limit or 20):
                    break
        except Exception as e:
            logger.warning(f"Greenhouse board fetch failed for {company}: {e}")
        return results

    async def search(self, query: JobSearchQuery) -> List[RawJobListing]:
        """Fetch matching openings from configured public company career feeds."""
        logger.info(f"GreenhouseJobSource searching career feeds for '{query.role}'")
        collected: List[RawJobListing] = []

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                for company in self.target_companies:
                    listings = await self._fetch_greenhouse_board(client, company, query)
                    collected.extend(listings)
                    if len(collected) >= (query.limit or 25):
                        break
        except Exception as e:
            logger.warning(f"GreenhouseJobSource error: {e}")

        logger.info(f"GreenhouseJobSource retrieved {len(collected)} company listings")
        return collected


# Backward-compatible alias
CompanyCareerSource = GreenhouseJobSource
