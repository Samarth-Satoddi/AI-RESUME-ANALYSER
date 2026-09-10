from abc import ABC, abstractmethod
from typing import List
from app.job_search.schemas import JobSearchQuery, RawJobListing


class JobSource(ABC):
    """
    Standard interface for all job discovery source adapters.
    Whether querying an official REST API, public search provider,
    company career page feed, or local mock data, all sources return RawJobListings.
    """
    source_name: str = "base_source"
    is_enabled: bool = True

    @abstractmethod
    async def search(self, query: JobSearchQuery) -> List[RawJobListing]:
        """
        Execute search query against the source provider.
        Must never bypass CAPTCHA, bot detection, or scrape prohibited pages.
        Must return RawJobListings with only known data, never fabricating missing attributes.
        """
        pass
