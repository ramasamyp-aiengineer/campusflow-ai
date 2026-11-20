import json
from types import SimpleNamespace

import httpx
import pytest
from app.config import get_settings
from app.database import SessionLocal
from app.models import Base, LearningWorkItem, SignalMessage, SkillNode, User
from app.services import ai, runtime
from app.services.seed import seed_if_empty
from app.services.signals import article_brief, seed_signals_if_empty
from app.services.story_actions import curriculum_drift, quiz_skill, quiz_skills
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

STUDENT = {"X-Persona": "student"}
STUDENT_NAMES = ("Arjun", "Priya", "Rohan", "Sneha", "Vikram", "Ananya", "STU_8921")


@pytest.fixture()
def cold_db():
    engine = create_engine("sqlite://", future=True)
    Base.metadata.create_all(engine)
    with Session(engine, future=True) as db:
        seed_if_empty(db)
        seed_signals_if_empty(db)
        db.commit()
        yield db


def test_first_story_a_judge_sees_awards_quiz_xp(cold_db: Session):
    arjun = cold_db.query(User).filter(User.anon_token == "STU_8921").one()
    first = (
        cold_db.query(SignalMessage)
        .filter(SignalMessage.student_id == arjun.id)
        .order_by(SignalMessage.id.desc())
        .first()
    )
    assert first.title.startswith("FastAPI services face")
    node = quiz_skill(cold_db, arjun, quiz_skills(cold_db, first))
    assert node is not None and node.skill_name == "FastAPI"
    titles = [row.title.lower() for row in cold_db.query(SignalMessage).all()]
    assert not any("derby" in title or "canteen" in title for title in titles)


def test_drift_radar_is_populated_on_a_cold_start(cold_db: Session):
    radar = curriculum_drift(cold_db)
    assert {trend["in_syllabus"] for trend in radar["trends"]} == {True, False}
    assert all(trend["suggestion"] for trend in radar["trends"])
    assert any(alert["level"] == "critical" and alert["title"] == "Hiring news is turning critical" for alert in radar["alerts"])
    rendered = json.dumps(radar)
    assert not any(name in rendered for name in STUDENT_NAMES)


def _fake_gemini(monkeypatch, status: int, payload: dict, sent: list[str]) -> None:
    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def post(self, url, **kwargs):
            sent.append(json.dumps(kwargs.get("json") or {}))
            return httpx.Response(status, json=payload, request=httpx.Request("POST", url))

    monkeypatch.setattr(get_settings(), "gemini_api_key", "test-key")
    monkeypatch.setattr(runtime, "model_is_resting", lambda _name: False)
    monkeypatch.setattr(runtime, "rest_model", lambda _name, _seconds: None)
    monkeypatch.setattr(ai, "httpx", SimpleNamespace(Client=FakeClient, HTTPError=httpx.HTTPError))


@pytest.fixture()
def gemini_down(monkeypatch):
    sent: list[str] = []
    _fake_gemini(monkeypatch, 503, {"error": {"code": 503}}, sent)
    return sent


def _ticket(code: str) -> int:
    with SessionLocal() as db:
        return db.query(LearningWorkItem).filter(LearningWorkItem.ticket_code == code).one().id


def _story(client: TestClient, needle: str) -> dict:
    messages = client.get("/api/v1/signals", headers=STUDENT).json()["messages"]
    return next(message for message in messages if needle in message["title"])


def test_every_ai_feature_answers_while_gemini_returns_503(client: TestClient, gemini_down: list[str]):
    sprint = client.post(
        "/api/v1/sprints/generate",
        headers=STUDENT,
        json={"title": "Resilience drill", "course_code": "CS399", "duration_weeks": 2, "syllabus": "Unit 1: Indexes and B+ trees. Unit 2: Transactions and locking."},
    )
    assert sprint.status_code == 200 and sprint.json()["items"]

    joins = _ticket("CS301-104")
    unblock = client.post(f"/api/v1/lwi/{joins}/unblock", headers=STUDENT, json={"message": "I am stuck on outer joins. Mail me at arjun.k@college.edu"})
    assert unblock.status_code == 200 and unblock.json()["result"]["guiding_question"]
    review = client.post(f"/api/v1/lwi/{joins}/evaluate", headers=STUDENT, json={"submission": "A left join keeps unmatched rows from the left table and fills NULLs."})
    assert review.status_code == 200

    brief, source = article_brief("Query planners explain joins", "A release improved index choice. Students learn SQL faster.", "Databases")
    assert source == "local" and brief.startswith("For Databases:")

    story = _story(client, "Query planners")
    task = client.post(f"/api/v1/signals/messages/{story['id']}/task", headers=STUDENT)
    assert task.status_code == 200 and task.json()["transport"] == "deterministic-fallback"
    card = client.post(f"/api/v1/signals/messages/{story['id']}/explain", headers=STUDENT)
    assert card.status_code == 200 and card.json()["source"] == "local"

    assert gemini_down, "Gemini should have been called"
    assert not any("arjun.k@college.edu" in body or "Arjun" in body or "STU_8921" in body for body in gemini_down)


def test_recovered_gemini_never_changes_a_quiz_in_progress_or_passed(client: TestClient, monkeypatch):
    recovered = {
        "concept": "A brand new concept sentence from the recovered model.",
        "use_case": "A brand new use case sentence from the recovered model.",
        "question": "Which option is new?",
        "options": ["new a", "new b", "new c"],
        "answer_index": 2,
        "why": "Because the model recovered.",
    }

    story = _story(client, "Query planners")
    with SessionLocal() as db:
        stored = json.loads(db.get(SignalMessage, story["id"]).explainer_json)
    assert stored["source"] == "local"
    answer = stored["card"]["answer_index"]

    body = {"candidates": [{"content": {"parts": [{"text": json.dumps(recovered)}]}}]}
    _fake_gemini(monkeypatch, 200, body, [])

    graded = client.post(f"/api/v1/signals/messages/{story['id']}/quiz", headers=STUDENT, json={"choice": answer}).json()
    assert graded["correct"] is True

    reopened = client.post(f"/api/v1/signals/messages/{story['id']}/explain", headers=STUDENT).json()
    assert reopened["source"] == "local" and reopened["question"] == stored["card"]["question"]
    with SessionLocal() as db:
        skill = db.query(SkillNode).filter(SkillNode.skill_name == graded["skill"]).first()
        assert skill is not None
