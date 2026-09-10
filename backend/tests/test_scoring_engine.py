import pytest
from app.services.scoring_engine import ScoringEngine


def test_scoring_engine_deterministic_calculation():
    """Verify that scoring is strictly deterministic and mathematical."""
    skills = [
        type("Skill", (), {"category": "programming_languages"}),
        type("Skill", (), {"category": "databases"}),
        type("Skill", (), {"category": "backend"}),
        type("Skill", (), {"category": "cloud"}),
    ]
    experiences = [
        type("Exp", (), {"company": "Tech", "job_title": "Dev"}),
        type("Exp", (), {"company": "Data", "job_title": "Senior"}),
    ]
    sections = [
        type("Sec", (), {"section_type": "summary"}),
        type("Sec", (), {"section_type": "skills"}),
        type("Sec", (), {"section_type": "experience"}),
        type("Sec", (), {"section_type": "education"}),
    ]
    contact = {"email": "alex@example.com", "phone": "555-1234", "linkedin_url": "linkedin.com/in/alex"}
    text = "Architected and optimized distributed APIs reducing latency by 45% for 10M daily users."

    res1 = ScoringEngine.evaluate_resume(skills, experiences, [], [], sections, contact, text)
    res2 = ScoringEngine.evaluate_resume(skills, experiences, [], [], sections, contact, text)

    # Determinism check
    assert res1.overall_score == res2.overall_score
    assert res1.ats_score == res2.ats_score
    assert res1.experience_score == res2.experience_score
    assert res1.overall_score > 50.0
    assert res1.ats_score > 50.0
    assert len(res1.strengths) > 0
    assert len(res1.recommendations) > 0
