from collections import Counter

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.limiter import limiter
from app.models import FeedSubscription, SignalMessage
from app.schemas import (
    ClusterOut,
    DriftRadar,
    ExplainerOut,
    FeedIn,
    FeedOut,
    InterestAnalysis,
    QuizIn,
    QuizOut,
    SignalInbox,
    SignalMessageOut,
    SignalPulse,
    SourceLink,
    StoryBadge,
    StoryTaskOut,
    SubscribeResult,
)
from app.services.board import audit, index_items, lwis_for, persona_user, sprint_out, to_lwi
from app.services.story_actions import (
    BadgeContext,
    QuizLocked,
    answer_quiz,
    build_explainer,
    create_story_task,
    curriculum_drift,
    story_badges,
)
from app.services.signals import (
    BUILTIN_FEEDS,
    BUILTIN_URL,
    BRIEFING_XML,
    POLL_HOURS,
    analyze_interest,
    hours_remaining,
    ingest_xml,
    poll_is_due,
    poll_subscription,
    story_sources,
    validate_public_url,
)
from app.routers.api import require

router = APIRouter(prefix="/api/v1/signals")

PIPELINE = [
    "Interest and RSS link",
    "Automatic fetch",
    "Keep what matches the topic",
    "Summary, then one story at a time",
]


def _feed_out(feed: FeedSubscription) -> FeedOut:
    return FeedOut(
        id=feed.id,
        label=feed.label,
        url=feed.url,
        last_polled_at=feed.last_polled_at,
        next_poll_at=feed.next_poll_at,
        last_status=feed.last_status,
        last_error=feed.last_error,
        items_seen=feed.items_seen,
        items_kept=feed.items_kept,
    )


def _message_out(message: SignalMessage, context: BadgeContext | None = None) -> SignalMessageOut:
    return SignalMessageOut(
        sources=[SourceLink(**link) for link in story_sources(message)],
        badges=[StoryBadge(**badge) for badge in story_badges(message, context)] if context else [],
        task_lwi_id=message.task_lwi_id,
        quiz_passed=bool(message.quiz_passed),
        id=message.id,
        title=message.title,
        url=message.url,
        source=message.source,
        published_at=message.published_at,
        summary=message.summary,
        brief=message.brief or "",
        brief_source=message.brief_source or "local",
        subscription_id=message.subscription_id,
        relevance_score=message.relevance_score,
        relevance_reason=message.relevance_reason,
        sentiment=message.sentiment,
        sentiment_score=message.sentiment_score,
        sentiment_reason=message.sentiment_reason,
        cluster_label=message.cluster_label,
        is_read=message.is_read,
        created_at=message.created_at,
    )


def _clusters(messages: list[SignalMessage]) -> list[ClusterOut]:
    grouped: dict[str, list[SignalMessage]] = {}
    for message in messages:
        grouped.setdefault(message.cluster_label, []).append(message)
    clusters: list[ClusterOut] = []
    for label, rows in grouped.items():
        counts = Counter(row.sentiment for row in rows)
        dominant = counts.most_common(1)[0][0]
        clusters.append(
            ClusterOut(
                label=label,
                count=len(rows),
                unread=sum(1 for row in rows if not row.is_read),
                dominant_sentiment=dominant,
                sentiments=dict(counts),
            )
        )
    clusters.sort(key=lambda cluster: cluster.count, reverse=True)
    return clusters


def _lock_detail(feed: FeedSubscription) -> str:
    return f"Not yet. This feed was scanned recently. The next public read is at {feed.next_poll_at}. CampusFlow waits {POLL_HOURS} hours between scans."


def _cooldown(feed: FeedSubscription) -> HTTPException:
    seconds = max(1, int((hours_remaining(feed) or 0) * 3600))
    return HTTPException(status_code=409, detail=_lock_detail(feed), headers={"Retry-After": str(seconds)})


@router.get("", response_model=SignalInbox)
def inbox(persona: str = Depends(require("student")), db: Session = Depends(get_db)) -> SignalInbox:
    student = persona_user(db, persona)
    feeds = db.query(FeedSubscription).filter(FeedSubscription.student_id == student.id).order_by(FeedSubscription.id).all()
    messages = (
        db.query(SignalMessage)
        .filter(SignalMessage.student_id == student.id)
        .order_by(SignalMessage.is_read, SignalMessage.id.desc())
        .all()
    )
    context = BadgeContext(db, student)
    return SignalInbox(
        unread=sum(1 for message in messages if not message.is_read),
        feeds=[_feed_out(feed) for feed in feeds],
        clusters=_clusters(messages),
        messages=[_message_out(message, context) for message in messages],
        pipeline=PIPELINE,
    )


@router.get("/pulse", response_model=SignalPulse)
def pulse(persona: str = Depends(require("faculty", "tpo")), db: Session = Depends(get_db)) -> SignalPulse:
    messages = db.query(SignalMessage).all()
    return SignalPulse(clusters=_clusters(messages), message_count=len(messages))


@router.post("/feeds", response_model=SubscribeResult)
@limiter.limit("6/minute")
def subscribe(
    request: Request,
    response: Response,
    body: FeedIn,
    persona: str = Depends(require("student")),
    db: Session = Depends(get_db),
) -> SubscribeResult:
    student = persona_user(db, persona)
    raw_url = body.url.strip()
    if raw_url in BUILTIN_FEEDS:
        url = raw_url
    else:
        try:
            url = validate_public_url(raw_url)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    feed = (
        db.query(FeedSubscription)
        .filter(FeedSubscription.student_id == student.id, FeedSubscription.url == url)
        .first()
    )
    if feed and not poll_is_due(feed):
        raise _cooldown(feed)
    is_new = feed is None
    if feed is None:
        label = body.label.strip() or urlparse_label(url)
        feed = FeedSubscription(student_id=student.id, url=url, label=label[:160], last_status="idle")
        db.add(feed)
        db.flush()
    try:
        stats = poll_subscription(db, student, feed)
    except PermissionError:
        raise _cooldown(feed) from None
    except ValueError as exc:
        if is_new:
            db.rollback()
        else:
            db.commit()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    audit(db, student, "signals.subscribe", f"kept={stats['kept']} held={stats['held']} fused={stats['fused']}")
    db.commit()
    db.refresh(feed)
    return SubscribeResult(
        feed=_feed_out(feed), seen=stats["seen"], kept=stats["kept"], held=stats["held"], fused=stats["fused"], next_poll_at=feed.next_poll_at
    )


@router.post("/briefing", response_model=SubscribeResult)
@limiter.limit("6/minute")
def briefing(
    request: Request,
    response: Response,
    persona: str = Depends(require("student")),
    db: Session = Depends(get_db),
) -> SubscribeResult:
    student = persona_user(db, persona)
    feed = (
        db.query(FeedSubscription)
        .filter(FeedSubscription.student_id == student.id, FeedSubscription.url == BUILTIN_URL)
        .first()
    )
    if feed and not poll_is_due(feed):
        raise _cooldown(feed)
    if feed is None:
        feed = FeedSubscription(
            student_id=student.id,
            url=BUILTIN_URL,
            label="Campus engineering briefing",
            last_status="idle",
        )
        db.add(feed)
        db.flush()
    stats = ingest_xml(db, student, feed, BRIEFING_XML)
    audit(db, student, "signals.briefing", f"kept={stats['kept']} held={stats['held']}")
    db.commit()
    db.refresh(feed)
    return SubscribeResult(
        feed=_feed_out(feed), seen=stats["seen"], kept=stats["kept"], held=stats["held"], fused=stats["fused"], next_poll_at=feed.next_poll_at
    )


def _own_message(db: Session, student, message_id: int) -> SignalMessage:
    message = db.get(SignalMessage, message_id)
    if message is None or message.student_id != student.id:
        raise HTTPException(status_code=404, detail="Story not found")
    return message


@router.post("/messages/{message_id}/task", response_model=StoryTaskOut)
@limiter.limit("10/minute")
def story_to_task(
    request: Request,
    response: Response,
    message_id: int,
    persona: str = Depends(require("student")),
    db: Session = Depends(get_db),
) -> StoryTaskOut:
    student = persona_user(db, persona)
    message = _own_message(db, student, message_id)
    row, sprint, created, transport = create_story_task(db, student, message)
    if created:
        audit(db, student, "signals.task", f"story={message.id} -> {row.ticket_code} via {transport}")
    db.commit()
    by_id = index_items(lwis_for(db, student.id))
    return StoryTaskOut(lwi=to_lwi(by_id[row.id], by_id), sprint=sprint_out(db, sprint, student.id), created=created, transport=transport)


@router.post("/messages/{message_id}/explain", response_model=ExplainerOut)
@limiter.limit("10/minute")
def explain_story(
    request: Request,
    response: Response,
    message_id: int,
    persona: str = Depends(require("student")),
    db: Session = Depends(get_db),
) -> ExplainerOut:
    student = persona_user(db, persona)
    message = _own_message(db, student, message_id)
    card, source = build_explainer(message)
    db.commit()
    return ExplainerOut(
        concept=card.concept, use_case=card.use_case, question=card.question, options=card.options, source=source, quiz_passed=bool(message.quiz_passed)
    )


@router.post("/messages/{message_id}/quiz", response_model=QuizOut)
@limiter.limit("20/minute")
def quiz_story(
    request: Request,
    response: Response,
    message_id: int,
    body: QuizIn,
    persona: str = Depends(require("student")),
    db: Session = Depends(get_db),
) -> QuizOut:
    student = persona_user(db, persona)
    message = _own_message(db, student, message_id)
    if not message.explainer_json:
        raise HTTPException(status_code=409, detail="Open the explainer before answering the check question")
    try:
        result = answer_quiz(db, student, message, body.choice)
    except QuizLocked as locked:
        raise HTTPException(status_code=429, detail=f"Wait {locked.seconds}s before another attempt") from locked
    if result["xp_awarded"]:
        audit(db, student, "signals.quiz", f"story={message.id} {result['skill']} +{result['xp_awarded']}")
    db.commit()
    return QuizOut(**result)


@router.get("/drift", response_model=DriftRadar)
def drift(persona: str = Depends(require("faculty", "tpo")), db: Session = Depends(get_db)) -> DriftRadar:
    return DriftRadar(**curriculum_drift(db))


@router.get("/feeds/{feed_id}/analysis", response_model=InterestAnalysis)
def interest_analysis(feed_id: int, persona: str = Depends(require("student")), db: Session = Depends(get_db)) -> InterestAnalysis:
    student = persona_user(db, persona)
    feed = db.get(FeedSubscription, feed_id)
    if feed is None or feed.student_id != student.id:
        raise HTTPException(status_code=404, detail="Interest not found")
    messages = (
        db.query(SignalMessage)
        .filter(SignalMessage.student_id == student.id, SignalMessage.subscription_id == feed.id)
        .order_by(SignalMessage.id.desc())
        .all()
    )
    return InterestAnalysis(feed=_feed_out(feed), **analyze_interest(messages, feed.label))


@router.delete("/feeds/{feed_id}")
def remove_feed(feed_id: int, persona: str = Depends(require("student")), db: Session = Depends(get_db)) -> dict:
    student = persona_user(db, persona)
    feed = db.get(FeedSubscription, feed_id)
    if feed is None or feed.student_id != student.id:
        raise HTTPException(status_code=404, detail="Feed not found")
    db.query(SignalMessage).filter(SignalMessage.subscription_id == feed.id).delete()
    db.delete(feed)
    audit(db, student, "signals.remove", f"feed={feed_id}")
    db.commit()
    return {"removed": feed_id}


@router.patch("/messages/{message_id}/read", response_model=SignalMessageOut)
def mark_read(message_id: int, persona: str = Depends(require("student")), db: Session = Depends(get_db)) -> SignalMessageOut:
    student = persona_user(db, persona)
    message = db.get(SignalMessage, message_id)
    if message is None or message.student_id != student.id:
        raise HTTPException(status_code=404, detail="Message not found")
    message.is_read = True
    db.commit()
    db.refresh(message)
    return _message_out(message)


def urlparse_label(url: str) -> str:
    from urllib.parse import urlparse

    host = urlparse(url).hostname or "RSS feed"
    return f"Google RSS · {host}" if "news.google." in host or "google." in host else f"RSS · {host}"
