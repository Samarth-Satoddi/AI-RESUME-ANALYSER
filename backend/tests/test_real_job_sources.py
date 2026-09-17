import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timezone
import httpx

from app.core.config import settings
from app.job_search.schemas import JobSearchQuery
from app.job_search.sources.arbeitnow_source import ArbeitnowJobSource
from app.job_search.sources.company_source import GreenhouseJobSource
from app.job_search.sources.api_source import RemotiveJobSource
from app.job_search.normalizer import JobNormalizer
from app.job_search.agent import JobSearchAgent


@pytest.mark.anyio
async def test_arbeitnow_source_success():
    source = ArbeitnowJobSource()
    fake_payload = {
        "data": [
            {
                "slug": "python-backend-engineer-munich-123",
                "title": "Python Backend Engineer",
                "company_name": "Datatech GmbH",
                "location": "Munich, Germany",
                "remote": True,
                "url": "https://www.arbeitnow.com/jobs/companies/datatech/python-backend-engineer-123",
                "tags": ["Python", "FastAPI", "Docker"],
                "job_types": ["full-time"],
                "description": "<p>Build high-throughput <strong>Python</strong> microservices.</p>",
                "created_at": 1725900000,
            }
        ]
    }

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = fake_payload

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_resp

        query = JobSearchQuery(role="Python Engineer", limit=10)
        listings = await source.search(query)

        assert len(listings) == 1
        job = listings[0]
        assert job.title == "Python Backend Engineer"
        assert job.company == "Datatech GmbH"
        assert job.source == "arbeitnow"
        assert job.remote_type == "remote"
        assert "Python" in job.description
        assert "<p>" not in job.description  # HTML stripped
        assert job.url == "https://www.arbeitnow.com/jobs/companies/datatech/python-backend-engineer-123"


@pytest.mark.anyio
async def test_greenhouse_source_success():
    source = GreenhouseJobSource(target_companies=["canonical"])
    fake_payload = {
        "jobs": [
            {
                "id": 889900,
                "title": "Senior Python Engineer - Systems",
                "location": {"name": "Home based - Worldwide"},
                "updated_at": "2026-09-01T12:00:00Z",
                "absolute_url": "https://job-boards.greenhouse.io/canonical/jobs/889900",
                "content": "<div><p>We are hiring a Senior Python Engineer to work on distributed Linux tooling.</p></div>",
            }
        ]
    }

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = fake_payload

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_resp

        query = JobSearchQuery(role="Python Engineer", limit=10)
        listings = await source.search(query)

        assert len(listings) == 1
        job = listings[0]
        assert job.title == "Senior Python Engineer - Systems"
        assert job.company == "Canonical"
        assert job.source == "greenhouse"
        assert job.remote_type == "remote"
        assert "Senior Python Engineer" in job.description
        assert job.url == "https://job-boards.greenhouse.io/canonical/jobs/889900"


@pytest.mark.anyio
async def test_remotive_source_success():
    source = RemotiveJobSource()
    fake_payload = {
        "jobs": [
            {
                "id": 776655,
                "title": "Backend Python Developer",
                "company_name": "CloudNova Labs",
                "candidate_required_location": "USA / Remote",
                "job_type": "full_time",
                "salary": "$110,000 - $140,000",
                "publication_date": "2026-09-05T08:00:00",
                "url": "https://remotive.com/remote-jobs/software-dev/backend-python-developer-776655",
                "description": "<p>Developing async REST APIs with FastAPI and PostgreSQL.</p>",
            }
        ]
    }

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = fake_payload

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_resp

        query = JobSearchQuery(role="Python Developer", limit=10)
        listings = await source.search(query)

        assert len(listings) == 1
        job = listings[0]
        assert job.title == "Backend Python Developer"
        assert job.company == "CloudNova Labs"
        assert job.source == "remotive"
        assert job.salary_min == 110000.0
        assert job.salary_max == 140000.0
        assert job.currency == "USD"
        assert job.url == "https://remotive.com/remote-jobs/software-dev/backend-python-developer-776655"


def test_url_security_and_canonicalization():
    # Safe HTTPS URL with tracking params
    dirty_url = "https://job-boards.greenhouse.io/canonical/jobs/12345?utm_source=linkedin&utm_campaign=hiring&gh_jid=12345"
    clean_url = JobNormalizer.sanitize_url(dirty_url)
    assert clean_url is not None
    assert "utm_source" not in clean_url
    assert "utm_campaign" not in clean_url
    assert "gh_jid=12345" in clean_url

    # Malicious or dangerous schemes rejected
    assert JobNormalizer.sanitize_url("javascript:alert('pwn')") is None
    assert JobNormalizer.sanitize_url("file:///etc/passwd") is None
    assert JobNormalizer.sanitize_url("data:text/html;base64,PHNjcmlwdD4=") is None
    assert JobNormalizer.sanitize_url("vbscript:msgbox(1)") is None
    assert JobNormalizer.sanitize_url("") is None


def test_format_source_display():
    assert JobNormalizer.format_source_display("greenhouse") == "Greenhouse"
    assert JobNormalizer.format_source_display("greenhouse:canonical") == "Greenhouse"
    assert JobNormalizer.format_source_display("remotive") == "Remotive"
    assert JobNormalizer.format_source_display("arbeitnow") == "Arbeitnow"
    assert JobNormalizer.format_source_display("mock_source") == "Development Data"


@pytest.mark.anyio
async def test_strict_no_mock_fallback_when_external_sources_fail(monkeypatch):
    """Verify that when external sources are enabled and fail, mock data is strictly NEVER returned."""
    monkeypatch.setattr(settings, "JOB_SEARCH_SOURCES", "greenhouse,remotive,arbeitnow")

    mock_resp = MagicMock()
    mock_resp.status_code = 500

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_resp

        query = JobSearchQuery(role="Python Backend Developer", limit=10)
        raw_listings, errors, sources_queried = await JobSearchAgent.fetch_from_sources([query])

        # Must return empty list - NO fake/mock fallback
        assert raw_listings == []
        for item in raw_listings:
            assert "mock" not in item.source.lower()
