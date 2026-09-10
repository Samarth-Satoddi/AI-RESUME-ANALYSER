import io
import time
import pytest
from fastapi.testclient import TestClient

SAMPLE_RESUME_TEXT = """Jordan Taylor
jordan.taylor@example.com | 555-4321 | Bangalore, India
https://github.com/jordantaylor

SUMMARY
Passionate Backend Engineer with 3+ years of experience building distributed APIs in Python, FastAPI, and PostgreSQL.

SKILLS
Python, FastAPI, PostgreSQL, Docker, Redis, REST APIs, SQL, Git

EXPERIENCE
Backend Developer | CloudTech Labs | 2021 - Present
- Designed and maintained scalable RESTful web APIs using Python and FastAPI.
- Optimized relational database indexing on PostgreSQL, improving query response time by 45%.
- Implemented asynchronous task workers using Celery and Redis message queues.

EDUCATION
B.Tech in Computer Science | National Institute of Technology | 2017 - 2021
"""


@pytest.fixture
def auth_user_a(client: TestClient):
    email = "agent.tester.a@example.com"
    pw = "SecurePass123!"
    client.post("/api/v1/auth/register", json={"email": email, "password": pw, "full_name": "Tester A"})
    token = client.post("/api/v1/auth/login", json={"email": email, "password": pw}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def auth_user_b(client: TestClient):
    email = "agent.tester.b@example.com"
    pw = "SecurePass123!"
    client.post("/api/v1/auth/register", json={"email": email, "password": pw, "full_name": "Tester B"})
    token = client.post("/api/v1/auth/login", json={"email": email, "password": pw}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def user_a_resume(client: TestClient, auth_user_a: dict):
    # Upload text resume
    file_bytes = io.BytesIO(SAMPLE_RESUME_TEXT.encode("utf-8"))
    files = {"file": ("jordan_resume.txt", file_bytes, "text/plain")}
    resp = client.post("/api/v1/resumes/upload", files=files, headers=auth_user_a)
    assert resp.status_code == 201
    return resp.json()["id"]


def test_search_defaults_endpoint(client: TestClient, auth_user_a: dict, user_a_resume: str):
    """Verify smart search defaults inferred from candidate resume and profile."""
    resp = client.get("/api/v1/job-search/defaults", headers=auth_user_a)
    assert resp.status_code == 200
    data = resp.json()
    assert "target_role" in data
    assert "skills" in data
    assert data["recommended_resume_id"] == user_a_resume


def test_job_search_end_to_end_flow(client: TestClient, auth_user_a: dict, user_a_resume: str):
    """
    End-to-end integration test:
    1. Start automated search
    2. Poll status until completed
    3. Retrieve ranked opportunities
    4. Verify explainability (matched & missing skills, AI explanation)
    5. Save a job & update application tracking status
    6. Verify saved list
    """
    # 1. Start search
    search_payload = {
        "role": "Python Backend Developer",
        "location": "Bangalore",
        "remote": True,
        "experience": "0-2 years",
        "resume_id": user_a_resume,
        "posted_within_days": 14,
        "limit": 10,
    }
    init_resp = client.post("/api/v1/job-search/search?sync=true", json=search_payload, headers=auth_user_a)
    assert init_resp.status_code == 202
    search_data = init_resp.json()
    search_id = search_data["search_id"]
    assert search_id

    # 2. Poll until completed (runs synchronously or via fast background execution)
    status_data = None
    for _ in range(15):
        poll_resp = client.get(f"/api/v1/job-search/searches/{search_id}", headers=auth_user_a)
        assert poll_resp.status_code == 200
        status_data = poll_resp.json()
        if status_data["status"] in {"completed", "failed"}:
            break
        time.sleep(0.5)

    assert status_data["status"] == "completed"
    assert status_data["jobs_found"] > 0
    assert status_data["jobs_matched"] > 0

    # 3. Retrieve ranked results
    res_resp = client.get(f"/api/v1/job-search/searches/{search_id}/results", headers=auth_user_a)
    assert res_resp.status_code == 200
    results_payload = res_resp.json()
    assert results_payload["total_results"] > 0

    top_job = results_payload["results"][0]
    assert top_job["rank"] == 1
    assert top_job["overall_match_score"] > 0
    assert top_job["skill_score"] > 0
    assert top_job["url"].startswith("http")
    assert top_job["ai_explanation"] is not None
    assert len(top_job["matched_skills"]) > 0

    # 4. Filter & sort tests
    sorted_resp = client.get(
        f"/api/v1/job-search/searches/{search_id}/results?sort_by=highest_skill",
        headers=auth_user_a,
    )
    assert sorted_resp.status_code == 200
    sorted_items = sorted_resp.json()["results"]
    assert sorted_items[0]["skill_score"] >= sorted_items[-1]["skill_score"]

    # 5. Save job bookmark
    listing_id = top_job["listing_id"]
    save_resp = client.post(f"/api/v1/job-search/jobs/{listing_id}/save", headers=auth_user_a)
    assert save_resp.status_code == 201
    assert save_resp.json()["status"] == "saved"

    # 6. Update application status to 'applied'
    status_patch = client.patch(
        f"/api/v1/job-search/jobs/{listing_id}/status",
        json={"status": "applied", "notes": "Submitted application via referral."},
        headers=auth_user_a,
    )
    assert status_patch.status_code == 200
    assert status_patch.json()["status"] == "applied"
    assert status_patch.json()["notes"] == "Submitted application via referral."

    # 7. Check saved jobs list
    saved_list = client.get("/api/v1/job-search/saved", headers=auth_user_a)
    assert saved_list.status_code == 200
    saved_items = saved_list.json()
    assert any(s["job_listing_id"] == listing_id and s["status"] == "applied" for s in saved_items)

    # 8. Check top recommendations
    recs_resp = client.get("/api/v1/job-search/top-recommendations", headers=auth_user_a)
    assert recs_resp.status_code == 200
    assert len(recs_resp.json()) > 0

    # 9. Unsave job
    unsave_resp = client.delete(f"/api/v1/job-search/jobs/{listing_id}/save", headers=auth_user_a)
    assert unsave_resp.status_code == 200


def test_tenant_isolation_and_ownership(
    client: TestClient,
    auth_user_a: dict,
    auth_user_b: dict,
    user_a_resume: str,
):
    """Verify User B cannot access or tamper with User A's job searches or saved jobs."""
    # User A starts a search
    resp_a = client.post(
        "/api/v1/job-search/search",
        json={"role": "Python Engineer", "resume_id": user_a_resume},
        headers=auth_user_a,
    )
    search_id = resp_a.json()["search_id"]

    # User B tries to access User A's search status -> Must return 404
    resp_b_status = client.get(f"/api/v1/job-search/searches/{search_id}", headers=auth_user_b)
    assert resp_b_status.status_code == 404

    # User B tries to view User A's results -> Must return 404
    resp_b_results = client.get(f"/api/v1/job-search/searches/{search_id}/results", headers=auth_user_b)
    assert resp_b_results.status_code == 404
