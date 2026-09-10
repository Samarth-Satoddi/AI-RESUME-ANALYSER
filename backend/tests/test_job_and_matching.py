import pytest
from fastapi.testclient import TestClient


SAMPLE_JOB = {
    "title": "Senior Python Backend Engineer",
    "company": "NextGen Cloud",
    "description": """We are seeking an experienced Senior Backend Engineer.
    Requirements:
    - 5+ years of experience in backend development.
    - Strong proficiency in Python, FastAPI, and PostgreSQL.
    - Experience building microservices with Docker and Redis.
    Preferred Qualifications:
    - Experience with Kubernetes and AWS.
    - Knowledge of GraphQL.
    """,
}

SAMPLE_RESUME = """Alex Morgan
alex.morgan@example.com | 555-0192 | Seattle, WA
https://linkedin.com/in/alexmorgan | https://github.com/alexmorgan

PROFESSIONAL SUMMARY
Senior Software Engineer with 6+ years of expertise in Python, FastAPI, and PostgreSQL.

SKILLS
Python, FastAPI, PostgreSQL, Docker, Redis, SQL, RESTful APIs

WORK EXPERIENCE
Lead Engineer | CloudScale | 2020 - Present
- Architected high-throughput microservices using Python and FastAPI.
- Optimized database queries resulting in 40% latency reduction for 5M users.

EDUCATION
BS in Computer Science, University of Washington | 2016 - 2020
"""


@pytest.fixture
def auth_candidate_a(client: TestClient):
    email = "candidate.a@example.com"
    pw = "SecurePass123!"
    client.post("/api/v1/auth/register", json={"email": email, "password": pw, "full_name": "Candidate A"})
    token = client.post("/api/v1/auth/login", json={"email": email, "password": pw}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def auth_candidate_b(client: TestClient):
    email = "candidate.b@example.com"
    pw = "SecurePass123!"
    client.post("/api/v1/auth/register", json={"email": email, "password": pw, "full_name": "Candidate B"})
    token = client.post("/api/v1/auth/login", json={"email": email, "password": pw}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_job_create_and_parse_requirements(client: TestClient, auth_candidate_a: dict):
    """Verify job creation and requirement deconstruction."""
    resp = client.post("/api/v1/jobs", json=SAMPLE_JOB, headers=auth_candidate_a)
    assert resp.status_code == 201
    data = resp.json()

    assert data["title"] == "Senior Python Backend Engineer"
    assert len(data["requirements"]) >= 3

    req_skills = [r["normalized_skill_name"] for r in data["requirements"] if r["requirement_type"] == "skill"]
    assert "python" in req_skills
    assert "fastapi" in req_skills
    assert "postgresql" in req_skills


def test_job_ownership_isolation(client: TestClient, auth_candidate_a: dict, auth_candidate_b: dict):
    """Candidate B cannot view or delete Candidate A's job."""
    resp = client.post("/api/v1/jobs", json=SAMPLE_JOB, headers=auth_candidate_a)
    job_id = resp.json()["id"]

    get_resp = client.get(f"/api/v1/jobs/{job_id}", headers=auth_candidate_b)
    assert get_resp.status_code == 404

    del_resp = client.delete(f"/api/v1/jobs/{job_id}", headers=auth_candidate_b)
    assert del_resp.status_code == 404


def test_end_to_end_analysis_and_matching(client: TestClient, auth_candidate_a: dict):
    """Verify end-to-end flow: Upload resume -> Create Job -> Run Analysis -> Check Match -> Check Roadmap & Interview Qs."""
    # 1. Upload resume
    upload_resp = client.post(
        "/api/v1/resumes/upload",
        headers=auth_candidate_a,
        files={"file": ("alex.txt", SAMPLE_RESUME.encode("utf-8"), "text/plain")},
    )
    assert upload_resp.status_code == 201
    resume_id = upload_resp.json()["id"]

    # 2. Create job
    job_resp = client.post("/api/v1/jobs", json=SAMPLE_JOB, headers=auth_candidate_a)
    assert job_resp.status_code == 201
    job_id = job_resp.json()["id"]

    # 3. Run full matching analysis
    analysis_resp = client.post(
        "/api/v1/analyses",
        json={"resume_id": resume_id, "job_id": job_id},
        headers=auth_candidate_a,
    )
    assert analysis_resp.status_code == 201
    analysis_data = analysis_resp.json()

    assert analysis_data["overall_score"] > 50.0
    assert analysis_data["ats_score"] > 50.0
    assert "Python" in analysis_data["matched_skills"] or "FastAPI" in analysis_data["matched_skills"]
    assert analysis_data["roadmap_item_count"] > 0
    assert analysis_data["interview_question_count"] > 0

    analysis_id = analysis_data["analysis_id"]

    # 4. Fetch roadmap
    roadmap_resp = client.get(f"/api/v1/analyses/{analysis_id}/roadmap", headers=auth_candidate_a)
    assert roadmap_resp.status_code == 200
    roadmap_data = roadmap_resp.json()
    assert len(roadmap_data["items"]) > 0

    # 5. Fetch interview questions
    interview_resp = client.get(f"/api/v1/analyses/{analysis_id}/interview", headers=auth_candidate_a)
    assert interview_resp.status_code == 200
    questions = interview_resp.json()
    assert len(questions) >= 3

    # 6. Check historical list
    history_resp = client.get("/api/v1/analyses", headers=auth_candidate_a)
    assert history_resp.status_code == 200
    assert len(history_resp.json()) >= 1


def test_resume_standalone_score(client: TestClient, auth_candidate_a: dict):
    """Verify calculating resume quality & ATS evaluation without requiring a job."""
    upload_resp = client.post(
        "/api/v1/resumes/upload",
        headers=auth_candidate_a,
        files={"file": ("alex2.txt", SAMPLE_RESUME.encode("utf-8"), "text/plain")},
    )
    resume_id = upload_resp.json()["id"]

    score_resp = client.get(f"/api/v1/resumes/{resume_id}/score", headers=auth_candidate_a)
    assert score_resp.status_code == 200
    score_data = score_resp.json()

    assert score_data["overall_score"] > 50.0
    assert score_data["ats_score"] > 50.0
    assert len(score_data["strengths"]) > 0


def test_ai_bullet_enhancer(client: TestClient, auth_candidate_a: dict):
    """Verify AI bullet point refactoring endpoint."""
    resp = client.post(
        "/api/v1/ai/improve-bullet",
        json={"bullet": "Worked on backend APIs with Python and SQL.", "target_role": "Senior Engineer"},
        headers=auth_candidate_a,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "Spearheaded" in data["improved"] or "Architected" in data["improved"]
    assert len(data["rationale"]) > 10
