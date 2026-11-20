import pytest
from app.database import SessionLocal
from app.models import AuditEvent, SchedulerLease, User, utcnow
from app.services.golden import golden_accuracy, golden_rows
from app.services.runtime import acquire_lease
from fastapi.testclient import TestClient


def test_fallback_reviewer_matches_the_golden_set():
    assert len(golden_rows()) == 10
    assert golden_accuracy() == 1.0


def test_registered_students_do_not_share_a_board(client: TestClient):
    password = "correct-horse-1"
    first = client.post(
        "/api/v1/auth/register",
        json={"name": "Asha Rao", "email": "asha.rao@campusflow.edu", "password": password},
    )
    second = client.post(
        "/api/v1/auth/register",
        json={"name": "Dev Patel", "email": "dev.patel@campusflow.edu", "password": password},
    )
    assert first.status_code == second.status_code == 200
    token_a = {"Authorization": f"Bearer {first.json()['token']}"}
    token_b = {"Authorization": f"Bearer {second.json()['token']}"}
    created = client.post(
        "/api/v1/sprints/generate",
        headers=token_a,
        json={
            "title": "Asha networks",
            "course_code": "CS390",
            "duration_weeks": 2,
            "syllabus": "Unit 1: Links\nFrames and errors\nUnit 2: Routing\nShortest paths and cost\n",
        },
    )
    assert created.status_code == 200
    sprint_id = created.json()["sprint"]["id"]
    own = client.get(f"/api/v1/sprints/{sprint_id}/board", headers=token_a)
    other = client.get(f"/api/v1/sprints/{sprint_id}/board", headers=token_b)
    assert own.status_code == 200 and own.json()
    assert other.status_code == 404
    boot_b = client.get("/api/v1/bootstrap", headers=token_b).json()
    assert boot_b["actor"]["name"] == "Dev Patel"
    assert all(sprint["id"] != sprint_id for sprint in boot_b["sprints"])


def test_ticket_create_rate_is_stored_with_the_user(client: TestClient):
    boot = client.get("/api/v1/bootstrap", headers={"X-Persona": "student"}).json()
    sprint_id = boot["sprints"][0]["id"]
    with SessionLocal() as db:
        student = db.query(User).filter(User.anon_token == "STU_8921").one()
        now = utcnow()
        for index in range(8):
            db.add(
                AuditEvent(
                    actor_token=student.anon_token,
                    actor_role="STUDENT",
                    action="lwi.create",
                    detail=f"rate-probe-{index}",
                    created_at=now,
                )
            )
        db.commit()
    try:
        blocked = client.post(
            f"/api/v1/sprints/{sprint_id}/tickets",
            headers={"X-Persona": "student"},
            json={"title": "Ninth ticket in a minute", "description": "Should wait.", "skill_tag": "SQL"},
        )
        assert blocked.status_code == 429
    finally:
        with SessionLocal() as db:
            db.query(AuditEvent).filter(AuditEvent.detail.like("rate-probe-%")).delete(synchronize_session=False)
            db.commit()


def test_poll_lease_has_one_owner():
    with SessionLocal() as db:
        assert acquire_lease(db, "test_poll", 60, owner="instance-a") is True
        db.commit()
    with SessionLocal() as db:
        assert acquire_lease(db, "test_poll", 60, owner="instance-a") is True
        assert acquire_lease(db, "test_poll", 60, owner="instance-b") is False
        row_gone = db.get(SchedulerLease, "test_poll")
        if row_gone is not None:
            db.delete(row_gone)
        db.commit()


def test_production_boot_rejects_the_dev_secret():
    from app.config import Settings

    with pytest.raises(ValueError, match="APP_SECRET"):
        Settings(
            environment="production",
            gemini_api_key="test-key",
            app_secret="campusflow-dev-secret",
            demo_password="not-the-shared-demo-password",
            allowed_origins="https://campusflow.example",
            gemini_model="gemini-3.5-flash-lite",
            gemini_fallback_model="gemini-2.5-flash-lite",
        )


def test_production_boot_rejects_wildcard_cors():
    from app.config import Settings

    with pytest.raises(RuntimeError, match="wildcard"):
        Settings(
            environment="production",
            gemini_api_key="test-key",
            app_secret="production-test-secret-that-is-long-enough",
            demo_password="not-the-shared-demo-password",
            allowed_origins="*",
            gemini_model="gemini-3.5-flash-lite",
            gemini_fallback_model="gemini-2.5-flash-lite",
            allow_persona_header=False,
        ).assert_production()
