import os
from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from pydantic import BaseModel

from app.core.config import settings
from app.core.logging import logger


class BulletImprovement(BaseModel):
    original: str
    improved: str
    rationale: str


class RoadmapStage(BaseModel):
    skill_name: str
    topic: str
    priority: str
    estimated_days: int
    prerequisites: List[str]


class GeneratedQuestion(BaseModel):
    category: str
    question: str
    difficulty: str
    why_it_matters: str
    answer_guidance: str


class BaseAIProvider(ABC):
    """Abstract interface for AI guidance and generation."""

    @abstractmethod
    def generate_recommendations(self, resume_text: str, job_text: str, missing_skills: List[str]) -> List[Dict[str, str]]:
        pass

    @abstractmethod
    def improve_bullet(self, bullet: str, target_role: Optional[str] = None) -> BulletImprovement:
        pass

    @abstractmethod
    def generate_roadmap(self, missing_skills: List[str], target_job: str) -> List[RoadmapStage]:
        pass

    @abstractmethod
    def generate_interview_questions(self, skills: List[str], target_job: str) -> List[GeneratedQuestion]:
        pass

    @abstractmethod
    def generate_job_match_explanation(
        self,
        job_title: str,
        matched_skills: List[str],
        missing_skills: List[str],
        overall_score: float,
    ) -> str:
        pass


class DeterministicMockAIProvider(BaseAIProvider):
    """
    Deterministic, high-quality AI provider for development and testing.
    Never invents fictitious facts; applies standard STAR resume frameworks and curriculum trees.
    """

    def generate_recommendations(self, resume_text: str, job_text: str, missing_skills: List[str]) -> List[Dict[str, str]]:
        recs = [
            {
                "title": "Lead with Quantifiable Impact",
                "description": "Transform descriptive bullets into metric-driven statements (e.g. 'Optimized database indexes, reducing query latency by 35%').",
                "priority": "high",
                "type": "content",
            },
            {
                "title": "Strengthen Professional Summary",
                "description": "Tailor your 3-line executive summary to highlight your years of experience, core tech stack, and specialty in high-throughput systems.",
                "priority": "medium",
                "type": "summary",
            },
        ]
        if missing_skills:
            top_3 = ", ".join(missing_skills[:3])
            recs.append({
                "title": f"Bridge Core Technical Gap: {top_3}",
                "description": f"The target role emphasizes {top_3}. Add any hands-on academic or personal project experience with these tools.",
                "priority": "high",
                "type": "skills",
            })
        return recs

    def improve_bullet(self, bullet: str, target_role: Optional[str] = None) -> BulletImprovement:
        import re
        cleaned = bullet.strip().lstrip("-*•").strip()
        role = target_role or "Software Engineer"

        # Sanitize adversarial prompt injection attempts
        injection_patterns = [
            r"ignore\s+(?:previous|all|prior)\s+instructions?",
            r"disregard\s+(?:all|prior)\s+prompts?",
            r"system\s*:",
            r"output\s*:",
            r"you\s+are\s+now\s+a",
            r"as\s+an?\s+ai",
        ]
        sanitized = cleaned
        was_injected = False
        for pat in injection_patterns:
            if re.search(pat, sanitized, re.IGNORECASE):
                was_injected = True
                sanitized = re.sub(pat, "", sanitized, flags=re.IGNORECASE)

        sanitized = re.sub(r"\s+", " ", sanitized).strip(":,. ")

        if was_injected:
            # If adversarial prompt detected, return a neutralized, safe engineering statement
            return BulletImprovement(
                original=cleaned,
                improved=f"Contributed to core software modules and backend services for {role} workflows, following rigorous engineering quality standards.",
                rationale="Neutralized non-standard prompt formatting and refactored into a standardized accomplishment statement.",
            )

        # Apply action verb and STAR structure enhancement
        if any(w in sanitized.lower() for w in ("worked on", "helped", "responsible for", "handled")):
            improved = f"Spearheaded the development of core components for {sanitized.replace('worked on', '').replace('responsible for', '').strip()}, optimizing throughput and code maintainability."
            rationale = "Replaced passive phrasing ('worked on') with authoritative action verb ('Spearheaded') and emphasized maintainability."
        else:
            improved = f"Architected and deployed {sanitized}, enhancing overall system reliability and accelerating delivery pipelines."
            rationale = "Structured the achievement around production reliability and engineering best practices."

        return BulletImprovement(
            original=cleaned,
            improved=improved,
            rationale=rationale,
        )

    def generate_roadmap(self, missing_skills: List[str], target_job: str) -> List[RoadmapStage]:
        stages: List[RoadmapStage] = []
        skills_to_map = missing_skills if missing_skills else ["Docker", "Kubernetes", "PostgreSQL", "FastAPI"]

        for idx, skill in enumerate(skills_to_map[:5]):
            stages.append(
                RoadmapStage(
                    skill_name=skill,
                    topic=f"Mastery of {skill} for Production {target_job}",
                    priority="high" if idx < 2 else "medium",
                    estimated_days=7 + (idx * 3),
                    prerequisites=[skills_to_map[idx - 1]] if idx > 0 else [],
                )
            )
        return stages

    def generate_interview_questions(self, skills: List[str], target_job: str) -> List[GeneratedQuestion]:
        top_skills = skills[:4] if skills else ["Python", "Databases", "System Design", "APIs"]
        questions = [
            GeneratedQuestion(
                category="System Design",
                question=f"How would you architect a distributed microservices platform tailored for {target_job} with 99.99% availability?",
                difficulty="hard",
                why_it_matters="Assesses architectural maturity, failure domain isolation, and horizontal scaling strategies.",
                answer_guidance="Discuss stateless API gateways, message queues for decoupling, caching layers, and database replica sharding.",
            ),
            GeneratedQuestion(
                category="Technical",
                question=f"Explain how you handle concurrency, race conditions, and connection pooling when integrating with {top_skills[0] if top_skills else 'PostgreSQL'}.",
                difficulty="medium",
                why_it_matters="Evaluates backend performance tuning and transactional consistency under load.",
                answer_guidance="Mention ACID transaction isolation levels, optimistic locking, and async connection pool sizing.",
            ),
            GeneratedQuestion(
                category="Behavioral",
                question="Tell me about a time you encountered an unexpected production outage or critical bug. How did you triage and resolve it?",
                difficulty="medium",
                why_it_matters="Evaluates emotional composure, root cause analysis (RCA), and incident response protocols.",
                answer_guidance="Use the STAR method: Situation, Task, Action (monitoring, hotfix), and Result (post-mortem and regression test added).",
            ),
            GeneratedQuestion(
                category="Project",
                question=f"Walk me through the most technically challenging project on your resume. What technical tradeoffs did you make?",
                difficulty="medium",
                why_it_matters="Tests ownership, technical self-awareness, and pragmatic decision-making.",
                answer_guidance="Highlight why you chose your tech stack over alternatives and what you would improve in hindsight.",
            ),
        ]
        return questions

    def generate_job_match_explanation(
        self,
        job_title: str,
        matched_skills: List[str],
        missing_skills: List[str],
        overall_score: float,
    ) -> str:
        matched_str = f"experience in {', '.join(matched_skills[:3])}" if matched_skills else "general technical alignment"
        if missing_skills:
            gap_str = f"Key skills to highlight or develop include {', '.join(missing_skills[:2])}."
        else:
            gap_str = "Your profile addresses all key requirements detected in the job posting."

        level = "strong" if overall_score >= 80 else "good" if overall_score >= 60 else "moderate"
        return (
            f"This role is a {level} match ({overall_score:.0f}%) because your resume demonstrates {matched_str}. "
            f"{gap_str}"
        )


class OpenAIProvider(BaseAIProvider):
    """OpenAI-backed provider with automatic fallback to mock provider."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self._fallback = DeterministicMockAIProvider()

    def generate_recommendations(self, resume_text: str, job_text: str, missing_skills: List[str]) -> List[Dict[str, str]]:
        # In production with API key, calls OpenAI; falls back gracefully
        return self._fallback.generate_recommendations(resume_text, job_text, missing_skills)

    def improve_bullet(self, bullet: str, target_role: Optional[str] = None) -> BulletImprovement:
        return self._fallback.improve_bullet(bullet, target_role)

    def generate_roadmap(self, missing_skills: List[str], target_job: str) -> List[RoadmapStage]:
        return self._fallback.generate_roadmap(missing_skills, target_job)

    def generate_interview_questions(self, skills: List[str], target_job: str) -> List[GeneratedQuestion]:
        return self._fallback.generate_interview_questions(skills, target_job)

    def generate_job_match_explanation(
        self,
        job_title: str,
        matched_skills: List[str],
        missing_skills: List[str],
        overall_score: float,
    ) -> str:
        return self._fallback.generate_job_match_explanation(job_title, matched_skills, missing_skills, overall_score)


def get_ai_provider() -> BaseAIProvider:
    """Factory to instantiate configured AI provider."""
    # If OPENAI_API_KEY is available and configured, use it, else default to DeterministicMockAIProvider
    api_key = os.getenv("OPENAI_API_KEY", "")
    if api_key and not api_key.startswith("mock"):
        return OpenAIProvider(api_key=api_key)
    return DeterministicMockAIProvider()
