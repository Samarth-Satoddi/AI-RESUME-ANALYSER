from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from app.core.config import settings
from app.core.logging import logger


class JobRankingEngine:
    """
    Ranks analyzed job opportunities using a multi-factor formula.
    Weights are configurable and guarantee that job freshness alone
    cannot override a low resume-to-job match score.
    """

    @classmethod
    def compute_location_fit(
        cls,
        user_location: Optional[str],
        user_remote: Optional[bool],
        job_location: Optional[str],
        job_remote_type: Optional[str],
    ) -> float:
        """Score alignment between user location/remote preference and job posting (0-100)."""
        # User requested remote
        if user_remote:
            if job_remote_type == "remote":
                return 100.0
            if job_remote_type == "hybrid":
                return 60.0
            return 30.0

        # User specified physical location
        if user_location and job_location:
            u_loc = user_location.lower().strip()
            j_loc = job_location.lower().strip()
            if u_loc in j_loc or j_loc in u_loc:
                return 100.0
            if job_remote_type == "remote":
                return 80.0
            return 30.0

        # If job is remote and user had no strict preference
        if job_remote_type == "remote":
            return 90.0

        return 70.0

    @classmethod
    def compute_freshness_score(cls, posted_at: Optional[datetime]) -> float:
        """Score listing freshness based on elapsed days since posting (0-100)."""
        if not posted_at:
            return 50.0

        try:
            now = datetime.now(timezone.utc)
            if posted_at.tzinfo is None:
                posted_at = posted_at.replace(tzinfo=timezone.utc)
            age_days = max(0, (now - posted_at).days)

            if age_days <= 2:
                return 100.0
            elif age_days <= 5:
                return 85.0
            elif age_days <= 10:
                return 70.0
            elif age_days <= 20:
                return 55.0
            elif age_days <= 30:
                return 40.0
            else:
                return 25.0
        except Exception:
            return 50.0

    @classmethod
    def compute_rank_score(
        cls,
        overall_match: float,
        skill_score: float,
        location_fit: float,
        freshness_score: float,
    ) -> float:
        """
        Calculate weighted composite ranking score.
        Enforces a non-override penalty for poor technical matches.
        """
        w_match = settings.JOB_SEARCH_RANK_WEIGHT_MATCH
        w_skill = settings.JOB_SEARCH_RANK_WEIGHT_SKILL
        w_loc = settings.JOB_SEARCH_RANK_WEIGHT_LOCATION
        w_fresh = settings.JOB_SEARCH_RANK_WEIGHT_FRESHNESS

        raw_score = (
            (overall_match * w_match) +
            (skill_score * w_skill) +
            (location_fit * w_loc) +
            (freshness_score * w_fresh)
        )

        # Critical constraint: If overall match is poor (< 50), cap rank score
        if overall_match < 50.0:
            raw_score = min(raw_score, overall_match)

        return round(raw_score, 1)

    @classmethod
    def rank_opportunities(
        cls,
        items: List[Dict[str, Any]],
        user_location: Optional[str] = None,
        user_remote: Optional[bool] = False,
    ) -> List[Dict[str, Any]]:
        """
        Rank a list of matched opportunity dictionaries.
        Computes location fit, freshness score, composite rank score,
        and assigns ascending integer rank indices (1, 2, 3...).
        """
        for item in items:
            loc_fit = cls.compute_location_fit(
                user_location=user_location,
                user_remote=user_remote,
                job_location=item.get("location"),
                job_remote_type=item.get("remote_type"),
            )
            fresh_score = cls.compute_freshness_score(item.get("posted_at"))
            rank_score = cls.compute_rank_score(
                overall_match=item.get("overall_match_score", 0.0),
                skill_score=item.get("skill_score", 0.0),
                location_fit=loc_fit,
                freshness_score=fresh_score,
            )
            item["location_fit"] = loc_fit
            item["freshness_score"] = fresh_score
            item["rank_score"] = rank_score

        # Sort descending by rank_score, then overall_match_score
        items.sort(
            key=lambda x: (x.get("rank_score", 0.0), x.get("overall_match_score", 0.0)),
            reverse=True,
        )

        # Assign rank 1-based index
        for idx, item in enumerate(items, start=1):
            item["rank"] = idx

        logger.info(f"Ranked {len(items)} opportunities. Top score: {items[0]['rank_score'] if items else 'N/A'}")
        return items
