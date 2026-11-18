from typing import Literal

from pydantic import BaseModel, Field

from app.security.pipeline import GuardMeta

Status = Literal["BACKLOG", "IN_PROGRESS", "AI_REVIEW", "MASTERED"]
ItemType = Literal["EPIC", "TASK", "SUBTASK"]
Persona = Literal["student", "faculty", "tpo"]


class ReasoningStep(BaseModel):
    step: int
    label: str
    state: Literal["done"] = "done"


class ActorOut(BaseModel):
    id: int
    name: str
    role: str
    department: str
    semester: int
    avatar_initials: str
    anon_token: str
    program: str
    cgpa: float


class SprintOut(BaseModel):
    id: int
    title: str
    course_code: str
    start_date: str
    end_date: str
    co_po_tags: list[str]
    kind: str
    lwi_count: int
    mastered_count: int
    progress_percent: int


class LWIOut(BaseModel):
    id: int
    sprint_id: int
    student_id: int
    ticket_code: str
    title: str
    description: str
    type: str
    status: str
    story_points: int
    skill_tag: str
    prerequisite_id: int | None
    prerequisite_code: str | None = None
    prerequisite_title: str | None = None
    blocked: bool
    block_reason: str | None = None
    co_tag: str
    rubric_criteria: list[str]
    ai_feedback: dict | None = None


class ChainNode(BaseModel):
    id: int
    ticket_code: str
    title: str
    status: str
    blocked: bool


class LWIDetail(LWIOut):
    prerequisite_chain: list[ChainNode]
    dependents: list[ChainNode]


class SkillOut(BaseModel):
    id: int
    skill_name: str
    proficiency_score: int
    verified_lwi_count: int
    evidence_tickets: list[str]
    evidence_hash: str
    last_updated: str


class SkillGraphResponse(BaseModel):
    student_id: int
    student_name: str
    anon_token: str
    verified_skill_score: int
    skills: list[SkillOut]


class RubricCheck(BaseModel):
    criterion: str
    passed: bool
    note: str


class EvaluationResult(BaseModel):
    refused_direct_solution: bool
    diagnosed_gap: str
    guiding_question: str
    readiness_score: int | None = Field(default=None, ge=0, le=100)
    checks: list[RubricCheck] = Field(default_factory=list)
    actionable_fixes: list[str] = Field(default_factory=list)
    remediation_title: str | None = None


class AIActionResponse(BaseModel):
    result: EvaluationResult
    reasoning_trace: list[ReasoningStep]
    lwi: LWIOut
    remediation_lwi: LWIOut | None = None
    skills: list[SkillOut] = Field(default_factory=list)
    guard: GuardMeta


class GenerateIn(BaseModel):
    title: str = Field(min_length=3, max_length=120)
    course_code: str = Field(min_length=2, max_length=16)
    duration_weeks: int = Field(default=4, ge=1, le=18)
    syllabus: str = Field(min_length=20, max_length=12000)


class GenerateResponse(BaseModel):
    sprint: SprintOut
    items: list[LWIOut]
    reasoning_trace: list[ReasoningStep]
    guard: GuardMeta


class TicketIn(BaseModel):
    title: str = Field(min_length=3, max_length=180)
    description: str = Field(default="", max_length=4000)
    type: str = Field(default="TASK", max_length=20)
    story_points: int = Field(default=3, ge=1, le=13)
    skill_tag: str = Field(min_length=2, max_length=80)
    co_tag: str = Field(default="CO1", max_length=20)
    rubric: str = Field(default="", max_length=800)


class StatusIn(BaseModel):
    status: Status


class UnblockIn(BaseModel):
    message: str = Field(min_length=4, max_length=8000)


class EvaluateIn(BaseModel):
    submission: str = Field(min_length=4, max_length=8000)


class JDIn(BaseModel):
    job_description: str = Field(min_length=20, max_length=8000)


class JDResponse(BaseModel):
    role_title: str
    match_percent: int = Field(ge=0, le=100)
    matched_skills: list[str]
    missing_skills: list[str]
    summary: str
    sprint: SprintOut
    items: list[LWIOut]
    reasoning_trace: list[ReasoningStep]
    guard: GuardMeta


class CohortStudent(BaseModel):
    id: int
    name: str
    avatar_initials: str
    semester: int
    cgpa: float
    velocity_drop_pct: float
    blocked_core: int
    at_risk: bool
    risk_reasons: list[str]
    top_gap: str | None
    anon_token: str
    verified_skill_score: int


class CohortHealth(BaseModel):
    cohort_size: int
    at_risk_count: int
    avg_velocity_drop: float
    avg_verified_skill: float
    students: list[CohortStudent]


class ReadinessRow(BaseModel):
    id: int
    name: str
    avatar_initials: str
    program: str
    cgpa: float
    verified_skill_score: int
    verified_lwi_count: int
    top_skills: list[str]
    evidence_hashes: list[str]
    shortlist: bool


class ReadinessMatrix(BaseModel):
    rows: list[ReadinessRow]
    threshold: int = 70


class Bootstrap(BaseModel):
    actor: ActorOut
    institution: dict
    semester_label: str
    semester_progress: int
    sprints: list[SprintOut]
    ai_mode: str
    security: dict
    signal_unread: int = 0
    signal_next_poll: str | None = None


class FeedIn(BaseModel):
    url: str = Field(min_length=12, max_length=500)
    label: str = Field(default="", max_length=160)


class FeedOut(BaseModel):
    id: int
    label: str
    url: str
    last_polled_at: str | None
    next_poll_at: str | None
    last_status: str
    last_error: str
    items_seen: int
    items_kept: int


class SourceLink(BaseModel):
    source: str
    url: str


class StoryBadge(BaseModel):
    kind: str
    label: str
    detail: str = ""


class SignalMessageOut(BaseModel):
    id: int
    title: str
    url: str
    source: str
    published_at: str
    summary: str
    brief: str = ""
    brief_source: str = "local"
    subscription_id: int
    relevance_score: int
    relevance_reason: str
    sentiment: str
    sentiment_score: int
    sentiment_reason: str
    cluster_label: str
    is_read: bool
    created_at: str
    sources: list[SourceLink] = Field(default_factory=list)
    badges: list[StoryBadge] = Field(default_factory=list)
    task_lwi_id: int | None = None
    quiz_passed: bool = False


class StoryTaskOut(BaseModel):
    lwi: LWIOut
    sprint: SprintOut
    created: bool
    transport: str


class ExplainerOut(BaseModel):
    concept: str
    use_case: str
    question: str
    options: list[str]
    source: str
    quiz_passed: bool


class QuizIn(BaseModel):
    choice: int = Field(ge=0, le=3)


class QuizOut(BaseModel):
    correct: bool
    why: str
    xp_awarded: int
    skill: str | None
    skill_score: int | None
    already_passed: bool


class DriftTrend(BaseModel):
    term: str
    stories: int
    share: int
    in_syllabus: bool
    suggestion: str


class DriftAlert(BaseModel):
    level: str
    title: str
    detail: str


class DriftSubtopic(BaseModel):
    label: str
    count: int
    critical: int
    positive: int
    watchful: int


class DriftRadar(BaseModel):
    total_stories: int
    students: int
    trends: list[DriftTrend]
    alerts: list[DriftAlert]
    subtopics: list[DriftSubtopic]


class ClusterOut(BaseModel):
    label: str
    count: int
    unread: int
    dominant_sentiment: str
    sentiments: dict[str, int]


class SignalInbox(BaseModel):
    unread: int
    feeds: list[FeedOut]
    clusters: list[ClusterOut]
    messages: list[SignalMessageOut]
    pipeline: list[str]


class SentimentRow(BaseModel):
    id: int
    title: str
    source: str
    published_at: str
    sentiment: str
    sentiment_score: int
    relevance_score: int
    topic: str
    is_read: bool


class InterestCluster(BaseModel):
    label: str
    count: int
    average_sentiment: int
    dominant_sentiment: str
    sentiments: dict[str, int]
    keywords: list[str]
    story_ids: list[int]


class InterestAnalysis(BaseModel):
    feed: FeedOut
    total: int
    average_sentiment: int
    average_relevance: int
    sentiments: dict[str, int]
    rows: list[SentimentRow]
    clusters: list[InterestCluster]


class SignalPulse(BaseModel):
    clusters: list[ClusterOut]
    message_count: int


class SubscribeResult(BaseModel):
    feed: FeedOut
    seen: int
    kept: int
    held: int
    fused: int = 0
    next_poll_at: str | None


class PreviewIn(BaseModel):
    text: str = Field(min_length=1, max_length=4000)


class PreviewOut(BaseModel):
    redacted_text: str
    redaction_count: int
    redaction_types: list[str]
    injection_flags: list[str]
    wrapped_preview: str


class AuditOut(BaseModel):
    action: str
    detail: str
    actor_role: str
    created_at: str


class PostureOut(BaseModel):
    ai_mode: str
    controls: list[dict]
    recent_audit: list[AuditOut]


class TicketSummary(BaseModel):
    total: int
    backlog: int
    in_progress: int
    ai_review: int
    mastered: int
    blocked: int
    points_total: int
    points_mastered: int


class SkillBrief(BaseModel):
    name: str
    score: int


class SkillSummary(BaseModel):
    count: int
    top: list[SkillBrief]
    weakest: SkillBrief | None


class StoryBrief(BaseModel):
    id: int
    title: str
    sentiment: str
    topic: str
    is_read: bool


class InterestSummary(BaseModel):
    topics: int
    saved: int
    unread: int
    sentiments: dict[str, int]
    next_fetch: str | None
    latest: list[StoryBrief]


class NextAction(BaseModel):
    kind: str
    title: str
    detail: str
    view: str


class DashboardStudent(BaseModel):
    name: str
    anon_token: str
    program: str
    semester: int
    cgpa: float
    avatar_initials: str


class DashboardOut(BaseModel):
    student: DashboardStudent
    semester_progress: int
    verified_skill_score: int
    shortlist_ready: bool
    shortlist_bar: int
    tickets: TicketSummary
    sprints: list[SprintOut]
    skills: SkillSummary
    interests: InterestSummary
    next_actions: list[NextAction]
    activity: list[AuditOut]


class LoginIn(BaseModel):
    email: str = Field(min_length=3, max_length=160)
    password: str = Field(min_length=1, max_length=128)


class SessionUser(BaseModel):
    id: int
    name: str
    email: str
    role: str
    persona: str
    avatar_initials: str
    program: str


class LoginOut(BaseModel):
    token: str
    expires_at: str
    user: SessionUser


class HealthOut(BaseModel):
    status: str
    service: str
    database: str
    ai_mode: str
    security: list[str]
