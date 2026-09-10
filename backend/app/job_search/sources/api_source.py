from datetime import datetime, timezone
from typing import List, Optional
import httpx

from app.core.config import settings
from app.core.logging import logger
from app.job_search.base import JobSource
from app.job_search.schemas import JobSearchQuery, RawJobListing


class ApiJobSource(JobSource):
    """
    Adapter for official job board REST APIs.
    Supports Remotive / Arbeitnow public developer APIs or custom enterprise endpoints
    configured through environment variables. Never bypasses authentication or rate limits.
    """
    source_name = "api_source"

    def __init__(self, api_url: Optional[str] = None, api_key: Optional[str] = None):
        self.api_url = api_url or settings.JOB_SEARCH_API_URL or "https://remotive.com/api/remote-jobs"
        self.api_key = api_key or settings.JOB_SEARCH_API_KEY
        self.timeout = float(settings.JOB_SEARCH_TIMEOUT_SECONDS)

    async def search(self, query: JobSearchQuery) -> List[RawJobListing]:
        """Query legitimate job API and map results into RawJobListing records."""
        logger.info(f"ApiJobSource querying {self.api_url} for '{query.role}'")

        params = {
            "search": query.role,
            "limit": min(query.limit or 25, 50),
        }

        headers = {
            "User-Agent": "AI-Resume-Analyzer-JobAgent/1.0",
            "Accept": "application/json",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        results: List[RawJobListing] = []

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(self.api_url, params=params, headers=headers)
                if response.status_code != 200:
                    logger.warning(f"ApiJobSource received status {response.status_code} from {self.api_url}")
                    return []

                payload = response.json()
                jobs_data = payload.get("jobs", []) if isinstance(payload, dict) else payload

                for item in jobs_data[:query.limit]:
                    posted_date = None
                    pub_str = item.get("publication_date") or item.get("posted_at")
                    if pub_str:
                        try:
                            posted_date = datetime.fromisoformat(pub_str.replace("Z", "+00:00"))
                        except Exception:
                            posted_date = None

                    results.append(
                        RawJobListing(
                            external_id=str(item.get("id", "")),
                            source="remotive_api" if "remotive" in self.api_url else "external_api",
                            title=item.get("title", ""),
                            company=item.get("company_name") or item.get("company"),
                            location=item.get("candidate_required_location") or item.get("location"),
                            remote_type="remote" if item.get("job_type") == "remote" or "remotive" in self.api_url else None,
                            employment_type=item.get("job_type"),
                            salary_min=None,
                            salary_max=None,
                            currency=None,
                            description=item.get("description", ""),
                            url=item.get("url"),
                            posted_at=posted_date,
                            collected_at=datetime.now(timezone.utc),
                        )
                    )

            logger.info(f"ApiJobSource retrieved {len(results)} listings")
        except httpx.TimeoutException:
            logger.warning(f"ApiJobSource request timed out after {self.timeout}s")
        except Exception as e:
            logger.warning(f"ApiJobSource search error: {e}")

        return results
