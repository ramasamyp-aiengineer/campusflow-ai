from datetime import UTC, datetime

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utcnow() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    role: Mapped[str] = mapped_column(String(20), index=True)
    department: Mapped[str] = mapped_column(String(80), default="CSE")
    semester: Mapped[int] = mapped_column(Integer, default=5)
    avatar_initials: Mapped[str] = mapped_column(String(4))
    anon_token: Mapped[str] = mapped_column(String(32), unique=True)
    cgpa: Mapped[float] = mapped_column(Float, default=0)
    velocity_drop_pct: Mapped[float] = mapped_column(Float, default=0)
    is_persona: Mapped[bool] = mapped_column(Boolean, default=False)
    program: Mapped[str] = mapped_column(String(80), default="B.Tech CSE")
    email: Mapped[str | None] = mapped_column(String(160), unique=True, index=True, nullable=True)
    password_hash: Mapped[str] = mapped_column(String(255), default="")


class AuthSession(Base):
    __tablename__ = "auth_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    created_at: Mapped[str] = mapped_column(String(40), default=utcnow)
    expires_at: Mapped[str] = mapped_column(String(40))
    revoked_at: Mapped[str | None] = mapped_column(String(40), nullable=True)


class Sprint(Base):
    __tablename__ = "sprints"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    course_code: Mapped[str] = mapped_column(String(20), index=True)
    start_date: Mapped[str] = mapped_column(String(20))
    end_date: Mapped[str] = mapped_column(String(20))
    co_po_tags: Mapped[str] = mapped_column(Text, default="[]")
    owner_student_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    kind: Mapped[str] = mapped_column(String(20), default="COURSE")


class LearningWorkItem(Base):
    __tablename__ = "learning_work_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    sprint_id: Mapped[int] = mapped_column(ForeignKey("sprints.id"), index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    ticket_code: Mapped[str] = mapped_column(String(32), index=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    type: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20), default="BACKLOG", index=True)
    story_points: Mapped[int] = mapped_column(Integer, default=3)
    skill_tag: Mapped[str] = mapped_column(String(80))
    prerequisite_id: Mapped[int | None] = mapped_column(ForeignKey("learning_work_items.id"), nullable=True)
    co_tag: Mapped[str] = mapped_column(String(20), default="CO1")
    rubric_criteria: Mapped[str] = mapped_column(Text, default="[]")
    ai_feedback_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    cosigned_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    cosigned_at: Mapped[str | None] = mapped_column(String(40), nullable=True)
    created_at: Mapped[str] = mapped_column(String(40), default=utcnow)


class SkillNode(Base):
    __tablename__ = "skill_nodes"

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    skill_name: Mapped[str] = mapped_column(String(80))
    proficiency_score: Mapped[int] = mapped_column(Integer, default=0)
    verified_lwi_count: Mapped[int] = mapped_column(Integer, default=0)
    evidence_tickets: Mapped[str] = mapped_column(Text, default="[]")
    evidence_hash: Mapped[str] = mapped_column(String(64), default="")
    last_updated: Mapped[str] = mapped_column(String(40), default=utcnow)


class FeedSubscription(Base):
    __tablename__ = "feed_subscriptions"

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    url: Mapped[str] = mapped_column(String(500))
    label: Mapped[str] = mapped_column(String(160))
    last_polled_at: Mapped[str | None] = mapped_column(String(40), nullable=True)
    next_poll_at: Mapped[str | None] = mapped_column(String(40), nullable=True)
    last_status: Mapped[str] = mapped_column(String(20), default="idle")
    last_error: Mapped[str] = mapped_column(Text, default="")
    items_seen: Mapped[int] = mapped_column(Integer, default=0)
    items_kept: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[str] = mapped_column(String(40), default=utcnow)


class SignalMessage(Base):
    __tablename__ = "signal_messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    subscription_id: Mapped[int] = mapped_column(ForeignKey("feed_subscriptions.id"), index=True)
    guid: Mapped[str] = mapped_column(String(64), index=True)
    title: Mapped[str] = mapped_column(String(300))
    url: Mapped[str] = mapped_column(String(500))
    source: Mapped[str] = mapped_column(String(120), default="")
    published_at: Mapped[str] = mapped_column(String(40), default="")
    summary: Mapped[str] = mapped_column(Text, default="")
    brief: Mapped[str] = mapped_column(Text, default="")
    brief_source: Mapped[str] = mapped_column(String(20), default="local")
    relevance_score: Mapped[int] = mapped_column(Integer, default=0)
    relevance_reason: Mapped[str] = mapped_column(Text, default="")
    sentiment: Mapped[str] = mapped_column(String(20), default="Neutral")
    sentiment_score: Mapped[int] = mapped_column(Integer, default=0)
    sentiment_reason: Mapped[str] = mapped_column(Text, default="")
    cluster_label: Mapped[str] = mapped_column(String(80), default="Campus briefing")
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    sources_json: Mapped[str] = mapped_column(Text, default="[]")
    task_lwi_id: Mapped[int | None] = mapped_column(ForeignKey("learning_work_items.id"), nullable=True)
    explainer_json: Mapped[str] = mapped_column(Text, default="")
    quiz_passed: Mapped[bool] = mapped_column(Boolean, default=False)
    quiz_lock_until: Mapped[str] = mapped_column(String(40), default="")
    sample: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[str] = mapped_column(String(40), default=utcnow)


class ModelCooldown(Base):
    """Shared across processes so a model outage on one instance rests the model on the others."""

    __tablename__ = "model_cooldowns"

    model_name: Mapped[str] = mapped_column(String(80), primary_key=True)
    resting_until: Mapped[float] = mapped_column(Float, default=0)


class SchedulerLease(Base):
    """One instance at a time runs the feed poll."""

    __tablename__ = "scheduler_leases"

    name: Mapped[str] = mapped_column(String(40), primary_key=True)
    owner: Mapped[str] = mapped_column(String(64), default="")
    expires_at: Mapped[float] = mapped_column(Float, default=0)


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    actor_token: Mapped[str] = mapped_column(String(32))
    actor_role: Mapped[str] = mapped_column(String(20))
    action: Mapped[str] = mapped_column(String(80))
    detail: Mapped[str] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(String(40), default=utcnow)
