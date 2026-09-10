from app.job_search.sources.base import SourceRegistry
from app.job_search.sources.api_source import ApiJobSource
from app.job_search.sources.search_source import SearchProviderJobSource
from app.job_search.sources.company_source import CompanyCareerSource
from app.job_search.sources.mock_source import MockJobSource

# Register default sources
SourceRegistry.register(MockJobSource())
SourceRegistry.register(ApiJobSource())
SourceRegistry.register(CompanyCareerSource())
SourceRegistry.register(SearchProviderJobSource())

__all__ = [
    "SourceRegistry",
    "ApiJobSource",
    "SearchProviderJobSource",
    "CompanyCareerSource",
    "MockJobSource",
]
