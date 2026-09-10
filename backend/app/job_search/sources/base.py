from typing import Dict, List, Type
from app.job_search.base import JobSource


class SourceRegistry:
    """Registry managing available job source adapters."""
    _sources: Dict[str, JobSource] = {}

    @classmethod
    def register(cls, source: JobSource) -> None:
        cls._sources[source.source_name] = source

    @classmethod
    def get_source(cls, name: str) -> JobSource:
        return cls._sources.get(name)

    @classmethod
    def get_all_enabled(cls) -> List[JobSource]:
        return [s for s in cls._sources.values() if s.is_enabled]
