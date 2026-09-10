import json
import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.logging import logger
from app.db.models import ResumeSkill, ResumeVersion


class ExtractedSkill(BaseModel):
    skill_name: str
    normalized_skill_name: str
    category: str
    proficiency: Optional[str] = None
    years_used: Optional[float] = None
    confidence: float = 1.0


class SkillExtractor:
    """
    Production-grade NLP skill extraction engine.
    Uses multi-category taxonomy, alias normalization, multi-word phrase matching,
    and contextual boundary checks to accurately detect skills.
    """

    _instance: Optional["SkillExtractor"] = None
    _taxonomy: Dict[str, List[str]] = {}
    _alias_map: Dict[str, str] = {}
    _skill_category_map: Dict[str, str] = {}

    # Common aliases & abbreviations -> Canonical Name
    ALIASES = {
        "k8s": "Kubernetes",
        "js": "JavaScript",
        "ts": "TypeScript",
        "py": "Python",
        "golang": "Go",
        "postgres": "PostgreSQL",
        "psql": "PostgreSQL",
        "mongo": "MongoDB",
        "reactjs": "React",
        "react.js": "React",
        "vuejs": "Vue.js",
        "vue": "Vue.js",
        "nodejs": "Node.js",
        "node": "Node.js",
        "aws ec2": "AWS",
        "aws s3": "AWS",
        "amazon web services": "AWS",
        "gcp": "Google Cloud Platform",
        "google cloud": "Google Cloud Platform",
        "azure": "Microsoft Azure",
        "tf": "Terraform",
        "sklearn": "scikit-learn",
        "scikit learn": "scikit-learn",
        "tf/keras": "TensorFlow",
        "rest api": "RESTful APIs",
        "restful api": "RESTful APIs",
        "rest apis": "RESTful APIs",
        "graphql api": "GraphQL",
        "ci cd": "CI/CD",
        "cicd": "CI/CD",
        "ml": "Machine Learning",
        "ai": "Artificial Intelligence",
        "dl": "Deep Learning",
    }

    def __init__(self):
        self._load_taxonomy()

    @classmethod
    def get_instance(cls) -> "SkillExtractor":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _load_taxonomy(self):
        """Load skills taxonomy from data/skills_taxonomy.json."""
        # Find path relative to project root
        current_dir = Path(__file__).resolve().parent
        potential_paths = [
            current_dir.parent.parent.parent / "data" / "skills_taxonomy.json",
            Path("data/skills_taxonomy.json").resolve(),
            Path("../data/skills_taxonomy.json").resolve(),
        ]

        taxonomy_file = None
        for p in potential_paths:
            if p.is_file():
                taxonomy_file = p
                break

        if taxonomy_file:
            try:
                with open(taxonomy_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._taxonomy = data.get("categories", {})
                    logger.info(f"Loaded skills taxonomy with {len(self._taxonomy)} categories")
            except Exception as e:
                logger.error(f"Failed to load skills taxonomy: {e}")
                self._taxonomy = {}
        else:
            logger.warning("skills_taxonomy.json not found, using fallback taxonomy")
            self._taxonomy = {}

        # Populate skill -> category and canonical maps
        for category, skills in self._taxonomy.items():
            for skill in skills:
                normalized = skill.lower().strip()
                self._skill_category_map[normalized] = category
                # Map self to canonical
                if normalized not in self._alias_map:
                    self._alias_map[normalized] = skill

        # Add custom aliases
        for alias, canonical in self.ALIASES.items():
            self._alias_map[alias.lower()] = canonical
            canonical_lower = canonical.lower()
            if canonical_lower in self._skill_category_map:
                self._skill_category_map[alias.lower()] = self._skill_category_map[canonical_lower]
            else:
                self._skill_category_map[alias.lower()] = "tools_and_methods"

    def _find_years_of_experience(self, text: str, skill: str) -> Optional[float]:
        """Detect mentions of experience duration near a skill mention."""
        pattern = rf"{re.escape(skill)}[^\.\n]*?(\d+(?:\.\d+)?)\+?\s*(?:years?|yrs?)"
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                pass
        return None

    def _detect_proficiency(self, text: str, skill: str) -> Optional[str]:
        """Detect proficiency indicators (Expert, Advanced, Intermediate, Familiar) near a skill."""
        patterns = [
            (r"(expert|lead|mastery|proficient)\s+(?:in|with)?\s*" + re.escape(skill), "expert"),
            (r"(advanced|senior)\s+(?:in|with)?\s*" + re.escape(skill), "advanced"),
            (r"(intermediate|solid|working knowledge)\s+(?:of|with)?\s*" + re.escape(skill), "intermediate"),
            (r"(familiar|basic|entry)\s+(?:with)?\s*" + re.escape(skill), "beginner"),
        ]
        for pat, level in patterns:
            if re.search(pat, text, re.IGNORECASE):
                return level
        return "intermediate"

    def extract_skills(self, text: str) -> List[ExtractedSkill]:
        """
        Extract all taxonomy-verified skills from resume or job text.
        Applies phrase matching, boundary checks, and normalization.
        """
        if not text:
            return []

        text_lower = text.lower()
        extracted: Dict[str, ExtractedSkill] = {}

        # 1. Check all canonical skills and aliases (sorted by length descending for greedy phrase matching)
        all_skill_terms = sorted(self._alias_map.keys(), key=len, reverse=True)

        for term in all_skill_terms:
            canonical = self._alias_map[term]
            norm_key = canonical.lower()

            # Skip if already detected via a longer phrase
            if norm_key in extracted:
                continue

            # Word boundary regex matching
            # Handle special symbols like C++, C#, .NET, Node.js
            if term in ("c++", "c#", ".net", "asp.net", "node.js", "vue.js", "next.js"):
                pattern = rf"(?:^|[\s,;:/|()\[\]])({re.escape(term)})(?:$|[\s,;:/|()\[\]])"
            elif len(term) <= 2:
                # Single or two letter skills (like 'R', 'C', 'Go') require strict boundary
                pattern = rf"(?:^|[\s,;:/|()\[\]])({re.escape(term)})(?:$|[\s,;:/|()\[\]])"
            else:
                pattern = rf"\b{re.escape(term)}\b"

            if re.search(pattern, text_lower):
                category = self._skill_category_map.get(term, self._skill_category_map.get(norm_key, "general"))
                years = self._find_years_of_experience(text, term)
                proficiency = self._detect_proficiency(text, term)

                extracted[norm_key] = ExtractedSkill(
                    skill_name=canonical,
                    normalized_skill_name=norm_key,
                    category=category,
                    proficiency=proficiency,
                    years_used=years,
                    confidence=1.0 if term == norm_key else 0.95,
                )

        return list(extracted.values())

    def save_resume_skills(
        self,
        db: Session,
        resume_version: ResumeVersion,
        skills: List[ExtractedSkill],
    ) -> List[ResumeSkill]:
        """Persist extracted skills to the database, removing any previous records."""
        db.query(ResumeSkill).filter(ResumeSkill.resume_version_id == resume_version.id).delete()

        created: List[ResumeSkill] = []
        for s in skills:
            record = ResumeSkill(
                resume_version_id=resume_version.id,
                skill_name=s.skill_name,
                normalized_skill_name=s.normalized_skill_name,
                category=s.category,
                proficiency=s.proficiency,
                years_used=s.years_used,
            )
            db.add(record)
            created.append(record)

        db.commit()
        logger.info(f"Saved {len(created)} skills for resume_version={resume_version.id}")
        return created
