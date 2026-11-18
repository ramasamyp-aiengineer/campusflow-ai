import json
import re

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.limiter import limiter
from app.models import LearningWorkItem, Sprint, User
from app.schemas import (
    AIActionResponse,
    AuditOut,
    Bootstrap,
    CohortHealth,
    CohortStudent,
    DashboardOut,
    EvaluateIn,
    GenerateIn,
    GenerateResponse,
    JDIn,
    JDResponse,
    UnblockIn,
    LWIDetail,
    LWIOut,
    PostureOut,
    PreviewIn,
    PreviewOut,
    ReadinessMatrix,
    ReadinessRow,
    ReasoningStep,
    SkillGraphResponse,
    StatusIn,
    TicketIn,
)
from app.config import get_settings
from app.security.auth import PERSONA_FOR_ROLE, session_for
from app.security.pii import redact_pii
from app.security.pipeline import guard_untrusted
from app.services.ai import plan_evaluation, plan_jd, plan_sprint, plan_unblock
from app.services.blocker import assert_can_enter, passing_readiness
from app.services.board import (
    audit,
    blocked_core_count,
    boost_skill,
    index_items,
    loads,
    lwis_for,
    next_ticket_code,
    persona_user,
    semester_progress,
    skill_out,
    skills_for,
    sprint_out,
    student_or_404,
    to_detail,
    to_lwi,
    top_gap,
    verified_average,
    visible_sprints,
    window_dates,
)
from app.models import utcnow

router = APIRouter(prefix="/api/v1")

INSTITUTION = {
    "university": "CampusFlow University",
    "college": "School of Computing",
    "department": "CSE",
}


def bearer_token(authorization: str) -> str:
    scheme, _, token = authorization.partition(" ")
    return token.strip() if scheme.lower() == "bearer" else ""


def current_persona(
    authorization: str = Header(default=""),
    x_persona: str = Header(default=""),
    db: Session = Depends(get_db),
) -> str:
    token = bearer_token(authorization)
    if token:
        session = session_for(db, token)
        user = db.get(User, session.user_id) if session else None
        if user is None or user.role not in PERSONA_FOR_ROLE:
            raise HTTPException(status_code=401, detail="Your session has ended. Sign in again.")
        return PERSONA_FOR_ROLE[user.role]
    if get_settings().allow_persona_header and x_persona:
        persona = x_persona.strip().lower()
        if persona not in {"student", "faculty", "tpo"}:
            raise HTTPException(status_code=401, detail="Unknown persona")
        return persona
    raise HTTPException(status_code=401, detail="Sign in to continue")


def require(*allowed: str):
    def dependency(persona: str = Depends(current_persona)) -> str:
        if persona not in allowed:
            raise HTTPException(status_code=403, detail="This view is outside the current role")
        return persona

    return dependency


def _trace(*labels: str) -> list[ReasoningStep]:
    return [ReasoningStep(step=index + 1, label=label) for index, label in enumerate(labels)]


def _own_lwi(db: Session, lwi_id: int, student: User) -> LearningWorkItem:
    item = db.get(LearningWorkItem, lwi_id)
    if item is None or item.student_id != student.id:
        raise HTTPException(status_code=404, detail="Learning work item not found")
    return item


def _persist_items(db: Session, student: User, sprint: Sprint, plan_items) -> list[LearningWorkItem]:
    created: list[LearningWorkItem] = []
    for item in plan_items:
        safe_title, _, _ = redact_pii(item.title)
        safe_description, _, _ = redact_pii(item.description)
        row = LearningWorkItem(
            sprint_id=sprint.id,
            student_id=student.id,
            ticket_code=next_ticket_code(db, sprint.course_code),
            title=safe_title[:200],
            description=safe_description,
            type=item.type if item.type in {"EPIC", "TASK", "SUBTASK"} else "TASK",
            status="BACKLOG",
            story_points=item.story_points,
            skill_tag=item.skill_tag,
            prerequisite_id=None,
            co_tag=item.co_tag,
            rubric_criteria=json.dumps(item.rubric_criteria),
            created_at=utcnow(),
        )
        db.add(row)
        db.flush()
        created.append(row)
    for index, item in enumerate(plan_items):
        if item.prerequisite_index is not None and 0 <= item.prerequisite_index < index:
            created[index].prerequisite_id = created[item.prerequisite_index].id
    db.flush()
    return created


def _serialize_many(db: Session, student_id: int, sprint_id: int) -> list[LWIOut]:
    items = lwis_for(db, student_id, sprint_id)
    by_id = index_items(lwis_for(db, student_id))
    return [to_lwi(item, by_id) for item in items]


def _remediation(db: Session, parent: LearningWorkItem, title: str, question: str) -> LearningWorkItem:
    marker = f"parent_id={parent.id};"
    existing = (
        db.query(LearningWorkItem)
        .filter(
            LearningWorkItem.student_id == parent.student_id,
            LearningWorkItem.sprint_id == parent.sprint_id,
            LearningWorkItem.description.contains(marker),
            LearningWorkItem.status != "MASTERED",
        )
        .first()
    )
    if existing:
        return existing
    sprint = db.get(Sprint, parent.sprint_id)
    course = sprint.course_code if sprint else "LWI"
    row = LearningWorkItem(
        sprint_id=parent.sprint_id,
        student_id=parent.student_id,
        ticket_code=next_ticket_code(db, course),
        title=title[:180],
        description=f"{marker}. Fifteen-minute remediation before retrying {parent.ticket_code}. {question}",
        type="SUBTASK",
        status="BACKLOG",
        story_points=1,
        skill_tag=parent.skill_tag,
        prerequisite_id=None,
        co_tag=parent.co_tag,
        rubric_criteria=parent.rubric_criteria,
        created_at=utcnow(),
    )
    db.add(row)
    db.flush()
    return row


@router.get("/bootstrap", response_model=Bootstrap)
def bootstrap(persona: str = Depends(current_persona), db: Session = Depends(get_db)) -> Bootstrap:
    actor = persona_user(db, persona)
    student = actor if actor.role == "STUDENT" else persona_user(db, "student")
    sprints = visible_sprints(db, student.id)
    from app.config import get_settings
    from app.services.signals import inbox_counts

    unread, next_poll = inbox_counts(db, actor.id if actor.role == "STUDENT" else 0)
    return Bootstrap(
        actor={
            "id": actor.id,
            "name": actor.name,
            "role": actor.role,
            "department": actor.department,
            "semester": actor.semester,
            "avatar_initials": actor.avatar_initials,
            "anon_token": actor.anon_token,
            "program": actor.program,
            "cgpa": actor.cgpa,
        },
        institution=INSTITUTION,
        semester_label="Sem 5 · 2026–27",
        semester_progress=semester_progress(db, student.id),
        sprints=[sprint_out(db, sprint, student.id) for sprint in sprints],
        ai_mode=get_settings().ai_mode,
        security={
            "rbac": True,
            "pii_redaction": True,
            "prompt_injection_guard": True,
            "schema_validation": True,
            "rate_limit": "10/minute on AI routes",
            "transport": get_settings().ai_mode,
            "rss_poll": "every 8 hours",
        },
        signal_unread=unread,
        signal_next_poll=next_poll,
    )


@router.get("/dashboard", response_model=DashboardOut)
def dashboard(persona: str = Depends(require("student")), db: Session = Depends(get_db)) -> DashboardOut:
    from app.services.dashboard import build_dashboard

    return DashboardOut(**build_dashboard(db, persona_user(db, persona)))


@router.get("/sprints/{sprint_id}/board", response_model=list[LWIOut])
def board(sprint_id: int, persona: str = Depends(require("student")), db: Session = Depends(get_db)) -> list[LWIOut]:
    student = persona_user(db, persona)
    sprint = db.get(Sprint, sprint_id)
    if sprint is None:
        raise HTTPException(status_code=404, detail="Sprint not found")
    return _serialize_many(db, student.id, sprint.id)


@router.get("/lwi/{lwi_id}", response_model=LWIDetail)
def lwi_detail(lwi_id: int, persona: str = Depends(require("student")), db: Session = Depends(get_db)) -> LWIDetail:
    student = persona_user(db, persona)
    item = _own_lwi(db, lwi_id, student)
    return to_detail(item, lwis_for(db, student.id))


@router.patch("/lwi/{lwi_id}/status", response_model=LWIOut)
def move_status(
    lwi_id: int,
    body: StatusIn,
    persona: str = Depends(require("student")),
    db: Session = Depends(get_db),
) -> LWIOut:
    student = persona_user(db, persona)
    item = _own_lwi(db, lwi_id, student)
    items = lwis_for(db, student.id)
    by_id = index_items(items)
    refusal = assert_can_enter(item, body.status, by_id)
    if refusal:
        raise HTTPException(status_code=409, detail=refusal)
    entering_mastery = body.status == "MASTERED" and item.status != "MASTERED"
    item.status = body.status
    if entering_mastery:
        score = passing_readiness(item)
        if score is None:
            raise HTTPException(status_code=409, detail="Mastery needs a scored submission of 75 or above")
        boost_skill(db, student, item.skill_tag, item.ticket_code, score)
    audit(db, student, "lwi.status", f"{item.ticket_code} -> {body.status}")
    db.commit()
    db.refresh(item)
    return to_lwi(item, index_items(lwis_for(db, student.id)))


@router.post("/sprints/{sprint_id}/tickets", response_model=LWIOut)
def create_ticket(
    sprint_id: int,
    body: TicketIn,
    persona: str = Depends(require("student")),
    db: Session = Depends(get_db),
) -> LWIOut:
    student = persona_user(db, persona)
    sprint = db.get(Sprint, sprint_id)
    if sprint is None:
        raise HTTPException(status_code=404, detail="Sprint not found")
    has_work = (
        db.query(LearningWorkItem.id)
        .filter(LearningWorkItem.sprint_id == sprint.id, LearningWorkItem.student_id == student.id)
        .first()
    )
    if sprint.owner_student_id != student.id and not has_work:
        raise HTTPException(status_code=404, detail="Sprint not found")
    title, _, _ = redact_pii(body.title.strip())
    description, _, _ = redact_pii(body.description.strip())
    kind = body.type.strip().upper()
    if kind not in {"EPIC", "TASK", "SUBTASK"}:
        kind = "TASK"
    criteria = [line.strip()[:180] for line in body.rubric.splitlines() if line.strip()]
    if not criteria:
        criteria = ["States the result and one input that would break it."]
    row = LearningWorkItem(
        sprint_id=sprint.id,
        student_id=student.id,
        ticket_code=next_ticket_code(db, sprint.course_code),
        title=title[:200],
        description=description,
        type=kind,
        status="BACKLOG",
        story_points=body.story_points,
        skill_tag=body.skill_tag.strip()[:80],
        prerequisite_id=None,
        co_tag=body.co_tag.strip()[:20] or "CO1",
        rubric_criteria=json.dumps(criteria),
        created_at=utcnow(),
    )
    db.add(row)
    db.flush()
    audit(db, student, "lwi.create", f"{row.ticket_code} {row.title}")
    db.commit()
    db.refresh(row)
    return to_lwi(row, index_items(lwis_for(db, student.id)))


@router.post("/sprints/generate", response_model=GenerateResponse)
@limiter.limit("10/minute")
def generate_sprint(
    request: Request,
    response: Response,
    body: GenerateIn,
    persona: str = Depends(require("student")),
    db: Session = Depends(get_db),
) -> GenerateResponse:
    student = persona_user(db, persona)
    try:
        plan, guarded = plan_sprint(body.title, body.course_code, body.syllabus, body.duration_weeks)
    except Exception:
        from app.services.ai import fallback_sprint

        plan = fallback_sprint(body.title, body.course_code, body.syllabus, body.duration_weeks)
        guarded = guard_untrusted(body.syllabus, "deterministic-fallback")
    start, end = window_dates(body.duration_weeks)
    code = re.sub(r"[^A-Z0-9]", "", plan.course_code.upper())[:8] or "GEN101"
    sprint = Sprint(
        title=plan.title,
        course_code=code,
        start_date=start,
        end_date=end,
        co_po_tags=json.dumps(plan.co_po_tags),
        owner_student_id=student.id,
        kind="GENERATED",
    )
    db.add(sprint)
    db.flush()
    created = _persist_items(db, student, sprint, plan.items)
    audit(
        db,
        student,
        "sprint.generate",
        f"{code} items={len(created)} redactions={guarded.meta.redactions} flags={','.join(guarded.meta.injection_flags) or 'none'}",
    )
    db.commit()
    db.refresh(sprint)
    return GenerateResponse(
        sprint=sprint_out(db, sprint, student.id),
        items=_serialize_many(db, student.id, sprint.id),
        reasoning_trace=_trace("Parsing syllabus", "Mapping CO–PO", "Building Kanban"),
        guard=guarded.meta,
    )


@router.post("/lwi/{lwi_id}/unblock", response_model=AIActionResponse)
@limiter.limit("10/minute")
def unblock(
    request: Request,
    response: Response,
    lwi_id: int,
    body: UnblockIn,
    persona: str = Depends(require("student")),
    db: Session = Depends(get_db),
) -> AIActionResponse:
    student = persona_user(db, persona)
    item = _own_lwi(db, lwi_id, student)
    try:
        result, guarded = plan_unblock(body.message, item.skill_tag, item.ticket_code)
    except Exception:
        from app.services.ai import fallback_evaluation

        result = fallback_evaluation(body.message, [], item.skill_tag)
        guarded = guard_untrusted(body.message, "deterministic-fallback")
    remediation = None
    if result.refused_direct_solution:
        remediation = _remediation(
            db,
            item,
            result.remediation_title or f"15-min: {item.skill_tag} gap",
            result.guiding_question,
        )
    item.ai_feedback_json = json.dumps(
        {
            "mode": "unblock",
            "refused_direct_solution": result.refused_direct_solution,
            "diagnosed_gap": result.diagnosed_gap,
            "guiding_question": result.guiding_question,
            "transport": guarded.meta.transport,
        }
    )
    audit(db, student, "lwi.unblock", f"{item.ticket_code} refused={result.refused_direct_solution}")
    db.commit()
    fresh = index_items(lwis_for(db, student.id))
    return AIActionResponse(
        result=result,
        reasoning_trace=_trace("Diagnosing the gap", "Applying the Socratic guardrail", "Scheduling remediation"),
        lwi=to_lwi(fresh[item.id], fresh),
        remediation_lwi=to_lwi(fresh[remediation.id], fresh) if remediation else None,
        skills=[skill_out(node) for node in skills_for(db, student.id)],
        guard=guarded.meta,
    )


@router.post("/lwi/{lwi_id}/evaluate", response_model=AIActionResponse)
@limiter.limit("10/minute")
def evaluate(
    request: Request,
    response: Response,
    lwi_id: int,
    body: EvaluateIn,
    persona: str = Depends(require("student")),
    db: Session = Depends(get_db),
) -> AIActionResponse:
    student = persona_user(db, persona)
    item = _own_lwi(db, lwi_id, student)
    rubric = []
    try:
        rubric = json.loads(item.rubric_criteria or "[]")
    except json.JSONDecodeError:
        rubric = []
    try:
        result, guarded = plan_evaluation(body.submission, rubric, item.skill_tag, item.ticket_code)
    except Exception:
        from app.services.ai import fallback_evaluation

        result = fallback_evaluation(body.submission, rubric, item.skill_tag)
        guarded = guard_untrusted(body.submission, "deterministic-fallback")
    remediation = None
    if result.refused_direct_solution:
        remediation = _remediation(
            db,
            item,
            result.remediation_title or f"15-min: {item.skill_tag} gap",
            result.guiding_question,
        )
    else:
        score = result.readiness_score or 0
        boost_skill(db, student, item.skill_tag, item.ticket_code, score)
    item.ai_feedback_json = result.model_dump_json()
    if not result.refused_direct_solution:
        score = result.readiness_score or 0
        items = lwis_for(db, student.id)
        by_id = index_items(items)
        if score >= 75 and item.status in {"BACKLOG", "IN_PROGRESS"} and not assert_can_enter(item, "AI_REVIEW", by_id):
            item.status = "AI_REVIEW"
    audit(
        db,
        student,
        "lwi.evaluate",
        f"{item.ticket_code} refused={result.refused_direct_solution} score={result.readiness_score}",
    )
    db.commit()
    fresh = index_items(lwis_for(db, student.id))
    return AIActionResponse(
        result=result,
        reasoning_trace=_trace("Parsing rubric", "Checking edge cases", "Updating skill graph"),
        lwi=to_lwi(fresh[item.id], fresh),
        remediation_lwi=to_lwi(fresh[remediation.id], fresh) if remediation else None,
        skills=[skill_out(node) for node in skills_for(db, student.id)],
        guard=guarded.meta,
    )


@router.post("/placement/analyze-jd", response_model=JDResponse)
@limiter.limit("10/minute")
def analyze_jd(
    request: Request,
    response: Response,
    body: JDIn,
    persona: str = Depends(require("student")),
    db: Session = Depends(get_db),
) -> JDResponse:
    student = persona_user(db, persona)
    scores = {node.skill_name: node.proficiency_score for node in skills_for(db, student.id)}
    try:
        plan, guarded = plan_jd(body.job_description, scores)
    except Exception:
        from app.services.ai import fallback_jd

        plan = fallback_jd(body.job_description, scores)
        guarded = guard_untrusted(body.job_description, "deterministic-fallback")
    start, end = window_dates(2)
    sprint = Sprint(
        title=f"14-Day Placement Prep · {plan.role_title}"[:180],
        course_code="PLACE",
        start_date=start,
        end_date=end,
        co_po_tags=json.dumps(["PO5", "PO8"]),
        owner_student_id=student.id,
        kind="PLACEMENT",
    )
    db.add(sprint)
    db.flush()
    _persist_items(db, student, sprint, plan.prep_items)
    audit(db, student, "placement.analyze", f"match={plan.match_percent} missing={len(plan.missing_skills)}")
    db.commit()
    db.refresh(sprint)
    return JDResponse(
        role_title=plan.role_title,
        match_percent=plan.match_percent,
        matched_skills=plan.matched_skills,
        missing_skills=plan.missing_skills,
        summary=plan.summary,
        sprint=sprint_out(db, sprint, student.id),
        items=_serialize_many(db, student.id, sprint.id),
        reasoning_trace=_trace("Reading the job description", "Matching the skill graph", "Injecting the prep sprint"),
        guard=guarded.meta,
    )


@router.get("/students/{student_id}/skill-graph", response_model=SkillGraphResponse)
def skill_graph(
    student_id: int,
    persona: str = Depends(require("student", "faculty", "tpo")),
    db: Session = Depends(get_db),
) -> SkillGraphResponse:
    actor = persona_user(db, persona)
    if persona == "student" and actor.id != student_id:
        raise HTTPException(status_code=403, detail="Students can open only their own skill graph")
    student = student_or_404(db, student_id)
    nodes = skills_for(db, student.id)
    return SkillGraphResponse(
        student_id=student.id,
        student_name=student.name,
        anon_token=student.anon_token,
        verified_skill_score=verified_average(nodes),
        skills=[skill_out(node) for node in nodes],
    )


@router.get("/faculty/cohort-health", response_model=CohortHealth)
def cohort_health(persona: str = Depends(require("faculty")), db: Session = Depends(get_db)) -> CohortHealth:
    students = db.query(User).filter(User.role == "STUDENT").order_by(User.id).all()
    rows: list[CohortStudent] = []
    for student in students:
        nodes = skills_for(db, student.id)
        blocked = blocked_core_count(db, student.id)
        reasons: list[str] = []
        if student.velocity_drop_pct > 35:
            reasons.append(f"Sprint velocity dropped {student.velocity_drop_pct:.0f}%")
        if blocked > 2:
            reasons.append(f"{blocked} core tickets are blocked")
        rows.append(
            CohortStudent(
                id=student.id,
                name=student.name,
                avatar_initials=student.avatar_initials,
                semester=student.semester,
                cgpa=student.cgpa,
                velocity_drop_pct=student.velocity_drop_pct,
                blocked_core=blocked,
                at_risk=bool(reasons),
                risk_reasons=reasons,
                top_gap=top_gap(nodes),
                anon_token=student.anon_token,
                verified_skill_score=verified_average(nodes),
            )
        )
    cohort = len(rows) or 1
    return CohortHealth(
        cohort_size=len(rows),
        at_risk_count=sum(1 for row in rows if row.at_risk),
        avg_velocity_drop=round(sum(row.velocity_drop_pct for row in rows) / cohort, 1),
        avg_verified_skill=round(sum(row.verified_skill_score for row in rows) / cohort, 1),
        students=rows,
    )


@router.get("/tpo/readiness", response_model=ReadinessMatrix)
def readiness(persona: str = Depends(require("tpo", "faculty")), db: Session = Depends(get_db)) -> ReadinessMatrix:
    students = db.query(User).filter(User.role == "STUDENT").order_by(User.id).all()
    rows: list[ReadinessRow] = []
    for student in students:
        nodes = skills_for(db, student.id)
        score = verified_average(nodes)
        top = [node.skill_name for node in nodes[:3]]
        hashes = [node.evidence_hash for node in nodes if node.evidence_hash][:3]
        rows.append(
            ReadinessRow(
                id=student.id,
                name=student.name,
                avatar_initials=student.avatar_initials,
                program=student.program,
                cgpa=student.cgpa,
                verified_skill_score=score,
                verified_lwi_count=sum(node.verified_lwi_count for node in nodes),
                top_skills=top,
                evidence_hashes=hashes,
                shortlist=score >= 70,
            )
        )
    rows.sort(key=lambda row: row.verified_skill_score, reverse=True)
    return ReadinessMatrix(rows=rows, threshold=70)


@router.post("/security/preview", response_model=PreviewOut)
@limiter.limit("20/minute")
def security_preview(
    request: Request,
    response: Response,
    body: PreviewIn,
    persona: str = Depends(current_persona),
    db: Session = Depends(get_db),
) -> PreviewOut:
    guarded = guard_untrusted(body.text)
    actor = persona_user(db, persona)
    audit(db, actor, "security.preview", f"redactions={guarded.meta.redactions} flags={len(guarded.meta.injection_flags)}")
    db.commit()
    return PreviewOut(
        redacted_text=guarded.redacted,
        redaction_count=guarded.meta.redactions,
        redaction_types=guarded.meta.redaction_types,
        injection_flags=guarded.meta.injection_flags,
        wrapped_preview=guarded.wrapped,
    )


@router.get("/security/posture", response_model=PostureOut)
def posture(persona: str = Depends(current_persona), db: Session = Depends(get_db)) -> PostureOut:
    from app.config import get_settings
    from app.models import AuditEvent

    events = db.query(AuditEvent).order_by(AuditEvent.id.desc()).limit(6).all()
    return PostureOut(
        ai_mode=get_settings().ai_mode,
        controls=[
            {"name": "Structured output", "detail": "Gemini JSON is validated with Pydantic. A failed parse retries once, then a deterministic plan is returned."},
            {"name": "Socratic guardrail", "detail": "Direct-solution requests never receive finished code. A 15-minute remediation ticket is filed instead."},
            {"name": "Prompt boundary", "detail": "Syllabi, submissions, and job descriptions are neutralized and wrapped in student_submission tags."},
            {"name": "PII redaction", "detail": "Emails, phone numbers, and roll numbers are replaced with tokens before any model call. Raw values are not logged."},
            {"name": "Sign-in", "detail": "Every route needs a session token. Passwords are salted scrypt hashes, tokens are stored hashed, sign-out revokes them, and login is limited to 20 tries a minute."},
            {"name": "RBAC", "detail": "The role comes from the signed-in account, not the browser. Students cannot open faculty views or another student's skill graph."},
            {"name": "Rate limit", "detail": "AI generation routes are limited to 10 requests per minute per IP."},
            {"name": "Secrets", "detail": "The Gemini key is read from the environment. .env.example is the only env file in source control."},
        ],
        recent_audit=[
            AuditOut(action=event.action, detail=event.detail, actor_role=event.actor_role, created_at=event.created_at)
            for event in events
        ],
    )
