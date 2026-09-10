from datetime import datetime, timedelta, timezone
import pytest

from app.job_search.deduplicator import JobDeduplicator
from app.job_search.normalizer import JobNormalizer
from app.job_search.ranking import JobRankingEngine
from app.job_search.schemas import JobSearchQuery, NormalizedJobListing, RawJobListing
from app.job_search.sources.base import SourceRegistry
from app.job_search.sources.mock_source import MockJobSource


def test_normalizer_title_sanitization():
    """Verify title noise and tags are cleanly stripped without altering core title."""
    assert JobNormalizer.normalize_title("[REMOTE] Senior Python Engineer (f/m/d)") == "Senior Python Engineer"
    assert JobNormalizer.normalize_title("Backend Developer - Req-12948") == "Backend Developer"
    assert JobNormalizer.normalize_title("Full Stack Developer [Contract]") == "Full Stack Developer"
    assert JobNormalizer.normalize_title("") == "Untitled Opportunity"


def test_normalizer_url_safety():
    """Verify strict URL validation accepts http/https and rejects malicious protocols."""
    assert JobNormalizer.sanitize_url("https://example.com/jobs/123") == "https://example.com/jobs/123"
    assert JobNormalizer.sanitize_url("http://jobs.company.org/view") == "http://jobs.company.org/view"
    # Reject dangerous protocols
    assert JobNormalizer.sanitize_url("javascript:alert(1)") is None
    assert JobNormalizer.sanitize_url("file:///etc/passwd") is None
    assert JobNormalizer.sanitize_url("data:text/html;base64,PHNjcmlwdD5hbGVydCgxKTwvc2NyaXB0Pg==") is None
    assert JobNormalizer.sanitize_url("/relative/path") is None
    assert JobNormalizer.sanitize_url(None) is None


def test_normalizer_location_and_remote_classification():
    """Verify location string normalization and remote type classification."""
    loc, remote_type = JobNormalizer.normalize_location_and_remote("Bangalore, India", "Backend Engineer", None)
    assert loc == "Bangalore, India"
    assert remote_type == "on-site"

    loc, remote_type = JobNormalizer.normalize_location_and_remote("Remote", "Python Developer", None)
    assert loc == "Remote"
    assert remote_type == "remote"

    loc, remote_type = JobNormalizer.normalize_location_and_remote("London, UK", "Hybrid Python Engineer", None)
    assert remote_type == "hybrid"


def test_normalizer_salary_validation():
    """Verify salary ranges are ordered and negative values handled."""
    raw = RawJobListing(
        source="test",
        title="Software Engineer",
        description="Write code.",
        salary_min=120000.0,
        salary_max=90000.0,  # inverted
    )
    norm = JobNormalizer.normalize(raw)
    assert norm.salary_min == 90000.0
    assert norm.salary_max == 120000.0


def test_normalizer_description_html_sanitization():
    """Verify HTML tags in descriptions are converted to clean plain text."""
    raw = "<p>Responsibilities: <br/>• Build APIs.<br/>• Manage DB.</p><script>evil()</script>"
    clean = JobNormalizer.sanitize_description(raw)
    assert "<p>" not in clean
    assert "<script>" not in clean
    assert "Build APIs." in clean


def test_deduplicator_canonical_urls():
    """Verify tracking parameters are stripped during URL canonicalization."""
    url1 = "https://example.com/job/123?utm_source=linkedin&utm_medium=job_board&ref=aggregator"
    url2 = "https://example.com/job/123"
    assert JobDeduplicator.canonicalize_url(url1) == JobDeduplicator.canonicalize_url(url2)


def test_deduplicator_filters_duplicates():
    """Verify duplicate listings with identical URLs or fingerprints are pruned."""
    now = datetime.now(timezone.utc)
    item1 = NormalizedJobListing(
        external_id="ext-1",
        source="source_a",
        title="Python Developer",
        company="TechCorp",
        location="Remote",
        remote_type="remote",
        description="Build Python web services.",
        url="https://example.com/job/1?utm_source=twitter",
        collected_at=now,
        dedup_hash="hash1",
    )
    # Duplicate with same canonical URL from source B
    item2 = NormalizedJobListing(
        external_id="ext-2",
        source="source_b",
        title="Python Developer",
        company="TechCorp",
        location="Remote",
        remote_type="remote",
        description="Build Python web services.",
        url="https://example.com/job/1?ref=jobboard",
        collected_at=now,
        dedup_hash="hash1",
    )
    # Distinct job
    item3 = NormalizedJobListing(
        external_id="ext-3",
        source="source_a",
        title="DevOps Engineer",
        company="TechCorp",
        location="Remote",
        remote_type="remote",
        description="Manage Kubernetes clusters.",
        url="https://example.com/job/2",
        collected_at=now,
        dedup_hash="hash2",
    )

    deduped = JobDeduplicator.deduplicate([item1, item2, item3])
    assert len(deduped) == 2
    assert deduped[0].title == "Python Developer"
    assert deduped[1].title == "DevOps Engineer"


def test_ranking_engine_calculation():
    """Verify multi-factor composite ranking formula and freshness penalty constraint."""
    # Excellent match with slightly older date
    score_high = JobRankingEngine.compute_rank_score(
        overall_match=92.0,
        skill_score=95.0,
        location_fit=100.0,
        freshness_score=70.0,
    )
    assert score_high >= 85.0

    # Low match (< 50) must not be elevated by freshness
    score_low = JobRankingEngine.compute_rank_score(
        overall_match=30.0,
        skill_score=20.0,
        location_fit=100.0,
        freshness_score=100.0,
    )
    assert score_low <= 30.0  # Capped at overall_match for low matches


def test_ranking_engine_ordering():
    """Verify opportunities are ordered from best match to lowest match."""
    items = [
        {"overall_match_score": 55.0, "skill_score": 60.0, "location": "New York", "remote_type": "on-site", "posted_at": None},
        {"overall_match_score": 90.0, "skill_score": 95.0, "location": "Bangalore", "remote_type": "remote", "posted_at": None},
        {"overall_match_score": 75.0, "skill_score": 70.0, "location": "Bangalore", "remote_type": "hybrid", "posted_at": None},
    ]
    ranked = JobRankingEngine.rank_opportunities(items, user_location="Bangalore", user_remote=True)
    assert ranked[0]["overall_match_score"] == 90.0
    assert ranked[0]["rank"] == 1
    assert ranked[1]["overall_match_score"] == 75.0
    assert ranked[1]["rank"] == 2
    assert ranked[2]["overall_match_score"] == 55.0
    assert ranked[2]["rank"] == 3


def test_mock_job_source_returns_data():
    """Verify MockJobSource yields valid, populated RawJobListings."""
    import asyncio
    src = MockJobSource()
    query = JobSearchQuery(role="Python Developer", location="Bangalore", remote=True, limit=5)
    results = asyncio.run(src.search(query))
    assert len(results) > 0
    assert "Python" in results[0].title or "Developer" in results[0].title
    assert results[0].description
    assert results[0].url.startswith("http")
