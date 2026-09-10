import pytest
from app.services.skill_extractor import SkillExtractor


def test_taxonomy_loading():
    """Verify that the skills taxonomy loads categories and skills properly."""
    extractor = SkillExtractor.get_instance()
    assert len(extractor._taxonomy) >= 5
    assert "programming_languages" in extractor._taxonomy
    assert "databases" in extractor._taxonomy
    assert "backend" in extractor._taxonomy


def test_exact_and_alias_skill_extraction():
    """Verify exact, case-insensitive, and alias-based skill identification."""
    extractor = SkillExtractor.get_instance()
    sample_text = """
    Software Engineer with deep experience in Python, postgres, and k8s.
    Built scalable microservices using FastAPI, Redis, and Docker.
    Familiar with TypeScript, React.js, and AWS EC2.
    """
    skills = extractor.extract_skills(sample_text)
    detected_names = {s.skill_name for s in skills}

    assert "Python" in detected_names
    assert "PostgreSQL" in detected_names  # alias 'postgres' -> 'PostgreSQL'
    assert "Kubernetes" in detected_names  # alias 'k8s' -> 'Kubernetes'
    assert "FastAPI" in detected_names
    assert "Redis" in detected_names
    assert "Docker" in detected_names
    assert "TypeScript" in detected_names
    assert "React" in detected_names  # alias 'React.js' -> 'React'
    assert "AWS" in detected_names  # alias 'AWS EC2' -> 'AWS'


def test_multi_word_skill_matching():
    """Verify that multi-word skills are extracted without partial collisions."""
    extractor = SkillExtractor.get_instance()
    sample_text = "Experienced in Natural Language Processing, Machine Learning, and RESTful APIs."
    skills = extractor.extract_skills(sample_text)
    detected_names = {s.skill_name for s in skills}

    assert "Natural Language Processing" in detected_names
    assert "Machine Learning" in detected_names


def test_experience_and_proficiency_detection():
    """Verify detecting years of experience and proficiency clues."""
    extractor = SkillExtractor.get_instance()
    sample_text = "Expert in Python with 6 years of experience building APIs. Advanced TypeScript developer."
    skills = extractor.extract_skills(sample_text)

    py_skill = next((s for s in skills if s.skill_name == "Python"), None)
    assert py_skill is not None
    assert py_skill.years_used == 6.0
    assert py_skill.proficiency in ("expert", "advanced")
