from datetime import timedelta
import uuid
import pytest
from app.core.security import create_access_token, decode_access_token, verify_password
from app.core.exceptions import ForbiddenError
from app.api.deps import verify_resource_ownership
from app.db.models import User, Profile


def test_registration_successful(client):
    """Test successful user registration with auto-provisioned profile."""
    payload = {
        "email": "sarah.connor@example.com",
        "password": "SecurePassword123!",
        "full_name": "Sarah Connor",
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "sarah.connor@example.com"
    assert data["is_active"] is True
    assert data["is_verified"] is False
    assert "id" in data
    assert "hashed_password" not in data
    assert "password" not in data


def test_registration_duplicate_email(client):
    """Test that duplicate email registration returns a 400 bad request error."""
    payload = {
        "email": "duplicate.user@example.com",
        "password": "SecurePassword123!",
        "full_name": "Original User",
    }
    r1 = client.post("/api/v1/auth/register", json=payload)
    assert r1.status_code == 201

    # Attempt duplicate registration
    r2 = client.post("/api/v1/auth/register", json=payload)
    assert r2.status_code == 400
    assert "already exists" in r2.json()["message"]


def test_registration_weak_password(client):
    """Test that weak or too-short passwords are rejected by validation."""
    # Too short (< 8 chars)
    r1 = client.post("/api/v1/auth/register", json={
        "email": "short@example.com",
        "password": "short",
        "full_name": "Short Pass",
    })
    assert r1.status_code == 422

    # Trivial password
    r2 = client.post("/api/v1/auth/register", json={
        "email": "trivial@example.com",
        "password": "password",
        "full_name": "Trivial Pass",
    })
    assert r2.status_code == 422


def test_login_successful_and_jwt_generation(client):
    """Test login returns access token and refresh token."""
    # Register
    client.post("/api/v1/auth/register", json={
        "email": "login.test@example.com",
        "password": "ValidPassword999",
        "full_name": "Login Tester",
    })

    # Login with JSON
    response = client.post("/api/v1/auth/login", json={
        "email": "login.test@example.com",
        "password": "ValidPassword999",
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["expires_in"] > 0
    assert "refresh_token" in data

    # Verify access token payload claims
    token_claims = decode_access_token(data["access_token"])
    assert "sub" in token_claims
    assert token_claims["type"] == "access"


def test_login_incorrect_credentials(client):
    """Test login rejection for bad password or nonexistent user."""
    # Nonexistent user
    r1 = client.post("/api/v1/auth/login", json={
        "email": "nonexistent@example.com",
        "password": "AnyPassword123",
    })
    assert r1.status_code == 401

    # Register user
    client.post("/api/v1/auth/register", json={
        "email": "wrong.pass@example.com",
        "password": "CorrectPassword123",
        "full_name": "User",
    })

    # Wrong password
    r2 = client.post("/api/v1/auth/login", json={
        "email": "wrong.pass@example.com",
        "password": "IncorrectPassword123",
    })
    assert r2.status_code == 401


def test_current_user_me_endpoint(client):
    """Test GET /api/v1/auth/me returns current user profile."""
    # Register & Login
    client.post("/api/v1/auth/register", json={
        "email": "me.endpoint@example.com",
        "password": "SecurePassword123",
        "full_name": "Me Endpoint User",
    })
    login_res = client.post("/api/v1/auth/login", json={
        "email": "me.endpoint@example.com",
        "password": "SecurePassword123",
    })
    token = login_res.json()["access_token"]

    # Unauthenticated request fails
    r_unauth = client.get("/api/v1/auth/me")
    assert r_unauth.status_code == 401

    # Authenticated request succeeds
    r_auth = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r_auth.status_code == 200
    user_data = r_auth.json()
    assert user_data["email"] == "me.endpoint@example.com"
    assert "hashed_password" not in user_data


def test_profile_retrieval_and_update(client):
    """Test candidate career profile retrieval and update endpoints."""
    # Register & Login
    client.post("/api/v1/auth/register", json={
        "email": "profile.tester@example.com",
        "password": "SecurePassword123",
        "full_name": "Profile Tester",
    })
    login_res = client.post("/api/v1/auth/login", json={
        "email": "profile.tester@example.com",
        "password": "SecurePassword123",
    })
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # GET profile
    get_res = client.get("/api/v1/profile", headers=headers)
    assert get_res.status_code == 200
    assert get_res.json()["full_name"] == "Profile Tester"

    # PUT profile update
    update_payload = {
        "full_name": "Profile Tester, M.Sc.",
        "target_role": "Principal ML Engineer",
        "years_of_experience": 8.5,
        "location": "San Francisco, CA",
        "linkedin_url": "https://linkedin.com/in/profiletester",
        "github_url": "https://github.com/profiletester",
    }
    put_res = client.put("/api/v1/profile", json=update_payload, headers=headers)
    assert put_res.status_code == 200
    data = put_res.json()
    assert data["full_name"] == "Profile Tester, M.Sc."
    assert data["target_role"] == "Principal ML Engineer"
    assert data["years_of_experience"] == 8.5
    assert data["location"] == "San Francisco, CA"
    assert data["linkedin_url"] == "https://linkedin.com/in/profiletester"


def test_profile_update_invalid_url(client):
    """Test URL validation on profile update."""
    client.post("/api/v1/auth/register", json={
        "email": "url.val@example.com",
        "password": "SecurePassword123",
        "full_name": "Url Val",
    })
    token = client.post("/api/v1/auth/login", json={
        "email": "url.val@example.com",
        "password": "SecurePassword123",
    }).json()["access_token"]

    # Invalid URL scheme
    res = client.put(
        "/api/v1/profile",
        json={"linkedin_url": "javascript:alert('xss')"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 422


def test_token_refresh_and_revocation(client):
    """Test session refresh and logout token revocation."""
    # Register & Login
    client.post("/api/v1/auth/register", json={
        "email": "refresh.test@example.com",
        "password": "SecurePassword123",
        "full_name": "Refresh Tester",
    })
    login_res = client.post("/api/v1/auth/login", json={
        "email": "refresh.test@example.com",
        "password": "SecurePassword123",
    })
    tokens = login_res.json()
    refresh_token = tokens["refresh_token"]

    # Successful refresh
    refresh_res = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert refresh_res.status_code == 200
    new_tokens = refresh_res.json()
    assert "access_token" in new_tokens
    new_refresh_token = new_tokens["refresh_token"]

    # Old refresh token should now be revoked (single-use rotation)
    reuse_res = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert reuse_res.status_code == 401

    # Logout with active new refresh token
    logout_res = client.post("/api/v1/auth/logout", json={"refresh_token": new_refresh_token})
    assert logout_res.status_code == 200

    # Using revoked token after logout fails
    after_logout = client.post("/api/v1/auth/refresh", json={"refresh_token": new_refresh_token})
    assert after_logout.status_code == 401


def test_change_password(client):
    """Test password rotation and subsequent login with new password."""
    email = "pass.change@example.com"
    old_pw = "OldPassword123"
    new_pw = "BrandNewPassword456"

    client.post("/api/v1/auth/register", json={
        "email": email,
        "password": old_pw,
        "full_name": "Pass Change",
    })
    token = client.post("/api/v1/auth/login", json={
        "email": email,
        "password": old_pw,
    }).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Wrong current password fails
    r_fail = client.post(
        "/api/v1/auth/change-password",
        json={"current_password": "WrongOldPassword", "new_password": new_pw},
        headers=headers,
    )
    assert r_fail.status_code == 401

    # Correct current password succeeds
    r_succ = client.post(
        "/api/v1/auth/change-password",
        json={"current_password": old_pw, "new_password": new_pw},
        headers=headers,
    )
    assert r_succ.status_code == 200

    # Old password no longer works
    r_old = client.post("/api/v1/auth/login", json={"email": email, "password": old_pw})
    assert r_old.status_code == 401

    # New password works
    r_new = client.post("/api/v1/auth/login", json={"email": email, "password": new_pw})
    assert r_new.status_code == 200


def test_ownership_authorization_guard():
    """Verify that verify_resource_ownership blocks cross-user access even with known UUID."""
    user_a = User(id=uuid.uuid4(), email="userA@example.com", hashed_password="pw")
    user_b_id = uuid.uuid4()

    # User A attempting to access User B's resource must raise ForbiddenError
    with pytest.raises(ForbiddenError):
        verify_resource_ownership(resource_owner_id=user_b_id, current_user=user_a)

    # User A accessing User A's resource must succeed
    verify_resource_ownership(resource_owner_id=user_a.id, current_user=user_a)
