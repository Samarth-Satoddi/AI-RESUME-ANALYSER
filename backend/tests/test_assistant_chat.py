import uuid
import pytest
from app.db.models.resume import Resume, ResumeVersion, ResumeSkill, ResumeSection
from app.db.models.user import User
from app.ai.intent.classifier import AssistantIntent
from app.ai.resume_context.builder import ResumeContextBuilder


@pytest.fixture
def test_user(db_session):
    user = User(
        id=uuid.uuid4(),
        email=f"candidate_{uuid.uuid4().hex[:6]}@example.com",
        hashed_password="hashedpassword123",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    return user


def test_resume_context_isolation(db_session, test_user):
    """
    Test 30: Resume Isolation Test.
    Resume A: Python, FastAPI, PostgreSQL
    Resume B: Java, Spring Boot, MySQL
    Context for Resume A must NOT include Resume B skills, and vice-versa.
    """
    # Create Resume A
    resume_a = Resume(
        id=uuid.uuid4(),
        user_id=test_user.id,
        name="Backend Python Resume",
        original_filename="python.pdf",
        file_type="application/pdf",
        file_size=1024,
        storage_path="/tmp/python.pdf",
    )
    db_session.add(resume_a)
    db_session.flush()

    ver_a = ResumeVersion(
        id=uuid.uuid4(),
        resume_id=resume_a.id,
        version_number=1,
        parser_status="completed",
    )
    db_session.add(ver_a)
    db_session.flush()

    skills_a = ["Python", "FastAPI", "PostgreSQL"]
    for s in skills_a:
        db_session.add(ResumeSkill(
            id=uuid.uuid4(),
            resume_version_id=ver_a.id,
            skill_name=s,
            normalized_skill_name=s.lower(),
            category="Backend",
        ))

    # Create Resume B
    resume_b = Resume(
        id=uuid.uuid4(),
        user_id=test_user.id,
        name="Enterprise Java Resume",
        original_filename="java.pdf",
        file_type="application/pdf",
        file_size=1024,
        storage_path="/tmp/java.pdf",
    )
    db_session.add(resume_b)
    db_session.flush()

    ver_b = ResumeVersion(
        id=uuid.uuid4(),
        resume_id=resume_b.id,
        version_number=1,
        parser_status="completed",
    )
    db_session.add(ver_b)
    db_session.flush()

    skills_b = ["Java", "Spring Boot", "MySQL"]
    for s in skills_b:
        db_session.add(ResumeSkill(
            id=uuid.uuid4(),
            resume_version_id=ver_b.id,
            skill_name=s,
            normalized_skill_name=s.lower(),
            category="Backend",
        ))

    db_session.commit()

    builder = ResumeContextBuilder(db=db_session, user_id=test_user.id)

    # Context for Resume A
    ctx_a = builder.build_context(resume_id=resume_a.id, intent=AssistantIntent.SKILL_QUESTION)
    assert "Python" in ctx_a["formatted_context"]
    assert "FastAPI" in ctx_a["formatted_context"]
    assert "PostgreSQL" in ctx_a["formatted_context"]
    assert "Java" not in ctx_a["formatted_context"]
    assert "Spring Boot" not in ctx_a["formatted_context"]

    # Context for Resume B
    ctx_b = builder.build_context(resume_id=resume_b.id, intent=AssistantIntent.SKILL_QUESTION)
    assert "Java" in ctx_b["formatted_context"]
    assert "Spring Boot" in ctx_b["formatted_context"]
    assert "MySQL" in ctx_b["formatted_context"]
    assert "Python" not in ctx_b["formatted_context"]
    assert "FastAPI" not in ctx_b["formatted_context"]


def test_anti_hallucination_context(db_session, test_user):
    """
    Test 31: Hallucination Test Context.
    Candidate only has Python & FastAPI.
    Context must NOT include Kubernetes, AWS, or Docker.
    """
    resume = Resume(
        id=uuid.uuid4(),
        user_id=test_user.id,
        name="Junior Python Dev",
        original_filename="junior.pdf",
        file_type="application/pdf",
        file_size=1024,
        storage_path="/tmp/junior.pdf",
    )
    db_session.add(resume)
    db_session.flush()

    ver = ResumeVersion(
        id=uuid.uuid4(),
        resume_id=resume.id,
        version_number=1,
        parser_status="completed",
    )
    db_session.add(ver)
    db_session.flush()

    for s in ["Python", "FastAPI"]:
        db_session.add(ResumeSkill(
            id=uuid.uuid4(),
            resume_version_id=ver.id,
            skill_name=s,
            normalized_skill_name=s.lower(),
            category="Backend",
        ))
    db_session.commit()

    builder = ResumeContextBuilder(db=db_session, user_id=test_user.id)
    ctx = builder.build_context(resume_id=resume.id, intent=AssistantIntent.SKILL_QUESTION)

    assert "Python" in ctx["skills"]
    assert "FastAPI" in ctx["skills"]
    assert "Kubernetes" not in ctx["skills"]
    assert "Docker" not in ctx["skills"]
    assert "AWS" not in ctx["skills"]


def test_ownership_security(db_session, test_user):
    """
    Section 28: Security.
    User A cannot access Resume belonging to User B.
    """
    other_user = User(
        id=uuid.uuid4(),
        email=f"other_{uuid.uuid4().hex[:6]}@example.com",
        hashed_password="hashedpassword123",
        is_active=True,
    )
    db_session.add(other_user)
    db_session.flush()

    resume = Resume(
        id=uuid.uuid4(),
        user_id=other_user.id,
        name="Confidential Resume",
        original_filename="other.pdf",
        file_type="application/pdf",
        file_size=1024,
        storage_path="/tmp/other.pdf",
    )
    db_session.add(resume)
    db_session.commit()

    builder = ResumeContextBuilder(db=db_session, user_id=test_user.id)
    with pytest.raises(ValueError, match="not found or access denied"):
        builder.build_context(resume_id=resume.id, intent=AssistantIntent.RESUME_QUESTION)


def test_actual_candidate_resume_grounding(db_session, test_user):
    """
    Test exact candidate resume from prompt:
    - Generative AI & Agentic Workflows
    - Python, Java, LLMs, RAG, LangChain, CrewAI, ChromaDB, Git & GitHub
    - Healthcare Assistant & Personal Smart Assistant
    - Jyothy Institute of Technology
    - ZERO work experience -> MUST NOT hallucinate WebCraft, Frontend Lead, React, or 3+ years
    """
    resume = Resume(
        id=uuid.uuid4(),
        user_id=test_user.id,
        name="Samarth GenAI Resume",
        original_filename="samarth_resume.pdf",
        file_type="application/pdf",
        file_size=2048,
        storage_path="/tmp/samarth_resume.pdf",
    )
    db_session.add(resume)
    db_session.flush()

    ver = ResumeVersion(
        id=uuid.uuid4(),
        resume_id=resume.id,
        version_number=1,
        parser_status="completed",
        extracted_text=(
            "SAMARTH SATODDI\n"
            "+91 7676098069 | samarthsatoddi@gmail.com\n"
            "SUMMARY\n"
            "Computer Science & Engineering student specializing in Generative AI and Agentic Workflows. "
            "Experienced in architecting RAG pipelines and multi-agent systems using CrewAI and LangChain.\n"
            "TECHNICAL SKILLS\n"
            "Programming Languages: Python, Java\n"
            "AI & Machine Learning: LLMs, RAG\n"
            "Frameworks & Libraries: LangChain, CrewAI\n"
            "Databases: ChromaDB\n"
            "Tools & Platforms: Git & GitHub\n"
            "Soft Skills: Teamwork, Problem Solving, Time Management\n"
            "PROJECTS\n"
            "Healthcare Assistant:\n"
            "- Architected a multi-agent system using CrewAI and LangChain, improving response accuracy by ~35%.\n"
            "- Developed an intelligent RAG pipeline with ChromaDB, reducing model hallucinations by ~25%.\n"
            "Personal Smart Assistant:\n"
            "- Architected a voice-enabled assistant utilizing AI Agents and Python, reducing manual effort by ~70%.\n"
            "EDUCATION\n"
            "B.E in Computer Science and Engineering (2024-2028), Jyothy Institute of Technology\n"
        ),
    )
    db_session.add(ver)
    db_session.flush()

    # Add sections
    db_session.add(ResumeSection(
        id=uuid.uuid4(),
        resume_version_id=ver.id,
        section_type="summary",
        content="Computer Science & Engineering student specializing in Generative AI and Agentic Workflows. Experienced in architecting RAG pipelines and multi-agent systems using CrewAI and LangChain.",
        section_order=1,
    ))
    db_session.add(ResumeSection(
        id=uuid.uuid4(),
        resume_version_id=ver.id,
        section_type="skills",
        content="Programming Languages: Python, Java\nAI & Machine Learning: LLMs, RAG\nFrameworks & Libraries: LangChain, CrewAI\nDatabases: ChromaDB\nTools & Platforms: Git & GitHub\nSoft Skills: Teamwork, Problem Solving, Time Management",
        section_order=2,
    ))
    db_session.add(ResumeSection(
        id=uuid.uuid4(),
        resume_version_id=ver.id,
        section_type="projects",
        content="Healthcare Assistant:\n- Architected a multi-agent system using CrewAI and LangChain, improving response accuracy by ~35%.\n- Developed an intelligent RAG pipeline with ChromaDB, reducing model hallucinations by ~25%.\nPersonal Smart Assistant:\n- Architected a voice-enabled assistant utilizing AI Agents and Python, reducing manual effort by ~70%.",
        section_order=3,
    ))
    db_session.add(ResumeSection(
        id=uuid.uuid4(),
        resume_version_id=ver.id,
        section_type="education",
        content="B.E in Computer Science and Engineering (2024-2028), Jyothy Institute of Technology",
        section_order=4,
    ))

    # Add skills
    for s in ["Python", "Java", "LLMs", "RAG", "LangChain", "CrewAI", "ChromaDB"]:
        db_session.add(ResumeSkill(
            id=uuid.uuid4(),
            resume_version_id=ver.id,
            skill_name=s,
            normalized_skill_name=s.lower(),
            category="AI/ML",
        ))

    db_session.commit()

    builder = ResumeContextBuilder(db=db_session, user_id=test_user.id)
    ctx = builder.build_context(resume_id=resume.id, intent=AssistantIntent.RESUME_QUESTION)
    formatted = ctx["formatted_context"]

    # Assert real data is present
    assert "SAMARTH SATODDI" in formatted
    assert "Generative AI and Agentic Workflows" in formatted
    assert "Python" in formatted
    assert "LangChain" in formatted
    assert "CrewAI" in formatted
    assert "ChromaDB" in formatted
    assert "Healthcare Assistant" in formatted
    assert "Personal Smart Assistant" in formatted
    assert "~35%" in formatted
    assert "~70%" in formatted
    assert "Jyothy Institute of Technology" in formatted

    # Assert zero hallucinated demo data
    assert "WebCraft" not in formatted
    assert "Frontend Lead" not in formatted
    assert "React" not in formatted
    assert "TypeScript" not in formatted
    assert "Node.js" not in formatted
    assert "Next.js" not in formatted
    assert "AWS" not in formatted
    assert "Docker" not in formatted
    assert "3+ years" not in formatted
    assert "NONE LISTED" in formatted
