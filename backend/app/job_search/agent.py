import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
import uuid

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging import logger
from app.db.models import (
    Analysis,
    JobDescription,
    JobListing,
    JobRequirement,
    JobSearch,
    JobSearchResult,
    Resume,
    ResumeVersion,
    User,
)
from app.job_search.deduplicator import JobDeduplicator
from app.job_search.normalizer import JobNormalizer
from app.job_search.ranking import JobRankingEngine
from app.job_search.schemas import JobSearchQuery, NormalizedJobListing, RawJobListing
from app.job_search.sources.base import SourceRegistry
from app.services.ai_provider import get_ai_provider
from app.services.entity_extractor import EntityExtractor
from app.services.job_service import JobService
from app.services.matching_engine import MatchingEngine
from app.services.skill_extractor import SkillExtractor


class JobSearchAgent:
    """
    Autonomous Job Search Agent orchestration layer.
    Coordinates query planning, multi-source collection, normalization,
    deduplication, requirement parsing, resume matching, skill-gap analysis,
    ranking, AI rationale generation, and transactional persistence.
    """

    @classmethod
    def generate_search_queries(cls, base_query: JobSearchQuery, resume_skills: List[str]) -> List[JobSearchQuery]:
        """
        Generate targeted, diversified queries from role, location, and resume skills
        without overloading external providers.
        """
        queries = [base_query]
        role = base_query.role.strip()

        # Query variation 1: Role + primary skill if skills available
        if resume_skills and len(queries) < 3:
            top_skill = resume_skills[0]
            if top_skill.lower() not in role.lower():
                q_variant = base_query.model_copy()
                q_variant.role = f"{role} {top_skill}"
                queries.append(q_variant)

        # Query variation 2: Role with remote emphasis if requested
        if base_query.remote and "remote" not in role.lower() and len(queries) < 3:
            q_remote = base_query.model_copy()
            q_remote.role = f"{role} Remote"
            queries.append(q_remote)

        return queries[:3]

    @classmethod
    async def fetch_from_sources(cls, queries: List[JobSearchQuery]) -> Tuple[List[RawJobListing], Dict[str, str], List[str]]:
        """
        Query enabled sources concurrently with timeout protection.
        Strictly prevents silent fallback to mock data in production mode.
        """
        sources_cfg = getattr(settings, "JOB_SEARCH_SOURCES", "") or getattr(settings, "JOB_SEARCH_PROVIDER", "")
        configured_names = [s.strip().lower() for s in sources_cfg.split(",") if s.strip()]

        active_sources = []
        is_mock_mode = any(name in ("mock", "mock_source") for name in configured_names)

        if is_mock_mode:
            logger.info("JobSearchAgent running in MOCK development mode.")
            mock_src = SourceRegistry.get_source("mock") or SourceRegistry.get_source("mock_source")
            if mock_src and mock_src.is_enabled:
                active_sources.append(mock_src)
        else:
            # Production mode: query legitimate external sources only
            for name in configured_names:
                src = SourceRegistry.get_source(name)
                if src and src.is_enabled and src not in active_sources:
                    active_sources.append(src)

            if not active_sources:
                logger.warning(
                    f"No active external job sources found for configured sources: {configured_names}. "
                    "Refusing mock fallback in production mode."
                )

        all_raw_listings: List[RawJobListing] = []
        source_errors: Dict[str, str] = {}
        sources_queried = [src.source_name for src in active_sources]

        for q in queries:
            tasks = [src.search(q) for src in active_sources]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for src, res in zip(active_sources, results):
                if isinstance(res, Exception):
                    logger.warning(f"JobSource '{src.source_name}' raised error: {res}")
                    source_errors[src.source_name] = str(res)
                elif isinstance(res, list):
                    all_raw_listings.extend(res)

        logger.info(
            f"Collected {len(all_raw_listings)} total raw listings from {len(active_sources)} sources ({sources_queried}). "
            f"Errors encountered: {len(source_errors)}"
        )
        return all_raw_listings, source_errors, sources_queried

    @classmethod
    def ensure_resume_analyzed(cls, db: Session, resume: Resume) -> Optional[ResumeVersion]:
        """
        Verify resume has extracted text and taxonomy skills.
        If missing, automatically executes text extraction and skill extraction.
        """
        if not resume.versions:
            return None

        active_version = resume.versions[-1]

        # Check if skills have been extracted
        if not active_version.skills:
            logger.info(f"Auto-extracting skills for resume_id={resume.id}")
            text = active_version.extracted_text or ""
            extractor = SkillExtractor.get_instance()
            skills = extractor.extract_skills(text)
            extractor.save_resume_skills(db, active_version, skills)

            # Also extract entities
            entity_extractor = EntityExtractor()
            entity_extractor.process_and_save_entities(
                db=db,
                resume_version=active_version,
                sections=active_version.sections,
                full_text=text,
            )
            db.refresh(active_version)

        return active_version

    @classmethod
    async def execute_search(
        cls,
        db: Session,
        search_record: JobSearch,
        user: User,
    ) -> JobSearch:
        """
        Full autonomous execution flow for a JobSearch entity.
        Updates database progress stages in real time.
        """
        try:
            logger.info(f"[JobSearchAgent] Commencing search id={search_record.id} for user={user.id}")

            # 1. Update status -> searching
            search_record.status = "searching"
            db.commit()

            # 2. Identify candidate resume
            target_resume: Optional[Resume] = None
            if search_record.resume_id:
                target_resume = (
                    db.query(Resume)
                    .filter(Resume.id == search_record.resume_id, Resume.user_id == user.id)
                    .first()
                )
            if not target_resume:
                # Default to user's first available resume
                target_resume = (
                    db.query(Resume)
                    .filter(Resume.user_id == user.id)
                    .order_by(Resume.created_at.desc())
                    .first()
                )

            active_version: Optional[ResumeVersion] = None
            resume_skill_names: List[str] = []
            if target_resume:
                active_version = cls.ensure_resume_analyzed(db, target_resume)
                if active_version and active_version.skills:
                    resume_skill_names = [s.skill_name for s in active_version.skills]

            # 3. Plan queries
            base_query = JobSearchQuery(
                role=search_record.query_role,
                location=search_record.location,
                remote=search_record.remote or False,
                experience=search_record.experience_level,
                employment_type=search_record.employment_type,
                salary_min=search_record.salary_min,
                salary_max=search_record.salary_max,
                posted_within_days=search_record.posted_within_days or 14,
                limit=settings.JOB_SEARCH_MAX_RESULTS_PER_SOURCE,
            )
            queries = cls.generate_search_queries(base_query, resume_skill_names)

            # 4. Fetch raw listings
            raw_listings, source_errors, sources_queried = await cls.fetch_from_sources(queries)
            search_record.jobs_found = len(raw_listings)
            db.commit()

            if not raw_listings:
                if source_errors and len(source_errors) >= len(sources_queried) and sources_queried:
                    search_record.status = "failed"
                    search_record.error_message = (
                        f"Unable to retrieve external jobs. Errors reported by: {', '.join(source_errors.keys())}."
                    )
                else:
                    search_record.status = "completed"
                    search_record.error_message = None
                db.commit()
                return search_record

            # 5. Normalization & Deduplication
            normalized_listings = [JobNormalizer.normalize(r) for r in raw_listings]
            unique_listings = JobDeduplicator.deduplicate(normalized_listings)

            # Limit total results
            max_results = min(len(unique_listings), settings.JOB_SEARCH_MAX_TOTAL_RESULTS)
            curated_listings = unique_listings[:max_results]

            # 6. Update status -> analyzing
            search_record.status = "analyzing"
            db.commit()

            ai_provider = get_ai_provider()
            evaluated_items: List[Dict[str, Any]] = []

            for idx, listing_data in enumerate(curated_listings, start=1):
                # Check if JobListing already stored by dedup_hash
                existing_listing = None
                if listing_data.dedup_hash:
                    existing_listing = (
                        db.query(JobListing)
                        .filter(JobListing.dedup_hash == listing_data.dedup_hash)
                        .first()
                    )

                if existing_listing:
                    listing_record = existing_listing
                else:
                    listing_record = JobListing(
                        external_id=listing_data.external_id,
                        source=listing_data.source,
                        title=listing_data.title,
                        company=listing_data.company,
                        location=listing_data.location,
                        remote_type=listing_data.remote_type,
                        employment_type=listing_data.employment_type,
                        salary_min=listing_data.salary_min,
                        salary_max=listing_data.salary_max,
                        currency=listing_data.currency,
                        description=listing_data.description,
                        url=listing_data.url,
                        posted_at=listing_data.posted_at,
                        collected_at=listing_data.collected_at,
                        dedup_hash=listing_data.dedup_hash,
                    )
                    db.add(listing_record)
                    db.flush()

                # Reuse existing JobDescription and JobRequirement system
                if not listing_record.job_description_id:
                    job_desc = JobDescription(
                        user_id=user.id,
                        title=listing_record.title,
                        company=listing_record.company,
                        description=listing_record.description,
                        source_url=listing_record.url,
                    )
                    db.add(job_desc)
                    db.flush()
                    JobService.parse_job_requirements(db, job_desc)
                    listing_record.job_description_id = job_desc.id
                    db.flush()
                else:
                    job_desc = db.query(JobDescription).filter(JobDescription.id == listing_record.job_description_id).first()

                search_record.jobs_analyzed = idx
                db.commit()

                # 7. Match against resume using existing MatchingEngine
                analysis_record: Optional[Analysis] = None
                matched_skills_list: List[str] = []
                missing_skills_list: List[str] = []

                if active_version and job_desc:
                    analysis_record = MatchingEngine.match_resume_to_job(
                        db=db,
                        resume_version=active_version,
                        job=job_desc,
                    )
                    matched_skills_list = [
                        sm.job_skill.split(":")[-1].strip()
                        for sm in analysis_record.skill_matches
                        if sm.match_type == "matched"
                    ]
                    missing_skills_list = [
                        ms.skill_name for ms in analysis_record.missing_skills
                    ]

                overall_score = analysis_record.overall_score if analysis_record else 50.0
                skill_score = analysis_record.skill_score if analysis_record else 50.0
                kw_score = analysis_record.keyword_score if analysis_record else 50.0
                sem_score = analysis_record.semantic_score if analysis_record else 50.0
                exp_score = analysis_record.experience_score if analysis_record else 50.0
                edu_score = analysis_record.education_score if analysis_record else 50.0

                # 8. Generate qualitative AI explanation
                explanation = ai_provider.generate_job_match_explanation(
                    job_title=listing_record.title,
                    matched_skills=matched_skills_list,
                    missing_skills=missing_skills_list,
                    overall_score=overall_score,
                )

                evaluated_items.append({
                    "listing_record": listing_record,
                    "analysis_record": analysis_record,
                    "overall_match_score": overall_score,
                    "skill_score": skill_score,
                    "keyword_score": kw_score,
                    "semantic_score": sem_score,
                    "experience_score": exp_score,
                    "education_score": edu_score,
                    "location": listing_record.location,
                    "remote_type": listing_record.remote_type,
                    "posted_at": listing_record.posted_at,
                    "ai_explanation": explanation,
                })

            # 9. Update status -> matching
            search_record.status = "matching"
            search_record.jobs_matched = len(evaluated_items)
            db.commit()

            # 10. Multi-signal ranking
            ranked_items = JobRankingEngine.rank_opportunities(
                items=evaluated_items,
                user_location=search_record.location,
                user_remote=search_record.remote,
            )

            # 11. Persist JobSearchResult records
            for item in ranked_items:
                res_record = JobSearchResult(
                    search_id=search_record.id,
                    job_listing_id=item["listing_record"].id,
                    analysis_id=item["analysis_record"].id if item.get("analysis_record") else None,
                    overall_match_score=item["overall_match_score"],
                    skill_score=item["skill_score"],
                    keyword_score=item["keyword_score"],
                    semantic_score=item["semantic_score"],
                    experience_score=item["experience_score"],
                    education_score=item["education_score"],
                    rank_score=item["rank_score"],
                    rank=item["rank"],
                    ai_explanation=item["ai_explanation"],
                )
                db.add(res_record)

            # 12. Finalize status -> completed
            search_record.status = "completed"
            db.commit()
            db.refresh(search_record)
            logger.info(f"[JobSearchAgent] Completed search id={search_record.id} with {len(ranked_items)} ranked results")
            return search_record

        except Exception as exc:
            logger.exception(f"[JobSearchAgent] Search run failed: {exc}")
            db.rollback()
            search_record.status = "failed"
            search_record.error_message = str(exc)
            db.commit()
            return search_record
