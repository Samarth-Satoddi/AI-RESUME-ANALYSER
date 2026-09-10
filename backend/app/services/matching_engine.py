import math
import re
from collections import Counter
from datetime import datetime, timezone
from typing import Dict, List, Set, Tuple

from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.logging import logger
from app.db.models import (
    Analysis,
    JobDescription,
    JobRequirement,
    MissingSkill,
    Recommendation,
    ResumeSkill,
    ResumeVersion,
    SkillMatch,
)
from app.services.embedding_service import EmbeddingService


class MatchResult(BaseModel):
    overall_match_score: float
    skill_score: float
    keyword_score: float
    semantic_score: float
    experience_score: float
    education_score: float
    matched_skills: List[str]
    missing_skills: List[Dict[str, str]]
    partial_matches: List[str]
    skill_match_records: List[dict]


class MatchingEngine:
    """
    Multi-signal resume-to-job matching engine.
    Combines exact skill matching, TF-IDF keyword overlap, cosine similarity,
    and requirement alignment into an explainable composite match score.
    """

    # Weights for overall match score
    WEIGHT_SKILLS = 0.40
    WEIGHT_KEYWORD = 0.25
    WEIGHT_SEMANTIC = 0.20
    WEIGHT_EXPERIENCE = 0.10
    WEIGHT_EDUCATION = 0.05

    @staticmethod
    def _compute_tf_idf_cosine(text1: str, text2: str) -> float:
        """Compute cosine similarity using term frequencies."""
        words1 = re.findall(r"\b[a-zA-Z0-9_-]{2,}\b", text1.lower())
        words2 = re.findall(r"\b[a-zA-Z0-9_-]{2,}\b", text2.lower())

        if not words1 or not words2:
            return 0.0

        vec1 = Counter(words1)
        vec2 = Counter(words2)

        intersection = set(vec1.keys()) & set(vec2.keys())
        numerator = sum(vec1[x] * vec2[x] for x in intersection)

        sum1 = sum(v ** 2 for v in vec1.values())
        sum2 = sum(v ** 2 for v in vec2.values())
        denominator = math.sqrt(sum1) * math.sqrt(sum2)

        if not denominator:
            return 0.0
        return min(round((numerator / denominator) * 100.0, 1), 100.0)

    @classmethod
    def match_resume_to_job(
        cls,
        db: Session,
        resume_version: ResumeVersion,
        job: JobDescription,
    ) -> Analysis:
        """
        Execute comprehensive matching analysis between resume version and job description,
        persisting Analysis, SkillMatch, MissingSkill, and Recommendation entities.
        """
        resume_text = resume_version.extracted_text or ""
        job_text = job.description or ""

        # Fetch candidate skills
        candidate_skills = (
            db.query(ResumeSkill)
            .filter(ResumeSkill.resume_version_id == resume_version.id)
            .all()
        )
        candidate_skill_map: Dict[str, ResumeSkill] = {
            s.normalized_skill_name: s for s in candidate_skills
        }
        candidate_skill_names = set(candidate_skill_map.keys())

        # Fetch job requirements
        job_reqs = (
            db.query(JobRequirement)
            .filter(JobRequirement.job_description_id == job.id)
            .all()
        )
        job_skill_reqs = [r for r in job_reqs if r.requirement_type == "skill"]

        # 1. Skill Matching Analysis
        matched_skills_list: List[str] = []
        partial_skills_list: List[str] = []
        missing_skills_list: List[Dict[str, str]] = []
        skill_match_records: List[SkillMatch] = []
        missing_records: List[MissingSkill] = []

        total_req_points = 0.0
        earned_req_points = 0.0

        for req in job_skill_reqs:
            weight = 2.0 if req.is_required else 1.0
            total_req_points += weight
            skill_norm = req.normalized_skill_name

            if skill_norm in candidate_skill_names:
                # Exact Match
                earned_req_points += weight
                matched_skills_list.append(req.requirement_text.split(":")[-1].strip())
                skill_match_records.append(
                    SkillMatch(
                        skill_name=req.normalized_skill_name,
                        resume_skill=candidate_skill_map[skill_norm].skill_name,
                        job_skill=req.requirement_text,
                        match_type="matched",
                        similarity_score=1.0,
                        importance="required" if req.is_required else "preferred",
                    )
                )
            elif any(skill_norm in s or s in skill_norm for s in candidate_skill_names):
                # Partial / Related Match
                earned_req_points += weight * 0.5
                partial_skills_list.append(req.requirement_text.split(":")[-1].strip())
                skill_match_records.append(
                    SkillMatch(
                        skill_name=req.normalized_skill_name,
                        resume_skill="Related",
                        job_skill=req.requirement_text,
                        match_type="partial",
                        similarity_score=0.5,
                        importance="required" if req.is_required else "preferred",
                    )
                )
            else:
                # Missing Skill
                missing_name = req.requirement_text.split(":")[-1].strip()
                priority = "high" if req.is_required else "medium"
                missing_skills_list.append({
                    "skill_name": missing_name,
                    "category": req.category or "General",
                    "priority": priority,
                })
                missing_records.append(
                    MissingSkill(
                        skill_name=missing_name,
                        category=req.category or "General",
                        priority=priority,
                        reason=f"Specified as {priority.upper()} priority requirement for {job.title}.",
                    )
                )

        skill_score = (
            round((earned_req_points / total_req_points) * 100.0, 1)
            if total_req_points > 0
            else 75.0
        )

        # 2. TF-IDF Keyword Score
        keyword_score = cls._compute_tf_idf_cosine(resume_text, job_text)

        # 3. Semantic Similarity Score (Dense vector embeddings via sentence-transformers)
        semantic_score, _ = EmbeddingService.compute_semantic_similarity(resume_text, job_text)

        # 4. Experience Match Score
        # Check if years requirement is met
        exp_req = next((r for r in job_reqs if r.requirement_type == "experience"), None)
        experience_score = 85.0
        if exp_req:
            # If candidate has 2+ experiences
            exp_count = len(resume_version.experiences) if resume_version.experiences else 1
            experience_score = min(exp_count * 30.0, 100.0)

        # 5. Education Match Score
        education_score = 90.0 if resume_version.education else 50.0

        # 6. Overall Match Score
        overall_match_score = round(
            (skill_score * cls.WEIGHT_SKILLS) +
            (keyword_score * cls.WEIGHT_KEYWORD) +
            (semantic_score * cls.WEIGHT_SEMANTIC) +
            (experience_score * cls.WEIGHT_EXPERIENCE) +
            (education_score * cls.WEIGHT_EDUCATION),
            1,
        )

        # 7. Create Analysis Record
        analysis = Analysis(
            user_id=job.user_id,
            resume_version_id=resume_version.id,
            job_description_id=job.id,
            status="completed",
            overall_score=overall_match_score,
            resume_score=round((skill_score + experience_score) / 2.0, 1),
            ats_score=keyword_score,
            skill_score=skill_score,
            semantic_score=semantic_score,
            experience_score=experience_score,
            keyword_score=keyword_score,
            education_score=education_score,
            completed_at=datetime.now(timezone.utc),
        )

        db.add(analysis)
        db.flush()

        # Link child records
        for sm in skill_match_records:
            sm.analysis_id = analysis.id
            db.add(sm)

        for ms in missing_records:
            ms.analysis_id = analysis.id
            db.add(ms)

        # Generate default deterministic recommendations
        recs: List[Recommendation] = []
        if missing_skills_list:
            top_missing = [m["skill_name"] for m in missing_skills_list[:3]]
            recs.append(
                Recommendation(
                    analysis_id=analysis.id,
                    recommendation_type="missing_skills",
                    title="Target Critical Missing Skills",
                    description=f"Add demonstrable experience or project work in: {', '.join(top_missing)}.",
                    priority="high",
                )
            )

        if keyword_score < 60:
            recs.append(
                Recommendation(
                    analysis_id=analysis.id,
                    recommendation_type="keywords",
                    title="Align Resume Terminology with Job Description",
                    description=f"Naturally incorporate keywords from {job.title} into your experience bullets to increase ATS pass rate.",
                    priority="medium",
                )
            )

        for r in recs:
            db.add(r)

        db.commit()
        db.refresh(analysis)
        logger.info(f"Match completed: analysis_id={analysis.id} score={overall_match_score}")
        return analysis
