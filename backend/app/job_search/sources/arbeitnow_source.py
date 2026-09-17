from datetime import datetime, timezone
import re
from typing import List, Optional
import httpx

from app.core.config import settings
from app.core.logging import logger
from app.job_search.base import JobSource
from app.job_search.schemas import JobSearchQuery, RawJobListing


class ArbeitnowJobSource(JobSource):
    """
    Adapter for the official Arbeitnow Job Board REST API.
    Public developer feed providing legitimate EU, tech, and remote openings
    without scraping or authentication bypass.
    Endpoint: https://www.arbeitnow.com/api/job-board-api
    """
    source_name = "arbeitnow"

    def __init__(self, api_url: Optional[str] = None):
        self.api_url = api_url or "https://www.arbeitnow.com/api/job-board-api"
        self.timeout = float(settings.JOB_SEARCH_TIMEOUT_SECONDS)

    async def search(self, query: JobSearchQuery) -> List[RawJobListing]:
        """Query official Arbeitnow feed and return normalized listings."""
        logger.info(f"ArbeitnowJobSource querying {self.api_url} for '{query.role}'")

        headers = {
            "User-Agent": "AI-Resume-Analyzer-JobAgent/1.0 (+https://github.com/Samarth-Satoddi/RESUME-ANALYSER-)",
            "Accept": "application/json",
        }

        results: List[RawJobListing] = []
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(self.api_url, headers=headers)
                if response.status_code != 200:
                    logger.warning(f"ArbeitnowJobSource received HTTP {response.status_code}")
                    return []

                payload = response.json()
                items = payload.get("data", []) if isinstance(payload, dict) else []

                # Filter keywords
                filter_terms = [w.lower() for w in query.role.split() if len(w) > 2]

                for item in items:
                    title = item.get("title", "")
                    description = item.get("description", "")
                    tags = [t.lower() for t in item.get("tags", [])]
                    title_lower = title.lower()
                    desc_lower = description.lower()

                    # Keyword match check
                    if filter_terms:
                        matches_title = any(t in title_lower for t in filter_terms)
                        matches_tags = any(any(t in tag for t in filter_terms) for tag in tags)
                        matches_desc = any(t in desc_lower for t in filter_terms)
                        if not (matches_title or matches_tags or matches_desc):
                            continue

                    # Location filter if specified
                    loc = item.get("location", "")
                    is_remote = bool(item.get("remote", False))
                    if query.remote and not is_remote:
                        continue

                    # Posted date parsing
                    posted_date = None
                    created_at_val = item.get("created_at")
                    if created_at_val:
                        try:
                            if isinstance(created_at_val, (int, float)):
                                posted_date = datetime.fromtimestamp(created_at_val, tz=timezone.utc)
                            else:
                                posted_date = datetime.fromisoformat(str(created_at_val).replace("Z", "+00:00"))
                        except Exception:
                            posted_date = None

                    # Clean description text from HTML tags if HTML is present
                    clean_desc = re.sub(r"<[^>]+>", " ", description)
                    clean_desc = re.sub(r"\s+", " ", clean_desc).strip()

                    slug = item.get("slug") or str(item.get("created_at", ""))
                    job_url = item.get("url")

                    results.append(
                        RawJobListing(
                            external_id=str(slug),
                            source="arbeitnow",
                            title=title,
                            company=item.get("company_name", "Unknown"),
                            location=loc or ("Remote" if is_remote else "Global"),
                            remote_type="remote" if is_remote else None,
                            employment_type=item.get("job_types", ["full-time"])[0] if item.get("job_types") else "full-time",
                            salary_min=None,
                            salary_max=None,
                            currency=None,
                            description=clean_desc,
                            url=job_url,
                            posted_at=posted_date,
                            collected_at=datetime.now(timezone.utc),
                        )
                    )

                    if len(results) >= (query.limit or 25):
                        break

            logger.info(f"ArbeitnowJobSource retrieved {len(results)} matching listings")
        except httpx.TimeoutException:
            logger.warning(f"ArbeitnowJobSource timed out after {self.timeout}s")
        except Exception as e:
            logger.warning(f"ArbeitnowJobSource error: {e}")

        return results
