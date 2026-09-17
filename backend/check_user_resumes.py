import httpx

def check():
    client = httpx.Client(base_url="http://127.0.0.1:8000")
    login_resp = client.post("/api/v1/auth/login", json={"email": "samarth@gmail.com", "password": "password123"})
    token = login_resp.json().get("access_token")
    if not token:
        print(f"Login failed: {login_resp.text}")
        return

    headers = {"Authorization": f"Bearer {token}"}
    res = client.get("/api/v1/resumes", headers=headers).json()
    print(f"User Resumes in API ({res['total']}):")
    for r in res["items"]:
        print(f"ID: {r['id']}")
        print(f"  Name: {r['name']}")
        print(f"  Original filename: {r['original_filename']}")
        print(f"  File type: {r['file_type']} | Version: v{r['version_number']}")
        print(f"  Parser status: {r['parser_status']}")
        print(f"  Primary: {r['is_primary']}")
        print(f"  Sections count: {r['sections_count']}")
        print(f"  Skills count: {r['skills_count']}")
        print(f"  Created at: {r['created_at']}")
        print("-" * 50)

if __name__ == "__main__":
    check()
