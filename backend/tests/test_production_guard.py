import pytest
from app.config import Settings, get_settings
from app.database import SessionLocal
from app.models import User
from app.services.board import blocked_core_count, load_cohort, skills_for
from fastapi.testclient import TestClient


def test_production_boot_rejects_missing_demo_password(monkeypatch):
    monkeypatch.delenv("DEMO_PASSWORD", raising=False)
    settings = Settings(
        environment="production",
        gemini_api_key="k" * 20,
        app_secret="x" * 40,
        allowed_origins="https://campusflow-ai-five.vercel.app",
        allow_persona_header=False,
        demo_password="CampusFlow@2026",
        gemini_model="gemini-2.5-flash-lite",
        gemini_fallback_model="gemini-2.5-flash-lite",
    )
    with pytest.raises(RuntimeError, match="DEMO_PASSWORD"):
        settings.assert_production()


def test_production_boot_accepts_explicit_demo_password(monkeypatch):
    monkeypatch.setenv("DEMO_PASSWORD", "CampusFlow@2026")
    settings = Settings(
        environment="production",
        gemini_api_key="k" * 20,
        app_secret="x" * 40,
        allowed_origins="https://campusflow-ai-five.vercel.app",
        allow_persona_header=False,
        demo_password="CampusFlow@2026",
        gemini_model="gemini-2.5-flash-lite",
        gemini_fallback_model="gemini-2.5-flash-lite",
    )
    settings.assert_production()


def test_production_validator_blocks_persona_header_and_weak_secret():
    with pytest.raises(ValueError, match="APP_SECRET"):
        Settings(
            environment="production",
            app_secret="short",
            allow_persona_header=False,
            demo_password="x",
            gemini_api_key="k",
        )
    with pytest.raises(ValueError, match="ALLOW_PERSONA_HEADER"):
        Settings(
            environment="production",
            app_secret="x" * 40,
            allow_persona_header=True,
            demo_password="x",
            gemini_api_key="k",
        )


def test_session_user_scopes_board_to_signed_in_student(client: TestClient):
    boot = client.get("/api/v1/bootstrap", headers={"X-Persona": "student"}).json()
    sprint_id = boot["sprints"][0]["id"]
    arjun = client.post(
        "/api/v1/auth/login",
        json={"email": "arjun@campusflow.edu", "password": "test-demo-pass"},
    ).json()
    headers = {"Authorization": f"Bearer {arjun['token']}"}
    board = client.get(f"/api/v1/sprints/{sprint_id}/board", headers=headers)
    assert board.status_code == 200
    spoofed = {**headers, "X-Persona": "faculty"}
    assert client.get("/api/v1/faculty/cohort-health", headers=spoofed).status_code == 403
    assert client.get("/api/v1/dashboard", headers=spoofed).status_code == 200


def test_load_cohort_matches_per_student_lookups():
    with SessionLocal() as db:
        rows = load_cohort(db)
        assert rows
        for entry in rows:
            student = entry["student"]
            assert isinstance(student, User)
            assert [node.skill_name for node in entry["nodes"]] == [
                node.skill_name for node in skills_for(db, student.id)
            ]
            assert entry["blocked"] == blocked_core_count(db, student.id)
            if entry["nodes"]:
                expected = round(sum(node.proficiency_score for node in entry["nodes"]) / len(entry["nodes"]))
            else:
                expected = 0
            assert entry["score"] == expected


def test_health_lists_production_boot_guard(client: TestClient):
    body = client.get("/health").json()
    assert "production_boot_guard" in body["security"]
    assert get_settings().ai_mode in {"gemini", "deterministic-fallback"}
