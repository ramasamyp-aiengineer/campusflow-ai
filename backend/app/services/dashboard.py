from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models import AuditEvent, FeedSubscription, SignalMessage, User
from app.services.blocker import block_reason
from app.services.board import (
    index_items,
    lwis_for,
    semester_progress,
    skills_for,
    sprint_out,
    verified_average,
    visible_sprints,
)

SHORTLIST_BAR = 70
STATUSES = ("BACKLOG", "IN_PROGRESS", "AI_REVIEW", "MASTERED")
SENTIMENTS = ("Positive", "Watchful", "Critical", "Neutral")


@dataclass
class ActionInputs:
    blocked_code: str | None = None
    blocked_prerequisite: str | None = None
    in_review: int = 0
    unread_stories: int = 0
    interest_count: int = 0
    weakest_skill: str | None = None
    weakest_score: int = 100
    has_placement_sprint: bool = False


def next_actions(inputs: ActionInputs, limit: int = 4) -> list[dict]:
    actions: list[dict] = []
    if inputs.blocked_code:
        actions.append(
            {
                "kind": "unblock",
                "title": f"Unlock {inputs.blocked_code}",
                "detail": f"Master {inputs.blocked_prerequisite} first. It is holding this ticket back."
                if inputs.blocked_prerequisite
                else "Its prerequisite is not mastered yet.",
                "view": "board",
            }
        )
    if inputs.in_review:
        noun = "ticket is" if inputs.in_review == 1 else "tickets are"
        actions.append(
            {
                "kind": "review",
                "title": f"{inputs.in_review} {noun} waiting in AI Review",
                "detail": "Submit your answer so the rubric can count it as evidence.",
                "view": "board",
            }
        )
    if inputs.unread_stories:
        noun = "story" if inputs.unread_stories == 1 else "stories"
        actions.append(
            {
                "kind": "read",
                "title": f"{inputs.unread_stories} unread {noun}",
                "detail": "New reading arrived in your interests.",
                "view": "signals",
            }
        )
    elif inputs.interest_count == 0:
        actions.append(
            {
                "kind": "follow",
                "title": "Follow your first topic",
                "detail": "Add an RSS link for something you care about.",
                "view": "signals",
            }
        )
    if inputs.weakest_skill and inputs.weakest_score < 75:
        actions.append(
            {
                "kind": "skill",
                "title": f"Lift {inputs.weakest_skill}",
                "detail": f"It sits at {inputs.weakest_score}. That is your lowest verified skill.",
                "view": "skills",
            }
        )
    if not inputs.has_placement_sprint:
        actions.append(
            {
                "kind": "placement",
                "title": "Match yourself to a job",
                "detail": "Paste a job description to get a 14-day prep sprint.",
                "view": "placement",
            }
        )
    return actions[:limit]


def ticket_summary(items, by_id) -> dict:
    counts = {status: 0 for status in STATUSES}
    blocked = 0
    for item in items:
        counts[item.status] = counts.get(item.status, 0) + 1
        if block_reason(item, by_id):
            blocked += 1
    return {
        "total": len(items),
        "backlog": counts["BACKLOG"],
        "in_progress": counts["IN_PROGRESS"],
        "ai_review": counts["AI_REVIEW"],
        "mastered": counts["MASTERED"],
        "blocked": blocked,
        "points_total": sum(item.story_points for item in items),
        "points_mastered": sum(item.story_points for item in items if item.status == "MASTERED"),
    }


def build_dashboard(db: Session, student: User) -> dict:
    items = lwis_for(db, student.id)
    by_id = index_items(items)
    sprints = visible_sprints(db, student.id)
    nodes = skills_for(db, student.id)
    score = verified_average(nodes)

    first_blocked = next((item for item in items if block_reason(item, by_id)), None)
    prerequisite = by_id.get(first_blocked.prerequisite_id) if first_blocked and first_blocked.prerequisite_id else None
    weakest = min(nodes, key=lambda node: node.proficiency_score) if nodes else None

    feeds = db.query(FeedSubscription).filter(FeedSubscription.student_id == student.id).all()
    messages = (
        db.query(SignalMessage)
        .filter(SignalMessage.student_id == student.id)
        .order_by(SignalMessage.id.desc())
        .all()
    )
    labels = {feed.id: feed.label for feed in feeds}
    mix = {label: 0 for label in SENTIMENTS}
    for message in messages:
        mix[message.sentiment if message.sentiment in mix else "Neutral"] += 1
    unread = sum(1 for message in messages if not message.is_read)
    upcoming = sorted(feed.next_poll_at for feed in feeds if feed.next_poll_at)

    events = (
        db.query(AuditEvent)
        .filter(AuditEvent.actor_token == student.anon_token)
        .order_by(AuditEvent.id.desc())
        .limit(8)
        .all()
    )

    tickets = ticket_summary(items, by_id)
    return {
        "student": {
            "name": student.name,
            "anon_token": student.anon_token,
            "program": student.program,
            "semester": student.semester,
            "cgpa": student.cgpa,
            "avatar_initials": student.avatar_initials,
        },
        "semester_progress": semester_progress(db, student.id),
        "verified_skill_score": score,
        "shortlist_ready": score >= SHORTLIST_BAR,
        "shortlist_bar": SHORTLIST_BAR,
        "tickets": tickets,
        "sprints": [sprint_out(db, sprint, student.id) for sprint in sprints],
        "skills": {
            "count": len(nodes),
            "top": [{"name": node.skill_name, "score": node.proficiency_score} for node in nodes[:3]],
            "weakest": {"name": weakest.skill_name, "score": weakest.proficiency_score} if weakest else None,
        },
        "interests": {
            "topics": len(feeds),
            "saved": len(messages),
            "unread": unread,
            "sentiments": mix,
            "next_fetch": upcoming[0] if upcoming else None,
            "latest": [
                {
                    "id": message.id,
                    "title": message.title,
                    "sentiment": message.sentiment,
                    "topic": labels.get(message.subscription_id, ""),
                    "is_read": message.is_read,
                }
                for message in messages[:3]
            ],
        },
        "next_actions": next_actions(
            ActionInputs(
                blocked_code=first_blocked.ticket_code if first_blocked else None,
                blocked_prerequisite=prerequisite.ticket_code if prerequisite else None,
                in_review=tickets["ai_review"],
                unread_stories=unread,
                interest_count=len(feeds),
                weakest_skill=weakest.skill_name if weakest else None,
                weakest_score=weakest.proficiency_score if weakest else 100,
                has_placement_sprint=any(sprint.kind == "PLACEMENT" for sprint in sprints),
            )
        ),
        "activity": [
            {"action": event.action, "detail": event.detail, "actor_role": event.actor_role, "created_at": event.created_at}
            for event in events
        ],
    }
