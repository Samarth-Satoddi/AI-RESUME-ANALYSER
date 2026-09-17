from app.job_search.sources.base import SourceRegistry
from app.job_search.sources.api_source import RemotiveJobSource, ApiJobSource
from app.job_search.sources.company_source import GreenhouseJobSource, CompanyCareerSource
from app.job_search.sources.arbeitnow_source import ArbeitnowJobSource
from app.job_search.sources.search_source import SearchProviderJobSource
from app.job_search.sources.mock_source import MockJobSource

# Register production external sources
greenhouse = GreenhouseJobSource()
remotive = RemotiveJobSource()
arbeitnow = ArbeitnowJobSource()
search_provider = SearchProviderJobSource()
mock_src = MockJobSource()

# Canonical keys
SourceRegistry.register(greenhouse)
SourceRegistry.register(remotive)
SourceRegistry.register(arbeitnow)
SourceRegistry.register(search_provider)
SourceRegistry.register(mock_src)

# Legacy alias mappings for backward compatibility
SourceRegistry._sources["company_careers"] = greenhouse
SourceRegistry._sources["api_source"] = remotive
SourceRegistry._sources["mock"] = mock_src
SourceRegistry._sources["mock_source"] = mock_src

__all__ = [
    "SourceRegistry",
    "GreenhouseJobSource",
    "RemotiveJobSource",
    "ArbeitnowJobSource",
    "SearchProviderJobSource",
    "MockJobSource",
    "CompanyCareerSource",
    "ApiJobSource",
]
