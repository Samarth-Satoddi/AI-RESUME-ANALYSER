import re
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel


class ScoreBreakdown(BaseModel):
    overall_score: float
    ats_score: float
    skill_score: float
    experience_score: float
    education_score: float
    project_score: float
    structure_score: float
    completeness_score: float
    strengths: List[str]
    weaknesses: List[str]
    recommendations: List[str]
    ats_details: Dict[str, Any]



class ScoringEngine:
    """
    Deterministic, explainable scoring engine for resume quality and ATS compliance.
    Scores components independently using configurable mathematical weights.
    """

    # Weights for overall score
    WEIGHT_SKILLS = 0.25
    WEIGHT_EXPERIENCE = 0.25
    WEIGHT_ATS = 0.20
    WEIGHT_PROJECTS = 0.10
    WEIGHT_EDUCATION = 0.10
    WEIGHT_STRUCTURE = 0.10

    # Strong action verbs for ATS and experience scoring
    ACTION_VERBS = {
        "architected", "developed", "built", "engineered", "implemented", "designed",
        "optimized", "scaled", "spearheaded", "accelerated", "deployed", "orchestrated",
        "automated", "refactored", "integrated", "led", "managed", "reduced", "increased",
        "saved", "resolved", "improved", "launched", "created", "executed"
    }

    # Standard essential sections
    ESSENTIAL_SECTIONS = {"summary", "skills", "experience", "education"}

    @classmethod
    def calculate_skill_score(cls, skills_count: int, categories_count: int) -> float:
        """Score skills based on count (breadth) and category diversity."""
        # 10+ skills gives max count score, 4+ categories gives max diversity
        count_score = min(skills_count / 10.0, 1.0) * 60.0
        diversity_score = min(categories_count / 4.0, 1.0) * 40.0
        return round(count_score + diversity_score, 1)

    @classmethod
    def calculate_experience_score(cls, experiences: list, text: str) -> Tuple[float, int, int]:
        """Score work experience based on depth, action verbs, and quantified metrics."""
        if not experiences:
            return 0.0, 0, 0

        # Base score from number of experiences (up to 3 experiences -> 40 pts)
        base_score = min(len(experiences) / 3.0, 1.0) * 40.0

        # Count action verbs in experience descriptions
        text_lower = text.lower()
        verb_count = sum(1 for verb in cls.ACTION_VERBS if re.search(rf"\b{verb}\b", text_lower))
        verb_score = min(verb_count / 6.0, 1.0) * 30.0

        # Count quantified achievements (e.g., 40%, $100k, 10M, 5x)
        metric_matches = re.findall(r"(?:\d+%\b|\$\d+[\d,]*|\b\d+M\b|\b\d+k\b|\b\d+x\b|\d+\s*(?:times|users|requests|percent))", text, re.IGNORECASE)
        metric_count = len(metric_matches)
        metric_score = min(metric_count / 4.0, 1.0) * 30.0

        total = round(base_score + verb_score + metric_score, 1)
        return min(total, 100.0), verb_count, metric_count

    @classmethod
    def calculate_ats_score(
        cls,
        sections: list,
        contact_info: dict,
        action_verb_count: int,
        metric_count: int,
        text_length: int,
    ) -> Tuple[float, Dict[str, Any]]:

        """
        Evaluate ATS machine-readability, structure, and formatting.
        Max 100 points:
        - Contact information presence (25 pts)
        - Essential section presence (35 pts)
        - Action verbs and metrics (25 pts)
        - Resume length & formatting health (15 pts)
        """
        details = {}

        # 1. Contact checks
        contact_score = 0.0
        has_email = bool(contact_info.get("email"))
        has_phone = bool(contact_info.get("phone"))
        has_linkedin = bool(contact_info.get("linkedin_url"))
        has_github = bool(contact_info.get("github_url"))

        if has_email: contact_score += 10.0
        if has_phone: contact_score += 8.0
        if has_linkedin or has_github: contact_score += 7.0
        details["contact_score"] = contact_score
        details["has_email"] = has_email
        details["has_phone"] = has_phone
        details["has_linkedin"] = has_linkedin

        # 2. Section completeness checks
        present_sections = {s.section_type for s in sections} if sections else set()
        matched_essential = present_sections.intersection(cls.ESSENTIAL_SECTIONS)
        section_score = (len(matched_essential) / len(cls.ESSENTIAL_SECTIONS)) * 35.0
        details["section_score"] = round(section_score, 1)
        details["missing_essential_sections"] = list(cls.ESSENTIAL_SECTIONS - present_sections)

        # 3. Content impact (action verbs + metrics)
        impact_score = min((action_verb_count * 2.5) + (metric_count * 3.0), 25.0)
        details["impact_score"] = round(impact_score, 1)
        details["action_verb_count"] = action_verb_count
        details["metric_count"] = metric_count

        # 4. Length/density checks (ideal: 1,500 to 5,000 characters)
        length_score = 15.0
        if text_length < 800:
            length_score = 6.0
        elif text_length > 10000:
            length_score = 9.0
        details["length_score"] = length_score
        details["text_length"] = text_length

        total_ats = round(contact_score + section_score + impact_score + length_score, 1)
        return min(total_ats, 100.0), details

    @classmethod
    def evaluate_resume(
        cls,
        skills: list,
        experiences: list,
        educations: list,
        projects: list,
        sections: list,
        contact_info: dict,
        full_text: str,
    ) -> ScoreBreakdown:
        """Run comprehensive multi-component scoring evaluation."""
        # 1. Skill Score
        categories = {s.category for s in skills if hasattr(s, "category")}
        skill_score = cls.calculate_skill_score(len(skills), len(categories))

        # 2. Experience Score
        experience_score, action_verbs, metrics = cls.calculate_experience_score(experiences, full_text)

        # 3. Education Score
        education_score = 90.0 if educations else 40.0

        # 4. Projects Score
        project_score = min(len(projects) * 35.0, 95.0) if projects else 45.0

        # 5. Structure Score
        section_types = {s.section_type for s in sections} if sections else set()
        structure_score = round(min(len(section_types) / 5.0, 1.0) * 100.0, 1)

        # 6. Completeness Score
        completeness_items = [
            bool(skills),
            bool(experiences),
            bool(educations),
            bool(projects),
            bool(contact_info.get("email")),
            bool(contact_info.get("phone")),
            len(sections) >= 4,
        ]
        completeness_score = round((sum(completeness_items) / len(completeness_items)) * 100.0, 1)

        # 7. ATS Score
        ats_score, ats_details = cls.calculate_ats_score(
            sections=sections,
            contact_info=contact_info,
            action_verb_count=action_verbs,
            metric_count=metrics,
            text_length=len(full_text),
        )

        # 8. Overall Score (Weighted)
        overall_score = round(
            (skill_score * cls.WEIGHT_SKILLS) +
            (experience_score * cls.WEIGHT_EXPERIENCE) +
            (ats_score * cls.WEIGHT_ATS) +
            (education_score * cls.WEIGHT_EDUCATION) +
            (project_score * cls.WEIGHT_PROJECTS) +
            (structure_score * cls.WEIGHT_STRUCTURE),
            1,
        )

        # Generate Strengths, Weaknesses, and Recommendations
        strengths: List[str] = []
        weaknesses: List[str] = []
        recommendations: List[str] = []

        if skill_score >= 60:
            strengths.append(f"Strong technical skill breadth ({len(skills)} taxonomy-verified skills identified across {len(categories)} domains).")
        else:
            weaknesses.append("Skill coverage is below average; highlight core tools and programming languages.")
            recommendations.append("Add a dedicated 'Technical Skills' section detailing languages, frameworks, and databases.")

        if metrics >= 1:
            strengths.append(f"Effective use of quantified achievements ({metrics} measurable performance metrics detected).")
        else:
            weaknesses.append("Experience bullets lack measurable business impact metrics.")
            recommendations.append("Quantify work experience achievements with numbers, percentages, or dollar values (e.g. 'Improved latency by 35%').")

        if ats_score >= 70:
            strengths.append("High ATS compliance with clear section hierarchy and standard headers.")
        else:
            weaknesses.append("Resume formatting has potential ATS readability risks.")
            recommendations.append("Ensure standard section headers ('Experience', 'Education', 'Skills') without non-standard table layouts.")

        if contact_info.get("email") and contact_info.get("phone"):
            strengths.append("Complete contact profile with verified email and phone communication channels.")

        if not contact_info.get("linkedin_url") and not contact_info.get("github_url"):
            weaknesses.append("No professional profile links (LinkedIn or GitHub) detected.")
            recommendations.append("Include your LinkedIn URL and GitHub profile link in the header contact information.")

        if not projects:
            recommendations.append("Include 1-2 featured technical projects showcasing end-to-end architecture.")


        return ScoreBreakdown(
            overall_score=overall_score,
            ats_score=ats_score,
            skill_score=skill_score,
            experience_score=experience_score,
            education_score=education_score,
            project_score=project_score,
            structure_score=structure_score,
            completeness_score=completeness_score,
            strengths=strengths,
            weaknesses=weaknesses,
            recommendations=recommendations,
            ats_details=ats_details,
        )
