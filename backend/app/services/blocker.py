from app.models import LearningWorkItem


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


ACTIVE = {"IN_PROGRESS", "AI_REVIEW", "MASTERED"}


def assert_can_enter(item: LearningWorkItem, new_status: str, by_id: dict[int, LearningWorkItem]) -> str | None:
    reason = block_reason(item, by_id)
    if reason and new_status in ACTIVE:
        return reason
    if new_status == "MASTERED" and item.status != "AI_REVIEW":
        return "Mastery is recorded only after the ticket has been through AI Review"
    return None
