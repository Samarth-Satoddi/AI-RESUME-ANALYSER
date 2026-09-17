from datetime import datetime, timezone
import html
import re
from typing import List, Optional
import httpx

from app.core.config import settings
from app.core.logging import logger
from app.job_search.base import JobSource
from app.job_search.schemas import JobSearchQuery, RawJobListing


class RemotiveJobSource(JobSource):
    """
    Adapter for official Remotive developer REST API.
    Public developer feed providing legitimate remote developer and technology openings
    without web scraping or bot circumvention.
    Endpoint: https://remotive.com/api/remote-jobs
    """
    source_name = "remotive"

    def __init__(self, api_url: Optional[str] = None, api_key: Optional[str] = None):
        self.api_url = api_url or settings.JOB_SEARCH_API_URL or "https://remotive.com/api/remote-jobs"
        self.api_key = api_key or settings.JOB_SEARCH_API_KEY
        self.timeout = float(settings.JOB_SEARCH_TIMEOUT_SECONDS)

    async def search(self, query: JobSearchQuery) -> List[RawJobListing]:
        """Query legitimate Remotive API and map results into RawJobListing records."""
        logger.info(f"RemotiveJobSource querying {self.api_url} for '{query.role}'")

        params = {
            "search": query.role,
            "limit": min(query.limit or 25, 50),
        }

        headers = {
            "User-Agent": "AI-Resume-Analyzer-JobAgent/1.0 (+https://github.com/Samarth-Satoddi/RESUME-ANALYSER-)",
            "Accept": "application/json",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        results: List[RawJobListing] = []

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(self.api_url, params=params, headers=headers)
                if response.status_code != 200:
                    logger.warning(f"RemotiveJobSource received status {response.status_code} from {self.api_url}")
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

                    raw_desc = item.get("description", "")
                    clean_desc = re.sub(r"<[^>]+>", " ", html.unescape(raw_desc))
                    clean_desc = re.sub(r"\s+", " ", clean_desc).strip()

                    raw_salary = item.get("salary") or ""
                    salary_min, salary_max = None, None
                    if raw_salary:
                        numbers = [float(n.replace(",", "")) for n in re.findall(r"\d[\d,]*", raw_salary)]
                        if len(numbers) >= 2:
                            salary_min, salary_max = numbers[0], numbers[1]
                        elif len(numbers) == 1:
                            salary_min = numbers[0]

                    results.append(
                        RawJobListing(
                            external_id=str(item.get("id", "")),
                            source="remotive",
                            title=item.get("title", ""),
                            company=item.get("company_name") or item.get("company") or "Unknown",
                            location=item.get("candidate_required_location") or "Remote",
                            remote_type="remote",
                            employment_type=item.get("job_type") or "full-time",
                            salary_min=salary_min,
                            salary_max=salary_max,
                            currency="USD" if "$" in raw_salary else None,
                            description=clean_desc,
                            url=item.get("url"),
                            posted_at=posted_date,
                            collected_at=datetime.now(timezone.utc),
                        )
                    )

            logger.info(f"RemotiveJobSource retrieved {len(results)} listings")
        except httpx.TimeoutException:
            logger.warning(f"RemotiveJobSource request timed out after {self.timeout}s")
        except Exception as e:
            logger.warning(f"RemotiveJobSource search error: {e}")

        return results


# Backward-compatible alias
ApiJobSource = RemotiveJobSource
