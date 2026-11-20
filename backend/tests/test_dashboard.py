from app.services.dashboard import ActionInputs, next_actions
from fastapi.testclient import TestClient

STUDENT = {"X-Persona": "student"}
VIEWS = {"board", "signals", "skills", "placement"}


def test_next_actions_put_a_blocked_ticket_first():
    actions = next_actions(ActionInputs(blocked_code="CS301-106", blocked_prerequisite="CS301-104", in_review=2))
    assert actions[0]["kind"] == "unblock"
    assert "CS301-104" in actions[0]["detail"]
    assert actions[1]["title"] == "2 tickets are waiting in AI Review"


def test_next_actions_suggest_a_first_topic_when_none_exist():
    actions = next_actions(ActionInputs(interest_count=0, has_placement_sprint=True))
    assert [action["kind"] for action in actions] == ["follow"]


def test_next_actions_prefer_unread_reading_over_a_first_topic():
    kinds = [
        action["kind"]
        for action in next_actions(ActionInputs(unread_stories=1, interest_count=2, has_placement_sprint=True))
    ]
    assert "read" in kinds
    assert "follow" not in kinds


def test_next_actions_skip_strong_skills_and_cap_the_list():
    assert all(
        action["kind"] != "skill"
        for action in next_actions(ActionInputs(weakest_skill="SQL", weakest_score=80, has_placement_sprint=True))
    )
    crowded = ActionInputs(
        blocked_code="A-1",
        in_review=1,
        unread_stories=3,
        interest_count=1,
        weakest_skill="DevOps",
        weakest_score=40,
    )
    assert len(next_actions(crowded)) == 4
    assert len(next_actions(crowded, limit=2)) == 2


def test_dashboard_is_student_only(client: TestClient):
    for persona in ("faculty", "tpo"):
        assert client.get("/api/v1/dashboard", headers={"X-Persona": persona}).status_code == 403


def test_dashboard_ticket_counts_match_the_boards(client: TestClient):
    body = client.get("/api/v1/dashboard", headers=STUDENT).json()
    tickets = body["tickets"]
    assert tickets["backlog"] + tickets["in_progress"] + tickets["ai_review"] + tickets["mastered"] == tickets["total"]
    assert 0 <= tickets["points_mastered"] <= tickets["points_total"]

    board_items = []
    for sprint in body["sprints"]:
        board_items += client.get(f"/api/v1/sprints/{sprint['id']}/board", headers=STUDENT).json()
    assert len(board_items) == tickets["total"]
    assert sum(1 for item in board_items if item["blocked"]) == tickets["blocked"]
    assert sum(1 for item in board_items if item["status"] == "MASTERED") == tickets["mastered"]


def test_dashboard_interest_totals_match_the_inbox(client: TestClient):
    body = client.get("/api/v1/dashboard", headers=STUDENT).json()
    inbox = client.get("/api/v1/signals", headers=STUDENT).json()
    interests = body["interests"]
    assert interests["topics"] == len(inbox["feeds"])
    assert interests["saved"] == len(inbox["messages"])
    assert interests["unread"] == inbox["unread"]
    assert sum(interests["sentiments"].values()) == interests["saved"]
    assert len(interests["latest"]) == min(3, interests["saved"])


def test_dashboard_scores_and_actions_are_consistent(client: TestClient):
    body = client.get("/api/v1/dashboard", headers=STUDENT).json()
    assert 0 <= body["semester_progress"] <= 100
    assert body["shortlist_ready"] == (body["verified_skill_score"] >= body["shortlist_bar"])
    assert body["skills"]["count"] >= len(body["skills"]["top"])
    assert body["next_actions"]
    assert all(action["view"] in VIEWS for action in body["next_actions"])
    assert all(event["actor_role"] == "STUDENT" for event in body["activity"])


def test_dashboard_reflects_a_new_ticket_immediately(client: TestClient):
    before = client.get("/api/v1/dashboard", headers=STUDENT).json()
    sprint_id = before["sprints"][0]["id"]
    created = client.post(
        f"/api/v1/sprints/{sprint_id}/tickets",
        headers=STUDENT,
        json={"title": "Dashboard check ticket", "skill_tag": "SQL", "story_points": 2},
    )
    assert created.status_code == 200
    after = client.get("/api/v1/dashboard", headers=STUDENT).json()
    assert after["tickets"]["total"] == before["tickets"]["total"] + 1
    assert after["tickets"]["backlog"] == before["tickets"]["backlog"] + 1
    assert after["tickets"]["points_total"] == before["tickets"]["points_total"] + 2
    assert after["activity"][0]["action"] == "lwi.create"
