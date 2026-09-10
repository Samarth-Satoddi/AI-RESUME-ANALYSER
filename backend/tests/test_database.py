import uuid
import pytest
from sqlalchemy.exc import IntegrityError
from app.db.base import Base
from app.db.models import (
    User,
    Profile,
    Resume,
    ResumeVersion,
    ResumeSection,
    ResumeSkill,
    Experience,
    Education,
    Project,
    Certification,
    JobDescription,
    JobRequirement,
    Analysis,
    SkillMatch,
    MissingSkill,
    Recommendation,
    LearningRoadmap,
    LearningRoadmapItem,
    InterviewQuestion,
)


def test_alembic_metadata_registered_tables():
    """Verify that all 19 required tables are registered in SQLAlchemy Base.metadata."""
    expected_tables = {
        "users",
        "profiles",
        "resumes",
        "resume_versions",
        "resume_sections",
        "resume_skills",
        "experiences",
        "educations",
        "projects",
        "certifications",
        "job_descriptions",
        "job_requirements",
        "analyses",
        "skill_matches",
        "missing_skills",
        "recommendations",
        "learning_roadmaps",
        "learning_roadmap_items",
        "interview_questions",
    }
    actual_tables = set(Base.metadata.tables.keys())
    assert expected_tables.issubset(actual_tables), f"Missing tables: {expected_tables - actual_tables}"


def test_user_and_profile_relationship(db_session):
    """Test User creation and 1-to-1 relationship with Profile."""
    user = User(
        email="candidate@example.com",
        hashed_password="hashed_secure_password_123",
        is_active=True,
        is_verified=True,
    )
    profile = Profile(
        user=user,
        full_name="Alex Mercer",
        target_role="Senior Backend Engineer",
        years_of_experience=6.5,
        location="Remote",
    )
    db_session.add(user)
    db_session.add(profile)
    db_session.commit()

    retrieved = db_session.query(User).filter_by(email="candidate@example.com").first()
    assert retrieved is not None
    assert retrieved.profile is not None
    assert retrieved.profile.full_name == "Alex Mercer"
    assert retrieved.profile.years_of_experience == 6.5
    assert retrieved.profile.user.id == retrieved.id


def test_user_unique_email_constraint(db_session):
    """Test that duplicate emails violate unique constraint."""
    user1 = User(
        email="duplicate@example.com",
        hashed_password="pw1",
    )
    db_session.add(user1)
    db_session.commit()

    user2 = User(
        email="duplicate@example.com",
        hashed_password="pw2",
    )
    db_session.add(user2)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_resume_and_version_relationship(db_session):
    """Test Resume creation and 1-to-many relationship with ResumeVersion."""
    user = User(
        email="resume_test@example.com",
        hashed_password="pw",
    )
    resume = Resume(
        user=user,
        name="Software Engineer Resume",
        original_filename="alex_mercer.pdf",
        file_type="application/pdf",
        file_size=204800,
        storage_path="/uploads/alex_mercer.pdf",
        is_primary=True,
    )
    v1 = ResumeVersion(
        resume=resume,
        version_number=1,
        extracted_text="Experience at TechCorp...",
        parser_status="completed",
    )
    v2 = ResumeVersion(
        resume=resume,
        version_number=2,
        extracted_text="Updated experience with AWS...",
        parser_status="completed",
    )
    db_session.add_all([user, resume, v1, v2])
    db_session.commit()

    retrieved = db_session.query(Resume).filter_by(id=resume.id).first()
    assert len(retrieved.versions) == 2
    assert retrieved.versions[0].version_number == 1
    assert retrieved.versions[1].version_number == 2


def test_resume_version_unique_constraint(db_session):
    """Test that version_number is unique per resume."""
    user = User(email="version_constraint@example.com", hashed_password="pw")
    resume = Resume(
        user=user,
        name="Resume",
        original_filename="res.pdf",
        file_type="application/pdf",
        file_size=1000,
        storage_path="/path",
    )
    v1 = ResumeVersion(resume=resume, version_number=1)
    v1_dup = ResumeVersion(resume=resume, version_number=1)
    db_session.add_all([user, resume, v1, v1_dup])

    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_resume_version_child_entities(db_session):
    """Test ResumeVersion children: sections, skills, experience, education, projects, certifications."""
    user = User(email="full_resume@example.com", hashed_password="pw")
    resume = Resume(
        user=user,
        name="Full Profile",
        original_filename="doc.pdf",
        file_type="application/pdf",
        file_size=5000,
        storage_path="/path",
    )
    version = ResumeVersion(resume=resume, version_number=1)

    section = ResumeSection(resume_version=version, section_type="skills", content="Python, FastAPI", section_order=1)
    skill = ResumeSkill(
        resume_version=version,
        skill_name="FastAPI",
        normalized_skill_name="fastapi",
        category="backend",
        proficiency="expert",
        years_used=4.0,
    )
    exp = Experience(
        resume_version=version,
        company="Stripe",
        job_title="Software Engineer",
        is_current=True,
        description="Built payment APIs",
    )
    edu = Education(
        resume_version=version,
        institution="MIT",
        degree="B.S. in Computer Science",
        field_of_study="Computer Science",
    )
    proj = Project(
        resume_version=version,
        name="OpenAPI Parser",
        technologies=["Python", "FastAPI"],
        github_url="https://github.com/example/parser",
    )
    cert = Certification(
        resume_version=version,
        name="AWS Certified Solutions Architect",
        issuing_organization="Amazon Web Services",
    )

    db_session.add_all([user, resume, version, section, skill, exp, edu, proj, cert])
    db_session.commit()

    ver = db_session.query(ResumeVersion).filter_by(id=version.id).first()
    assert len(ver.sections) == 1
    assert len(ver.skills) == 1
    assert ver.skills[0].normalized_skill_name == "fastapi"
    assert len(ver.experiences) == 1
    assert ver.experiences[0].company == "Stripe"
    assert len(ver.education) == 1
    assert len(ver.projects) == 1
    assert len(ver.certifications) == 1
    assert ver.certifications[0].name == "AWS Certified Solutions Architect"


def test_job_description_and_requirements(db_session):
    """Test JobDescription and 1-to-many relationship with JobRequirement."""
    user = User(email="recruiter@example.com", hashed_password="pw")
    job = JobDescription(
        user=user,
        title="Staff Backend Engineer",
        company="Datadog",
        description="Looking for an experienced distributed systems engineer...",
    )
    req1 = JobRequirement(
        job_description=job,
        requirement_type="technical_skill",
        requirement_text="Proficiency in Python and Go",
        normalized_skill_name="python",
        category="programming_languages",
        is_required=True,
        years_required=5.0,
    )
    req2 = JobRequirement(
        job_description=job,
        requirement_type="technical_skill",
        requirement_text="Experience with Kubernetes",
        normalized_skill_name="kubernetes",
        category="devops",
        is_required=False,
    )
    db_session.add_all([user, job, req1, req2])
    db_session.commit()

    retrieved = db_session.query(JobDescription).filter_by(id=job.id).first()
    assert len(retrieved.requirements) == 2
    required_skills = [r.normalized_skill_name for r in retrieved.requirements if r.is_required]
    assert "python" in required_skills


def test_analysis_complete_relationships(db_session):
    """Test Analysis model with all child relationships (SkillMatch, MissingSkill, Recommendation, LearningRoadmap, InterviewQuestion)."""
    user = User(email="analysis_test@example.com", hashed_password="pw")
    resume = Resume(
        user=user,
        name="Analyst Resume",
        original_filename="res.pdf",
        file_type="application/pdf",
        file_size=1000,
        storage_path="/path",
    )
    version = ResumeVersion(resume=resume, version_number=1)
    job = JobDescription(user=user, title="Python Dev", description="Python backend")

    analysis = Analysis(
        user=user,
        resume_version=version,
        job_description=job,
        status="completed",
        overall_score=88.5,
        resume_score=85.0,
        ats_score=82.0,
        skill_score=90.0,
        semantic_score=85.0,
        experience_score=90.0,
    )

    skill_match = SkillMatch(
        analysis=analysis,
        skill_name="FastAPI",
        match_type="strong",
        similarity_score=1.0,
    )
    missing_skill = MissingSkill(
        analysis=analysis,
        skill_name="Kubernetes",
        priority="high",
        reason="Required for deployment pipeline",
    )
    rec = Recommendation(
        analysis=analysis,
        recommendation_type="impact",
        title="Quantify Project Outcomes",
        description="Add concrete metrics to your Stripe experience bullets.",
        priority="high",
    )
    roadmap = LearningRoadmap(
        analysis=analysis,
        title="Kubernetes & Cloud Readiness",
        estimated_days=21,
    )
    roadmap_item = LearningRoadmapItem(
        learning_roadmap=roadmap,
        skill_name="Kubernetes",
        topic="Pods, Deployments, and Services",
        estimated_days=7,
        order_index=1,
    )
    interview_q = InterviewQuestion(
        analysis=analysis,
        category="technical",
        question="How does ASGI concurrency work in FastAPI compared to WSGI?",
        difficulty="hard",
        why_it_matters="Assesses deep understanding of Python async internals",
    )

    db_session.add_all([
        user, resume, version, job, analysis,
        skill_match, missing_skill, rec, roadmap, roadmap_item, interview_q,
    ])
    db_session.commit()

    retrieved = db_session.query(Analysis).filter_by(id=analysis.id).first()
    assert retrieved.overall_score == 88.5
    assert len(retrieved.skill_matches) == 1
    assert len(retrieved.missing_skills) == 1
    assert len(retrieved.recommendations) == 1
    assert retrieved.learning_roadmap is not None
    assert len(retrieved.learning_roadmap.items) == 1
    assert len(retrieved.interview_questions) == 1


def test_cascade_delete_user(db_session):
    """Test that deleting a User cascades to its Profile, Resumes, and JobDescriptions."""
    user = User(email="delete_cascade@example.com", hashed_password="pw")
    profile = Profile(user=user, full_name="Delete Me")
    resume = Resume(
        user=user,
        name="Resume",
        original_filename="f.pdf",
        file_type="application/pdf",
        file_size=100,
        storage_path="/p",
    )
    version = ResumeVersion(resume=resume, version_number=1)
    job = JobDescription(user=user, title="Job", description="Desc")

    db_session.add_all([user, profile, resume, version, job])
    db_session.commit()

    user_id = user.id
    resume_id = resume.id
    version_id = version.id

    # Delete User
    db_session.delete(user)
    db_session.commit()

    # Verify children are deleted
    assert db_session.query(Profile).filter_by(user_id=user_id).first() is None
    assert db_session.query(Resume).filter_by(id=resume_id).first() is None
    assert db_session.query(ResumeVersion).filter_by(id=version_id).first() is None
