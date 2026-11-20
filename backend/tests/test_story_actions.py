from app.models import SignalMessage
from app.services.signals import FUSION_OVERLAP, fingerprint, story_similarity
from app.services.story_actions import Explainer, graph_skill, skills_in
from fastapi.testclient import TestClient

STUDENT = {"X-Persona": "student"}


def _subscribe(client: TestClient, url: str, label: str):
    return client.post("/api/v1/signals/feeds", headers=STUDENT, json={"url": url, "label": label})


def _inbox(client: TestClient) -> dict:
    return client.get("/api/v1/signals", headers=STUDENT).json()


def _story(client: TestClient, needle: str) -> dict:
    return next(message for message in _inbox(client)["messages"] if needle.lower() in message["title"].lower())


def test_same_story_from_two_outlets_scores_as_a_duplicate():
    left = fingerprint("A campus lab trains a small neural model on handwritten digits")
    right = fingerprint(
        "Students train a small neural model to read handwritten digits - AI Research Wire", "AI Research Wire"
    )
    other = fingerprint("Query planners now explain hash joins in plain language")
    assert story_similarity(left, right) >= FUSION_OVERLAP
    assert story_similarity(left, other) < FUSION_OVERLAP
    assert "wire" not in right


def test_skills_are_read_from_whole_words():
    assert "SQL" in skills_in("postgres query planners explain joins")
    assert "Machine Learning" in skills_in("a 4-bit lora recipe for fine-tuning")
    assert "API Design" not in skills_in("rapid capital growth")


def test_free_form_task_skills_snap_to_the_skill_graph():
    story = SignalMessage(
        title="LoRA quantization cuts VRAM for fine-tuning", summary="A 4-bit recipe keeps model accuracy."
    )
    assert graph_skill("sql", story) == "SQL"
    assert graph_skill("memory profiling", story) == "Machine Learning"


def test_explainer_rejects_an_answer_outside_the_options():
    try:
        Explainer(
            concept="A concept sentence.",
            use_case="A use case sentence.",
            question="Which one?",
            options=["a", "b", "c"],
            answer_index=3,
            why="Because it is.",
        )
    except ValueError:
        return
    raise AssertionError("answer_index 3 should be rejected for three options")


def test_cross_feed_duplicates_fuse_into_one_story(client: TestClient):
    first = _subscribe(client, "builtin:machine-learning", "Machine Learning")
    assert first.status_code in {200, 409}
    wire = _subscribe(client, "builtin:ai-research-wire", "Machine learning research")
    assert wire.status_code == 200
    body = wire.json()
    assert body["fused"] >= 2
    assert body["kept"] >= 2
    assert body["held"] >= 1

    digits = _story(client, "handwritten digits")
    outlets = {link["source"] for link in digits["sources"]}
    assert {"Campus ML Notes", "AI Research Wire"} <= outlets
    titles = [message["title"] for message in _inbox(client)["messages"]]
    assert sum("handwritten digits" in title for title in titles) == 1


def test_story_becomes_a_backlog_task_once(client: TestClient):
    lora = _story(client, "LoRA quantization")
    created = client.post(f"/api/v1/signals/messages/{lora['id']}/task", headers=STUDENT)
    assert created.status_code == 200
    body = created.json()
    assert body["created"] is True
    assert body["lwi"]["status"] == "BACKLOG"
    assert body["lwi"]["ticket_code"].startswith("LAB-")
    assert body["lwi"]["skill_tag"] == "Machine Learning"
    assert body["sprint"]["kind"] == "READING"

    again = client.post(f"/api/v1/signals/messages/{lora['id']}/task", headers=STUDENT).json()
    assert again["created"] is False
    assert again["lwi"]["id"] == body["lwi"]["id"]

    board = client.get(f"/api/v1/sprints/{body['sprint']['id']}/board", headers=STUDENT).json()
    assert any(item["id"] == body["lwi"]["id"] for item in board)
    refreshed = _story(client, "LoRA quantization")
    assert refreshed["task_lwi_id"] == body["lwi"]["id"]
    assert any(badge["kind"] == "task" for badge in refreshed["badges"])
    assert (
        client.post(f"/api/v1/signals/messages/{lora['id']}/task", headers={"X-Persona": "faculty"}).status_code == 403
    )


def test_relevance_badges_explain_the_skill_graph_link(client: TestClient):
    messages = _inbox(client)["messages"]
    labels = [badge["label"] for message in messages for badge in message["badges"]]
    assert any(label.startswith("Closes a skill gap: FastAPI") for label in labels)
    assert any(badge["kind"] == "ticket" for message in messages for badge in message["badges"])


def test_explain_and_quiz_award_xp_once(client: TestClient):
    story = _story(client, "FastAPI services face")
    untouched = _story(client, "Linux 6.x scheduler")
    assert (
        client.post(f"/api/v1/signals/messages/{untouched['id']}/quiz", headers=STUDENT, json={"choice": 0}).status_code
        == 409
    )

    card = client.post(f"/api/v1/signals/messages/{story['id']}/explain", headers=STUDENT)
    assert card.status_code == 200
    explainer = card.json()
    assert len(explainer["options"]) == 3
    assert "answer_index" not in explainer and "why" not in explainer

    import json

    from app.database import SessionLocal
    from app.models import SignalMessage

    with SessionLocal() as db:
        answer = json.loads(db.get(SignalMessage, story["id"]).explainer_json)["card"]["answer_index"]
    passed = client.post(
        f"/api/v1/signals/messages/{story['id']}/quiz", headers=STUDENT, json={"choice": answer}
    ).json()
    assert passed["correct"] is True
    assert passed["skill"] == "FastAPI"
    assert passed["xp_awarded"] == 2

    repeat = client.post(
        f"/api/v1/signals/messages/{story['id']}/quiz", headers=STUDENT, json={"choice": answer}
    ).json()
    assert repeat["correct"] is True
    assert repeat["xp_awarded"] == 0
    assert repeat["already_passed"] is True
    assert repeat["skill_score"] == passed["skill_score"]


def test_drift_radar_is_for_faculty_and_tpo_only(client: TestClient):
    assert client.get("/api/v1/signals/drift", headers=STUDENT).status_code == 403
    for persona in ("faculty", "tpo"):
        radar = client.get("/api/v1/signals/drift", headers={"X-Persona": persona})
        assert radar.status_code == 200
    body = radar.json()
    assert body["total_stories"] >= 1
    fine_tuning = next(trend for trend in body["trends"] if trend["term"] == "LLM fine-tuning")
    assert fine_tuning["in_syllabus"] is False
    assert any(alert["level"] == "critical" and "Hiring" in alert["title"] for alert in body["alerts"])
    assert all("name" not in trend for trend in body["trends"])
