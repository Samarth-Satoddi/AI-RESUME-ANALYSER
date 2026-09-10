import re
from typing import List, Set
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from app.core.logging import logger
from app.job_search.schemas import NormalizedJobListing


class JobDeduplicator:
    """
    Multi-signal deduplication engine to filter duplicate job postings
    discovered across multiple aggregators, APIs, and company pages.
    """

    # Query parameters commonly used for tracking and affiliate routing
    TRACKING_PARAMS = {
        "utm_source",
        "utm_medium",
        "utm_campaign",
        "utm_term",
        "utm_content",
        "ref",
        "source",
        "affiliate",
        "click_id",
        "tracking",
    }

    @classmethod
    def canonicalize_url(cls, raw_url: str) -> str:
        """Strip tracking tokens and normalizes URL for canonical comparison."""
        if not raw_url:
            return ""
        try:
            parsed = urlparse(raw_url.strip())
            netloc = parsed.netloc.lower()
            if netloc.startswith("www."):
                netloc = netloc[4:]

            query_params = parse_qs(parsed.query, keep_blank_values=False)
            filtered_query = {
                k: v for k, v in query_params.items()
                if k.lower() not in cls.TRACKING_PARAMS
            }

            path = parsed.path.rstrip("/")

            canonical = urlunparse((
                parsed.scheme.lower(),
                netloc,
                path,
                "",  # params
                urlencode(filtered_query, doseq=True),
                "",  # fragment
            ))
            return canonical
        except Exception:
            return raw_url.strip().lower()

    @classmethod
    def compute_text_similarity(cls, text1: str, text2: str) -> float:
        """Compute Jaccard similarity over word tokens to compare job descriptions."""
        if not text1 or not text2:
            return 0.0
        words1 = set(re.findall(r"\b[a-zA-Z]{3,}\b", text1.lower()))
        words2 = set(re.findall(r"\b[a-zA-Z]{3,}\b", text2.lower()))
        if not words1 or not words2:
            return 0.0
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        return intersection / union if union > 0 else 0.0

    @classmethod
    def deduplicate(cls, listings: List[NormalizedJobListing]) -> List[NormalizedJobListing]:
        """
        Deduplicate listings using a multi-pass signal verification:
        1. Seen canonical URLs
        2. Exact fingerprint dedup_hash (company + normalized title + location)
        3. External ID collision within same source
        4. Cross-source near-duplicate detection (same company + high title match + high description overlap)
        """
        seen_canonical_urls: Set[str] = set()
        seen_dedup_hashes: Set[str] = set()
        seen_external_ids: Set[str] = set()

        unique_listings: List[NormalizedJobListing] = []
        duplicates_count = 0

        for item in listings:
            # 1. Canonical URL check
            can_url = cls.canonicalize_url(item.url) if item.url else ""
            if can_url and can_url in seen_canonical_urls:
                duplicates_count += 1
                continue

            # 2. Source + External ID check
            if item.external_id:
                ext_key = f"{item.source}:{item.external_id}"
                if ext_key in seen_external_ids:
                    duplicates_count += 1
                    continue

            # 3. Exact dedup hash check
            if item.dedup_hash in seen_dedup_hashes:
                duplicates_count += 1
                continue

            # 4. Near-duplicate check against already accepted unique listings
            is_near_dup = False
            item_title_clean = re.sub(r"[^a-z0-9]", "", item.title.lower())
            item_company_clean = (item.company or "").lower().strip()

            if item_company_clean:
                for existing in unique_listings:
                    existing_company = (existing.company or "").lower().strip()
                    if existing_company == item_company_clean:
                        existing_title_clean = re.sub(r"[^a-z0-9]", "", existing.title.lower())
                        if item_title_clean == existing_title_clean:
                            # Both company and title match exactly: compare description overlap
                            sim = cls.compute_text_similarity(item.description, existing.description)
                            if sim >= 0.70:
                                is_near_dup = True
                                duplicates_count += 1
                                break

            if is_near_dup:
                continue

            # Register identifiers
            if can_url:
                seen_canonical_urls.add(can_url)
            if item.external_id:
                seen_external_ids.add(f"{item.source}:{item.external_id}")
            seen_dedup_hashes.add(item.dedup_hash)

            unique_listings.append(item)

        logger.info(f"Deduplication complete: {len(listings)} inputs -> {len(unique_listings)} unique ({duplicates_count} duplicates pruned)")
        return unique_listings
