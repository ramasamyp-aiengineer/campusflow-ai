from fastapi.testclient import TestClient

from app.config import get_settings
from app.database import SessionLocal
from app.models import AuthSession, User
from app.security.auth import _token_hash, hash_password, session_for, verify_password

ARJUN = {"email": "arjun@campusflow.edu", "password": "test-demo-pass"}


def _login(client: TestClient, email: str, password: str):
    return client.post("/api/v1/auth/login", json={"email": email, "password": password})


def _bearer(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_passwords_are_salted_scrypt_hashes():
    first, second = hash_password("CampusFlow@2026"), hash_password("CampusFlow@2026")
    assert first != second
    assert first.startswith("scrypt$") and "CampusFlow" not in first
    assert verify_password("CampusFlow@2026", first)
    assert not verify_password("campusflow@2026", first)
    assert not verify_password("anything", "not-a-hash")


def test_wrong_password_and_unknown_email_get_the_same_answer(client: TestClient):
    wrong = _login(client, ARJUN["email"], "guess")
    unknown = _login(client, "nobody@campusflow.edu", "guess")
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json()["detail"] == unknown.json()["detail"]
    assert "token" not in wrong.json()


def test_login_returns_a_session_that_decides_the_role(client: TestClient):
    response = _login(client, " Arjun@CampusFlow.edu ", ARJUN["password"])
    assert response.status_code == 200
    body = response.json()
    assert body["user"]["persona"] == "student" and body["user"]["name"] == "Arjun K."
    token = body["token"]

    assert client.get("/api/v1/auth/me", headers=_bearer(token)).json()["email"] == ARJUN["email"]
    assert client.get("/api/v1/dashboard", headers=_bearer(token)).status_code == 200
    spoofed = {**_bearer(token), "X-Persona": "faculty"}
    assert client.get("/api/v1/faculty/cohort-health", headers=spoofed).status_code == 403

    with SessionLocal() as db:
        stored = db.query(AuthSession).filter(AuthSession.token_hash == _token_hash(token)).one()
        assert stored.token_hash != token


def test_logout_revokes_the_token(client: TestClient):
    token = _login(client, ARJUN["email"], ARJUN["password"]).json()["token"]
    assert client.post("/api/v1/auth/logout", headers=_bearer(token)).status_code == 204
    assert client.get("/api/v1/auth/me", headers=_bearer(token)).status_code == 401
    assert client.get("/api/v1/dashboard", headers=_bearer(token)).status_code == 401
    assert client.get("/api/v1/dashboard", headers=_bearer("forged-token")).status_code == 401


def test_expired_sessions_are_refused():
    with SessionLocal() as db:
        user = db.query(User).filter(User.anon_token == "STU_8921").one()
        db.add(AuthSession(token_hash=_token_hash("old-token"), user_id=user.id, expires_at="2020-01-01T00:00:00+00:00"))
        db.commit()
        assert session_for(db, "old-token") is None


def test_role_header_alone_is_refused_when_disabled(client: TestClient, monkeypatch):
    monkeypatch.setattr(get_settings(), "allow_persona_header", False)
    response = client.get("/api/v1/dashboard", headers={"X-Persona": "student"})
    assert response.status_code == 401
    assert response.json()["detail"] == "Sign in to continue"


def test_demo_switch_issues_a_session_without_client_password(client: TestClient):
    response = client.post("/api/v1/auth/demo-switch", json={"persona": "faculty"})
    assert response.status_code == 200
    body = response.json()
    assert body["user"]["persona"] == "faculty"
    assert client.get("/api/v1/faculty/cohort-health", headers={"Authorization": f"Bearer {body['token']}"}).status_code == 200
