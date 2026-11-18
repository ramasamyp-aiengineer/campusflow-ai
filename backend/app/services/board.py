import hashlib
import json
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models import AuditEvent, LearningWorkItem, SkillNode, Sprint, User, utcnow
from app.schemas import ChainNode, LWIDetail, LWIOut, SkillOut, SprintOut
from app.services.blocker import block_reason

CORE_SKILLS = {
    "SQL",
    "Data Structures",
    "Operating Systems",
    "Python",
    "Distributed Systems",
    "Relational Algebra",
    "FastAPI",
    "API Design",
    "Security Engineering",
    "Frontend Engineering",
    "DevOps",
    "System Design",
}


def loads(raw: str | None, fallback):
    if not raw:
        return fallback
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return fallback


def persona_user(db: Session, persona: str) -> User:
    role = {"student": "STUDENT", "faculty": "FACULTY", "tpo": "TPO"}[persona]
    user = (
        db.query(User)
        .filter(User.role == role, User.is_persona.is_(True))
        .order_by(User.id)
        .first()
    )
    if user is None:
        raise LookupError(f"No persona user for {persona}")
    return user


def student_or_404(db: Session, student_id: int) -> User:
    user = db.get(User, student_id)
    if user is None or user.role != "STUDENT":
        raise LookupError("Student not found")
    return user


def audit(db: Session, actor: User, action: str, detail: str) -> None:
    db.add(
        AuditEvent(
            actor_token=actor.anon_token,
            actor_role=actor.role,
            action=action,
            detail=detail[:500],
            created_at=utcnow(),
        )
    )


def lwis_for(db: Session, student_id: int, sprint_id: int | None = None) -> list[LearningWorkItem]:
    query = db.query(LearningWorkItem).filter(LearningWorkItem.student_id == student_id)
    if sprint_id is not None:
        query = query.filter(LearningWorkItem.sprint_id == sprint_id)
    return query.order_by(LearningWorkItem.id).all()


def index_items(items: list[LearningWorkItem]) -> dict[int, LearningWorkItem]:
    return {item.id: item for item in items}


def to_lwi(item: LearningWorkItem, by_id: dict[int, LearningWorkItem]) -> LWIOut:
    reason = block_reason(item, by_id)
    parent = by_id.get(item.prerequisite_id) if item.prerequisite_id else None
    feedback = loads(item.ai_feedback_json, None)
    return LWIOut(
        id=item.id,
        sprint_id=item.sprint_id,
        student_id=item.student_id,
        ticket_code=item.ticket_code,
        title=item.title,
        description=item.description,
        type=item.type,
        status=item.status,
        story_points=item.story_points,
        skill_tag=item.skill_tag,
        prerequisite_id=item.prerequisite_id,
        prerequisite_code=parent.ticket_code if parent else None,
        prerequisite_title=parent.title if parent else None,
        blocked=reason is not None,
        block_reason=reason,
        co_tag=item.co_tag,
        rubric_criteria=loads(item.rubric_criteria, []),
        ai_feedback=feedback if isinstance(feedback, dict) else None,
    )


def chain_for(item: LearningWorkItem, by_id: dict[int, LearningWorkItem]) -> list[ChainNode]:
    nodes: list[ChainNode] = []
    seen: set[int] = set()
    cursor = by_id.get(item.prerequisite_id) if item.prerequisite_id else None
    while cursor and cursor.id not in seen:
        seen.add(cursor.id)
        reason = block_reason(cursor, by_id)
        nodes.append(
            ChainNode(
                id=cursor.id,
                ticket_code=cursor.ticket_code,
                title=cursor.title,
                status=cursor.status,
                blocked=reason is not None,
            )
        )
        cursor = by_id.get(cursor.prerequisite_id) if cursor.prerequisite_id else None
    nodes.reverse()
    return nodes


def dependents_for(item: LearningWorkItem, items: list[LearningWorkItem], by_id: dict[int, LearningWorkItem]) -> list[ChainNode]:
    return [
        ChainNode(
            id=other.id,
            ticket_code=other.ticket_code,
            title=other.title,
            status=other.status,
            blocked=block_reason(other, by_id) is not None,
        )
        for other in items
        if other.prerequisite_id == item.id
    ]


def to_detail(item: LearningWorkItem, items: list[LearningWorkItem]) -> LWIDetail:
    by_id = index_items(items)
    base = to_lwi(item, by_id)
    return LWIDetail(
        **base.model_dump(),
        prerequisite_chain=chain_for(item, by_id),
        dependents=dependents_for(item, items, by_id),
    )


def sprint_out(db: Session, sprint: Sprint, student_id: int) -> SprintOut:
    items = lwis_for(db, student_id, sprint.id)
    total = len(items)
    mastered = sum(1 for item in items if item.status == "MASTERED")
    points = sum(item.story_points for item in items) or 1
    mastered_points = sum(item.story_points for item in items if item.status == "MASTERED")
    return SprintOut(
        id=sprint.id,
        title=sprint.title,
        course_code=sprint.course_code,
        start_date=sprint.start_date,
        end_date=sprint.end_date,
        co_po_tags=loads(sprint.co_po_tags, []),
        kind=sprint.kind,
        lwi_count=total,
        mastered_count=mastered,
        progress_percent=round(100 * mastered_points / points) if total else 0,
    )


def visible_sprints(db: Session, student_id: int) -> list[Sprint]:
    sprint_ids = {
        row[0]
        for row in db.query(LearningWorkItem.sprint_id)
        .filter(LearningWorkItem.student_id == student_id)
        .distinct()
    }
    if not sprint_ids:
        return []
    return db.query(Sprint).filter(Sprint.id.in_(sprint_ids)).order_by(Sprint.id).all()


def semester_progress(db: Session, student_id: int) -> int:
    items = lwis_for(db, student_id)
    points = sum(item.story_points for item in items) or 1
    done = sum(item.story_points for item in items if item.status == "MASTERED")
    return round(100 * done / points)


def next_ticket_code(db: Session, course_code: str) -> str:
    rows = db.query(LearningWorkItem.ticket_code).filter(LearningWorkItem.ticket_code.like(f"{course_code}-%")).all()
    numbers = []
    for (code,) in rows:
        tail = code.rsplit("-", 1)[-1]
        if tail.isdigit():
            numbers.append(int(tail))
    number = (max(numbers) + 1) if numbers else 101
    return f"{course_code}-{number:03d}"


def evidence_hash(student_id: int, skill: str, tickets: list[str]) -> str:
    payload = f"{student_id}|{skill}|{','.join(tickets)}"
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


def skill_out(node: SkillNode) -> SkillOut:
    return SkillOut(
        id=node.id,
        skill_name=node.skill_name,
        proficiency_score=node.proficiency_score,
        verified_lwi_count=node.verified_lwi_count,
        evidence_tickets=loads(node.evidence_tickets, []),
        evidence_hash=node.evidence_hash,
        last_updated=node.last_updated,
    )


def skills_for(db: Session, student_id: int) -> list[SkillNode]:
    return (
        db.query(SkillNode)
        .filter(SkillNode.student_id == student_id)
        .order_by(SkillNode.proficiency_score.desc(), SkillNode.skill_name)
        .all()
    )


def verified_average(nodes: list[SkillNode]) -> int:
    if not nodes:
        return 0
    return round(sum(node.proficiency_score for node in nodes) / len(nodes))


def boost_skill(db: Session, student: User, skill: str, ticket_code: str, score: int) -> None:
    if score < 70:
        return
    node = (
        db.query(SkillNode)
        .filter(SkillNode.student_id == student.id, SkillNode.skill_name == skill)
        .first()
    )
    if node is None:
        node = SkillNode(
            student_id=student.id,
            skill_name=skill,
            proficiency_score=40,
            verified_lwi_count=0,
            evidence_tickets="[]",
            evidence_hash="",
            last_updated=utcnow(),
        )
        db.add(node)
        db.flush()
    tickets = loads(node.evidence_tickets, [])
    if ticket_code in tickets:
        return
    delta = max(2, (score - 60) // 5)
    node.proficiency_score = min(100, node.proficiency_score + delta)
    tickets.append(ticket_code)
    node.evidence_tickets = json.dumps(tickets)
    node.verified_lwi_count = len(tickets)
    node.evidence_hash = evidence_hash(student.id, skill, tickets)
    node.last_updated = utcnow()


def blocked_core_count(db: Session, student_id: int) -> int:
    items = (
        db.query(LearningWorkItem)
        .join(Sprint, Sprint.id == LearningWorkItem.sprint_id)
        .filter(LearningWorkItem.student_id == student_id, Sprint.kind == "COURSE")
        .all()
    )
    by_id = index_items(items)
    count = 0
    for item in items:
        if item.skill_tag in CORE_SKILLS and block_reason(item, by_id):
            count += 1
    return count


def top_gap(nodes: list[SkillNode]) -> str | None:
    if not nodes:
        return None
    weakest = min(nodes, key=lambda node: node.proficiency_score)
    if weakest.proficiency_score >= 75:
        return None
    return weakest.skill_name


def window_dates(weeks: int) -> tuple[str, str]:
    start = datetime.now(timezone.utc).date()
    from datetime import timedelta

    end = start + timedelta(days=7 * weeks)
    return start.isoformat(), end.isoformat()
