import hashlib
import html
import re
from typing import Optional, Tuple
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from app.job_search.schemas import NormalizedJobListing, RawJobListing


class JobNormalizer:
    """
    Sanitizes, validates, and normalizes raw job listings from heterogeneous sources
    into consistent internal representations without ever fabricating missing fields.
    """

    TITLE_NOISE_REGEX = re.compile(
        r"(?:\[(?:remote|hybrid|onsite|contract|full[- ]time|urgent)\]|\((?:m/w/d|f/m/d|remote|hybrid|h/f)\)|[-–/]\s*(?:req|job ID|remote|id)[\s\d\w#-]*$)",
        re.IGNORECASE,
    )

    SAFE_SCHEMES = {"http", "https"}
    TRACKING_PARAMS = {
        "utm_source", "utm_medium", "utm_campaign", "utm_term",
        "utm_content", "fbclid", "gclid", "ref", "_hsenc", "_hsmi",
    }

    @classmethod
    def sanitize_url(cls, url: Optional[str]) -> Optional[str]:
        """
        Validate URL safety: strictly permit only http and https protocols.
        Reject javascript:, data:, file:, etc.
        Canonicalize URL by stripping marketing tracking parameters while preserving job IDs.
        """
        if not url or not isinstance(url, str):
            return None
        cleaned = url.strip()
        try:
            parsed = urlparse(cleaned)
            if parsed.scheme.lower() not in cls.SAFE_SCHEMES or not parsed.netloc:
                return None

            # Strip tracking parameters while retaining job parameters
            query_dict = parse_qs(parsed.query, keep_blank_values=False)
            filtered_query = {
                k: v for k, v in query_dict.items()
                if k.lower() not in cls.TRACKING_PARAMS
            }
            clean_query = urlencode(filtered_query, doseq=True)

            canonical = urlunparse((
                parsed.scheme.lower(),
                parsed.netloc.lower(),
                parsed.path.rstrip("/") if parsed.path != "/" else "/",
                parsed.params,
                clean_query,
                "",  # strip fragments
            ))
            return canonical
        except Exception:
            return None

    @classmethod
    def format_source_display(cls, source: str) -> str:
        """Map internal source keys to clean, user-facing branded names."""
        s = (source or "").lower()
        if "greenhouse" in s:
            return "Greenhouse"
        elif "remotive" in s:
            return "Remotive"
        elif "arbeitnow" in s:
            return "Arbeitnow"
        elif "mock" in s:
            return "Development Data"
        return source.capitalize() if source else "External"

    @classmethod
    def normalize_title(cls, title: str) -> str:
        """Standardize title formatting and strip extraneous tags."""
        if not title:
            return "Untitled Opportunity"
        cleaned = html.unescape(title)
        cleaned = cls.TITLE_NOISE_REGEX.sub("", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        cleaned = cleaned.strip("-–/|:,")
        return cleaned.strip() or "Untitled Opportunity"

    @classmethod
    def normalize_company(cls, company: Optional[str]) -> Optional[str]:
        """Clean company name whitespace and formatting."""
        if not company:
            return None
        cleaned = html.unescape(company).strip()
        cleaned = re.sub(r"\s+", " ", cleaned)
        return cleaned or None

    @classmethod
    def normalize_location_and_remote(
        cls,
        location: Optional[str],
        title: str,
        raw_remote: Optional[str],
    ) -> Tuple[Optional[str], str]:
        """
        Classify remote work model and clean location string.
        Returns: (normalized_location, remote_type: 'remote' | 'hybrid' | 'on-site' | 'unknown')
        """
        combined = f"{location or ''} {title} {raw_remote or ''}".lower()

        if "hybrid" in combined:
            remote_type = "hybrid"
        elif "remote" in combined or "work from home" in combined or "anywhere" in combined or "worldwide" in combined:
            remote_type = "remote"
        elif "on-site" in combined or "onsite" in combined or "in-office" in combined:
            remote_type = "on-site"
        elif location:
            remote_type = "on-site"
        else:
            remote_type = "unknown"

        cleaned_loc = None
        if location:
            cleaned_loc = re.sub(r"\s+", " ", location).strip()
            if cleaned_loc.lower() in {"remote", "anywhere", "work from home", "worldwide"}:
                cleaned_loc = "Remote"

        return cleaned_loc, remote_type

    @classmethod
    def normalize_employment_type(cls, raw_type: Optional[str]) -> Optional[str]:
        """Normalize employment types to standard canonical values."""
        if not raw_type:
            return None
        t = raw_type.lower()
        if "full" in t:
            return "full-time"
        if "part" in t:
            return "part-time"
        if "contract" in t or "freelance" in t:
            return "contract"
        if "intern" in t:
            return "internship"
        return raw_type.strip()

    @classmethod
    def sanitize_description(cls, desc: str) -> str:
        """Strip HTML tags while preserving line breaks and basic formatting."""
        if not desc:
            return ""
        text = re.sub(r"<(?:br\s*/?|/p|/li)>", "\n", desc, flags=re.IGNORECASE)
        text = re.sub(r"<[^>]+>", "", text)
        text = html.unescape(text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    @classmethod
    def compute_dedup_hash(
        cls,
        company: Optional[str],
        title: str,
        location: Optional[str],
        canonical_url: Optional[str] = None,
    ) -> str:
        """Compute deterministic fingerprint for deduplication."""
        c = (company or "").lower().strip()
        t = re.sub(r"[^a-z0-9]", "", title.lower())
        l = (location or "").lower().strip()
        u = (canonical_url or "").lower().strip()
        raw_key = f"{c}|{t}|{l}|{u}"
        return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

    @classmethod
    def normalize(cls, raw: RawJobListing) -> NormalizedJobListing:
        """Convert a RawJobListing into a NormalizedJobListing."""
        norm_title = cls.normalize_title(raw.title)
        norm_company = cls.normalize_company(raw.company)
        norm_loc, remote_type = cls.normalize_location_and_remote(
            raw.location,
            norm_title,
            raw.remote_type,
        )
        safe_url = cls.sanitize_url(raw.url)
        clean_desc = cls.sanitize_description(raw.description)
        emp_type = cls.normalize_employment_type(raw.employment_type)
        dedup_hash = cls.compute_dedup_hash(norm_company, norm_title, norm_loc, safe_url)
        display_source = cls.format_source_display(raw.source)

        # Validate salary ranges
        sal_min = raw.salary_min
        sal_max = raw.salary_max
        if sal_min is not None and sal_max is not None and sal_min > sal_max:
            sal_min, sal_max = sal_max, sal_min

        return NormalizedJobListing(
            external_id=raw.external_id,
            source=display_source,
            title=norm_title,
            company=norm_company,
            location=norm_loc,
            remote_type=remote_type,
            employment_type=emp_type,
            salary_min=sal_min,
            salary_max=sal_max,
            currency=raw.currency,
            description=clean_desc,
            url=safe_url,
            posted_at=raw.posted_at,
            collected_at=raw.collected_at,
            dedup_hash=dedup_hash,
        )
