import json

from app.models import LearningWorkItem

PASS_SCORE = 75
ACTIVE = {"IN_PROGRESS", "AI_REVIEW", "MASTERED"}


def block_reason(
    item: LearningWorkItem,
    by_id: dict[int, LearningWorkItem],
    seen: set[int] | None = None,
) -> str | None:
    seen = set(seen or ())
    if item.id in seen:
        return "Blocked by a prerequisite cycle"
    seen.add(item.id)
    if not item.prerequisite_id:
        return None
    parent = by_id.get(item.prerequisite_id)
    if parent is None:
        return None
    if parent.status != "MASTERED":
        return f"Blocked until {parent.ticket_code} · {parent.title} reaches Mastered"
    return block_reason(parent, by_id, seen)


def passing_readiness(item: LearningWorkItem) -> int | None:
    """Return the stored readiness score when a non-refused evaluation cleared the bar."""
    if not item.ai_feedback_json:
        return None
    try:
        feedback = json.loads(item.ai_feedback_json)
    except json.JSONDecodeError:
        return None
    if not isinstance(feedback, dict) or feedback.get("refused_direct_solution"):
        return None
    score = feedback.get("readiness_score")
    if not isinstance(score, int) or score < PASS_SCORE:
        return None
    return score


def assert_can_enter(item: LearningWorkItem, new_status: str, by_id: dict[int, LearningWorkItem]) -> str | None:
    reason = block_reason(item, by_id)
    if reason and new_status in ACTIVE:
        return reason
    if new_status in {"AI_REVIEW", "MASTERED"} and passing_readiness(item) is None:
        return f"AI Review and Mastery need a scored submission of {PASS_SCORE} or above"
    if new_status == "MASTERED" and item.status != "AI_REVIEW":
        return "Mastery is recorded only after the ticket has been through AI Review"
    if new_status == "MASTERED" and not item.cosigned_by_id:
        return "Mastery is recorded when faculty co-sign an AI-reviewed ticket"
    return None
