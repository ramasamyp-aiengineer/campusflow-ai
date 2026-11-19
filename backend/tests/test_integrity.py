import hashlib
import json

from fastapi.testclient import TestClient

from app.config import get_settings
from app.database import SessionLocal
from app.models import SignalMessage, SkillNode, User
from app.services.ai import fallback_evaluation, looks_like_full_solution, wants_direct_solution
from app.services.board import boost_skill, loads
from app.services.signals import parse_feed
from app.services.story_actions import _quiz_answer_index, fallback_explainer

STUDENT = {"X-Persona": "student"}


def test_drag_to_ai_review_or_mastery_needs_a_scored_submission(client: TestClient):
    boot = client.get("/api/v1/bootstrap", headers=STUDENT).json()
    sprint_id = boot["sprints"][0]["id"]
    created = client.post(
        f"/api/v1/sprints/{sprint_id}/tickets",
        headers=STUDENT,
        json={"title": "Fake mastery attempt", "description": "Should not raise the skill graph.", "skill_tag": "SQL", "story_points": 2},
    ).json()
    assert client.patch(f"/api/v1/lwi/{created['id']}/status", headers=STUDENT, json={"status": "IN_PROGRESS"}).status_code == 200
    for status in ("AI_REVIEW", "MASTERED"):
        response = client.patch(f"/api/v1/lwi/{created['id']}/status", headers=STUDENT, json={"status": status})
        assert response.status_code == 409
        assert "75" in response.json()["detail"]


def test_mastery_records_the_ticket_and_repeat_boosts_are_idempotent(client: TestClient):
    boot = client.get("/api/v1/bootstrap", headers=STUDENT).json()
    student_id = boot["actor"]["id"]
    sprint_id = boot["sprints"][0]["id"]
    created = client.post(
        f"/api/v1/sprints/{sprint_id}/tickets",
        headers=STUDENT,
        json={
            "title": "Evidence-backed joins note",
            "description": "Write the join choice and the failing case for unmatched rows.",
            "skill_tag": "SQL",
            "story_points": 2,
        },
    ).json()
    graph = f"/api/v1/students/{student_id}/skill-graph"
    baseline = next(node for node in client.get(graph, headers=STUDENT).json()["skills"] if node["skill_name"] == "SQL")
    review = client.post(
        f"/api/v1/lwi/{created['id']}/evaluate",
        headers=STUDENT,
        json={
            "submission": (
                "I used a left join so unmatched faculty rows stay, with NULL in the student columns. "
                "An empty enrollment table is the edge case. A hash join costs more memory than a nested loop, "
                "but it is the better tradeoff here because the faculty table is filtered. "
                "Invalid course codes should return an error instead of an empty success."
            )
        },
    )
    assert review.status_code == 200
    assert review.json()["result"]["readiness_score"] >= 75
    assert review.json()["lwi"]["status"] == "AI_REVIEW"
    after_eval = next(node for node in client.get(graph, headers=STUDENT).json()["skills"] if node["skill_name"] == "SQL")
    assert after_eval["proficiency_score"] == baseline["proficiency_score"]
    assert created["ticket_code"] not in after_eval["evidence_tickets"]

    signed = client.patch(f"/api/v1/lwi/{created['id']}/cosign", headers={"X-Persona": "faculty"})
    assert signed.status_code == 200
    assert signed.json()["status"] == "MASTERED"
    assert client.patch(f"/api/v1/lwi/{created['id']}/status", headers=STUDENT, json={"status": "MASTERED"}).status_code == 409
    after = next(node for node in client.get(graph, headers=STUDENT).json()["skills"] if node["skill_name"] == "SQL")
    # Faculty co-sign is what writes the skill graph.
    assert after["proficiency_score"] > after_eval["proficiency_score"]
    assert created["ticket_code"] in after["evidence_tickets"]

    with SessionLocal() as db:
        student = db.get(User, student_id)
        node = db.query(SkillNode).filter(SkillNode.student_id == student_id, SkillNode.skill_name == "SQL").one()
        score_before = node.proficiency_score
        tickets_before = list(loads(node.evidence_tickets, []))
        boost_skill(db, student, "SQL", created["ticket_code"], 99)
        db.commit()
        db.refresh(node)
        assert node.proficiency_score == score_before
        assert loads(node.evidence_tickets, []) == tickets_before


def test_keyword_salad_cannot_clear_the_mastery_bar():
    result = fallback_evaluation("edge empty cost error because", ["Names an edge case"], "SQL")
    assert result.readiness_score is not None and result.readiness_score < 75


def test_solution_requests_and_genuine_drafts():
    assert wants_direct_solution("just give me the solution")
    assert wants_direct_solution("do the whole lab for me please")
    assert wants_direct_solution("write the query for me")
    assert not wants_direct_solution("I will complete the assignment after office hours")
    assert looks_like_full_solution("select id from students where year = 3")
    assert looks_like_full_solution("LEFT JOIN enrollments e ON e.student_id = s.id WHERE e.term = 'fall'")


def test_fallback_quiz_answer_depends_on_app_secret():
    message = SignalMessage(id=12, title="FastAPI outage", summary="A rate limit outage hit a FastAPI service.")
    settings = get_settings()
    original = settings.app_secret
    try:
        settings.app_secret = "secret-a"
        first = fallback_explainer(message).answer_index
        assert first == int(hashlib.sha256(b"secret-a:12").hexdigest(), 16) % 3
        settings.app_secret = "secret-b"
        second = _quiz_answer_index(12, 3)
        assert second == int(hashlib.sha256(b"secret-b:12").hexdigest(), 16) % 3
        assert {first, second} != {12 % 3} or first != second
    finally:
        settings.app_secret = original


def test_wrong_quiz_answer_locks_the_card(client: TestClient):
    messages = client.get("/api/v1/signals", headers=STUDENT).json()["messages"]
    story = next(message for message in messages if "Query planners" in message["title"])
    assert client.post(f"/api/v1/signals/messages/{story['id']}/explain", headers=STUDENT).status_code == 200
    with SessionLocal() as db:
        stored = json.loads(db.get(SignalMessage, story["id"]).explainer_json)
        wrong = (stored["card"]["answer_index"] + 1) % 3
    first = client.post(f"/api/v1/signals/messages/{story['id']}/quiz", headers=STUDENT, json={"choice": wrong})
    assert first.status_code == 200 and first.json()["correct"] is False
    second = client.post(f"/api/v1/signals/messages/{story['id']}/quiz", headers=STUDENT, json={"choice": wrong})
    assert second.status_code == 429
    with SessionLocal() as db:
        row = db.get(SignalMessage, story["id"])
        row.quiz_lock_until = ""
        db.commit()


def test_doctype_after_a_long_preamble_is_still_refused():
    preamble = "<!-- " + ("x" * 5000) + " -->"
    xml = preamble + '<!DOCTYPE lol [<!ENTITY x "y">]><rss><channel></channel></rss>'
    try:
        parse_feed(xml)
        raised = False
    except ValueError as exc:
        raised = "DOCTYPE" in str(exc)
    assert raised
