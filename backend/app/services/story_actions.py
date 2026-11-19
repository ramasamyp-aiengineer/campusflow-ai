"""Turn kept stories into learning: badges, sprint tasks, explainers, quizzes, and the curriculum drift radar."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone

from pydantic import BaseModel, Field, ValidationError, model_validator
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import LearningWorkItem, SignalMessage, SkillNode, Sprint, User, utcnow
from app.security.pii import redact_pii
from app.services.signals import (
    SENTENCE,
    STOPWORDS,
    TOPICS,
    WORD,
    _cluster_for,
    mentions,
    plain,
    subtopic_for,
    tokens_of,
)

SKILL_HINTS: dict[str, tuple[str, ...]] = {
    "SQL": ("sql", "join", "query", "postgres", "database"),
    "FastAPI": ("fastapi",),
    "API Design": ("api", "endpoint", "rate-limit"),
    "Python": ("python",),
    "Operating Systems": ("kernel", "scheduler", "linux", "deadlock"),
    "Distributed Systems": ("distributed", "transaction", "consensus", "replication"),
    "Data Structures": ("hash", "b+ tree", "index"),
    "System Design": ("system design", "scalability", "latency", "architecture"),
    "DevOps": ("devops", "kubernetes", "docker", "deployment"),
    "Security Engineering": (
        "cybersecurity", "cyber", "breach", "leak", "vulnerability", "exploit", "cve", "ransomware", "phishing", "malware", "encryption", "authentication",
    ),
    "Relational Algebra": ("normalization", "relational"),
    "Frontend Engineering": ("react", "frontend"),
    "Machine Learning": ("machine learning", "neural", "training", "dataset", "lora", "fine-tuning", "model"),
}

READING_KIND = "READING"
READING_CODE = "LAB"
QUIZ_XP = 2


def story_text(message: SignalMessage) -> str:
    return f"{message.title} {message.summary}".lower()


def skills_in(text: str) -> list[str]:
    blob = text.lower()
    tokens = tokens_of(blob)
    found = []
    for skill, hints in SKILL_HINTS.items():
        if mentions(skill, blob, tokens) or any(mentions(hint, blob, tokens) for hint in hints):
            found.append(skill)
    return found


def _salient(title: str) -> set[str]:
    return {word.strip(".") for word in WORD.findall(title.lower()) if len(word) >= 4 and word.strip(".") not in STOPWORDS}


class BadgeContext:
    def __init__(self, db: Session, student: User):
        self.open_items = (
            db.query(LearningWorkItem)
            .filter(LearningWorkItem.student_id == student.id, LearningWorkItem.status != "MASTERED")
            .all()
        )
        self.items_by_id = {
            item.id: item
            for item in db.query(LearningWorkItem).filter(LearningWorkItem.student_id == student.id).all()
        }
        self.scores = {
            node.skill_name: node.proficiency_score
            for node in db.query(SkillNode).filter(SkillNode.student_id == student.id).all()
        }
        placement_ids = {
            sprint.id for sprint in db.query(Sprint).filter(Sprint.owner_student_id == student.id, Sprint.kind == "PLACEMENT")
        }
        self.placement_items = [item for item in self.open_items if item.sprint_id in placement_ids]


def story_badges(message: SignalMessage, context: BadgeContext) -> list[dict[str, str]]:
    text = story_text(message)
    tokens = tokens_of(text)
    skills = skills_in(text)
    badges: list[dict[str, str]] = []

    task = context.items_by_id.get(message.task_lwi_id) if message.task_lwi_id else None
    if task is not None:
        badges.append({"kind": "task", "label": f"On your board as {task.ticket_code}", "detail": task.title})

    best, best_score = None, 0
    for item in context.open_items:
        if task is not None and item.id == task.id:
            continue
        score = sum(1 for word in _salient(item.title) if mentions(word, text, tokens))
        score += 2 if item.skill_tag in skills else 0
        if score > best_score:
            best, best_score = item, score
    if best is not None and best_score >= 2:
        badges.append({"kind": "ticket", "label": f"Matches your active ticket {best.ticket_code}", "detail": best.title})

    gaps = sorted((context.scores[skill], skill) for skill in skills if skill in context.scores and context.scores[skill] < 70)
    if gaps:
        score, skill = gaps[0]
        badges.append({"kind": "gap", "label": f"Closes a skill gap: {skill} ({score})", "detail": f"{skill} is below the verified bar of 70."})

    if context.placement_items:
        for skill in skills:
            share = sum(1 for item in context.placement_items if item.skill_tag == skill)
            if share:
                percent = round(100 * share / len(context.placement_items))
                badges.append(
                    {"kind": "placement", "label": f"Placement prep: {skill} is {percent}% of your sprint", "detail": "Your job-description prep sprint includes this skill."}
                )
                break

    if not any(badge["kind"] in {"gap", "ticket"} for badge in badges):
        strong = sorted(((context.scores[skill], skill) for skill in skills if context.scores.get(skill, 0) >= 70), reverse=True)
        if strong:
            score, skill = strong[0]
            badges.append({"kind": "skill", "label": f"Builds on verified {skill} ({score})", "detail": "You already have evidence for this skill."})
    return badges[:3]


class StoryTaskPlan(BaseModel):
    title: str = Field(min_length=8, max_length=120)
    description: str = Field(min_length=20, max_length=700)
    skill_tag: str = Field(min_length=2, max_length=60)
    story_points: int = Field(default=3, ge=1, le=5)
    rubric_criteria: list[str] = Field(min_length=2, max_length=4)


TASK_HINT = (
    '{"title":"Verb-first lab title","description":"What to build, with which free dataset or tool, and what to record",'
    '"skill_tag":"one skill","story_points":3,"rubric_criteria":["str","str","str"]}'
)


def fallback_task(message: SignalMessage) -> StoryTaskPlan:
    skills = skills_in(story_text(message))
    skill = skills[0] if skills else "Software Engineering"
    short = plain(message.title)[:70].rstrip(" .,-")
    return StoryTaskPlan(
        title=f"Reproduce one claim from: {short}"[:120],
        description=(
            f"Read the story from {message.source or 'the feed'}. Pick the single measurable claim it makes, "
            "rebuild the smallest version you can run on your laptop, and record what you observed next to what the article reported."
        ),
        skill_tag=skill,
        story_points=3,
        rubric_criteria=[
            "States the claim being tested and where it came from",
            "Shows the smallest runnable setup and its measured result",
            "Names one reason the result could differ from the article",
        ],
    )


def plan_story_task(message: SignalMessage) -> tuple[StoryTaskPlan, str]:
    from app.security.pipeline import guard_untrusted
    from app.services.ai import complete_json

    guarded = guard_untrusted(f"{message.title}\n{message.summary}")
    skills = ", ".join(SKILL_HINTS)
    try:
        plan, transport = complete_json(
            "Turn this public article into one hands-on micro-lab that a third-year CSE student can finish in 2 to 4 hours. "
            "Start the title with a verb. Use a free dataset or a local tool. Give the steps to attempt, not the solution. "
            f"Pick skill_tag from: {skills}.",
            guarded,
            TASK_HINT,
            StoryTaskPlan,
        )
    except Exception:
        plan, transport = None, "deterministic-fallback"
    if plan is None:
        return fallback_task(message), "deterministic-fallback"
    plan.skill_tag = graph_skill(plan.skill_tag, message)
    return plan, transport


def graph_skill(tag: str, message: SignalMessage) -> str:
    """Keep task skills on the skill graph so later XP has a node to land on."""
    for skill in SKILL_HINTS:
        if skill.lower() == tag.strip().lower():
            return skill
    found = skills_in(tag) or skills_in(story_text(message))
    return found[0] if found else tag


def reading_sprint(db: Session, student: User) -> Sprint:
    sprint = (
        db.query(Sprint)
        .filter(Sprint.owner_student_id == student.id, Sprint.kind == READING_KIND)
        .order_by(Sprint.id)
        .first()
    )
    if sprint is not None:
        return sprint
    from app.services.board import assert_owned_sprint_capacity, window_dates

    assert_owned_sprint_capacity(db, student.id)

    start, end = window_dates(4)
    sprint = Sprint(
        title="Reading labs · from your interests",
        course_code=READING_CODE,
        start_date=start,
        end_date=end,
        co_po_tags=json.dumps(["PO12"]),
        owner_student_id=student.id,
        kind=READING_KIND,
    )
    db.add(sprint)
    db.flush()
    return sprint


def create_story_task(db: Session, student: User, message: SignalMessage) -> tuple[LearningWorkItem, Sprint, bool, str]:
    from app.services.board import next_ticket_code

    if message.task_lwi_id:
        existing = db.get(LearningWorkItem, message.task_lwi_id)
        if existing is not None:
            return existing, db.get(Sprint, existing.sprint_id), False, "existing"
    plan, transport = plan_story_task(message)
    sprint = reading_sprint(db, student)
    from app.services.board import assert_sprint_capacity

    assert_sprint_capacity(db, student.id, sprint.id)
    title, _, _ = redact_pii(plain(plan.title))
    description, _, _ = redact_pii(plain(plan.description))
    row = LearningWorkItem(
        sprint_id=sprint.id,
        student_id=student.id,
        ticket_code=next_ticket_code(db, sprint.course_code),
        title=title[:200],
        description=f"{description} Source: {message.source} · {message.url}"[:1200],
        type="TASK",
        status="BACKLOG",
        story_points=plan.story_points,
        skill_tag=plain(plan.skill_tag)[:80],
        prerequisite_id=None,
        co_tag="PO12",
        rubric_criteria=json.dumps([plain(item)[:180] for item in plan.rubric_criteria]),
        created_at=utcnow(),
    )
    db.add(row)
    db.flush()
    message.task_lwi_id = row.id
    message.is_read = True
    return row, sprint, True, transport


class Explainer(BaseModel):
    concept: str = Field(min_length=12, max_length=400)
    use_case: str = Field(min_length=12, max_length=400)
    question: str = Field(min_length=8, max_length=240)
    options: list[str] = Field(min_length=3, max_length=4)
    answer_index: int = Field(ge=0, le=3)
    why: str = Field(min_length=8, max_length=300)

    @model_validator(mode="after")
    def _answer_in_range(self) -> "Explainer":
        if self.answer_index >= len(self.options) or any(not option.strip() for option in self.options):
            raise ValueError("answer_index must point at a non-empty option")
        return self


EXPLAIN_HINT = (
    '{"concept":"one plain sentence","use_case":"one plain sentence","question":"one check question",'
    '"options":["a","b","c"],"answer_index":0,"why":"one sentence"}'
)


QUIZ_LOCK_SECONDS = 20


class QuizLocked(Exception):
    def __init__(self, seconds: int):
        self.seconds = max(1, seconds)
        super().__init__(f"quiz locked for {self.seconds}s")


def _quiz_answer_index(message_id: int, option_count: int = 3) -> int:
    secret = get_settings().app_secret.strip()
    if not secret:
        raise RuntimeError("APP_SECRET is required to generate quiz answers")
    digest = hashlib.sha256(f"{secret}:{message_id}".encode()).hexdigest()
    return int(digest, 16) % max(1, option_count)


def fallback_explainer(message: SignalMessage) -> Explainer:
    body = plain(message.summary or message.brief or message.title)
    sentences = [part.strip() for part in SENTENCE.split(body) if part.strip()]
    label, hits = _cluster_for(story_text(message))
    correct = label if hits else (skills_in(story_text(message)) or ["Software engineering"])[0]
    others = [topic for topic, _ in TOPICS if topic != correct]
    offset = message.id % len(others)
    distractors = [others[offset], others[(offset + 3) % len(others)]]
    position = _quiz_answer_index(message.id, 3)
    options = distractors[:position] + [correct] + distractors[position:]
    skills = skills_in(story_text(message))
    return Explainer(
        concept=(sentences[0] if sentences else plain(message.title))[:400],
        use_case=(
            sentences[1] if len(sentences) > 1 else f"You would meet this when you work on {skills[0] if skills else correct} in a real project."
        )[:400],
        question="Which area is this story mainly about?",
        options=options,
        answer_index=position,
        why=f"The story is about {correct.lower()}, which is where its key terms come from.",
    )


def cached_explainer(message: SignalMessage) -> tuple[Explainer, str] | None:
    if not message.explainer_json:
        return None
    try:
        cached = json.loads(message.explainer_json)
        return Explainer.model_validate(cached["card"]), cached.get("source", "local")
    except (json.JSONDecodeError, KeyError, ValidationError, TypeError):
        return None


def build_explainer(message: SignalMessage) -> tuple[Explainer, str]:
    cached = cached_explainer(message)
    # Once a card is issued, freeze it. Upgrading mid-attempt can move the answer key.
    if cached:
        return cached
    from app.security.pipeline import guard_untrusted
    from app.services.ai import complete_json

    guarded = guard_untrusted(f"{message.title}\n{message.summary}")
    try:
        card, transport = complete_json(
            "Explain this article to a third-year CSE student in plain words. concept: the core idea in one sentence. "
            "use_case: one real-world place this is used. Then write one multiple-choice check question with 3 options, "
            "exactly one correct, answerable from the concept alone. Avoid jargon.",
            guarded,
            EXPLAIN_HINT,
            Explainer,
        )
    except Exception:
        card, transport = None, "deterministic-fallback"
    source = "gemini" if card is not None and transport == "gemini" else "local"
    if card is None:
        if cached:
            return cached
        card = fallback_explainer(message)
    message.explainer_json = json.dumps({"card": card.model_dump(), "source": source})
    return card, source


def quiz_skills(db: Session, message: SignalMessage) -> list[str]:
    names: list[str] = []
    if message.task_lwi_id:
        task = db.get(LearningWorkItem, message.task_lwi_id)
        if task is not None:
            names.append(task.skill_tag)
    return names + skills_in(story_text(message))


def quiz_skill(db: Session, student: User, names: list[str]) -> SkillNode | None:
    for name in names:
        node = (
            db.query(SkillNode)
            .filter(SkillNode.student_id == student.id, SkillNode.skill_name == name)
            .first()
        )
        if node is not None:
            return node
    return None


def answer_quiz(db: Session, student: User, message: SignalMessage, choice: int) -> dict:
    now = datetime.now(timezone.utc)
    if message.quiz_lock_until:
        try:
            locked = datetime.fromisoformat(message.quiz_lock_until)
        except ValueError:
            locked = None
        if locked is not None:
            if locked.tzinfo is None:
                locked = locked.replace(tzinfo=timezone.utc)
            remaining = int((locked - now).total_seconds())
            if remaining > 0:
                raise QuizLocked(remaining)
    card, _ = cached_explainer(message) or build_explainer(message)
    correct = choice == card.answer_index
    result = {"correct": correct, "why": card.why if correct else "Not quite. Re-read the core concept and try again.",
              "xp_awarded": 0, "skill": None, "skill_score": None, "already_passed": message.quiz_passed}
    if not correct:
        message.quiz_lock_until = (now + timedelta(seconds=QUIZ_LOCK_SECONDS)).isoformat()
        return result
    message.quiz_lock_until = ""
    names = quiz_skills(db, message)
    result["skill"] = names[0] if names else None
    node = quiz_skill(db, student, names)
    if node is not None:
        result["skill"] = node.skill_name
        if not message.quiz_passed:
            node.proficiency_score = min(100, node.proficiency_score + QUIZ_XP)
            node.last_updated = utcnow()
            result["xp_awarded"] = QUIZ_XP
        result["skill_score"] = node.proficiency_score
    elif result["skill"]:
        result["why"] = (
            f"{result['why']} {result['skill']} is not on your skill graph yet. "
            "Finish a lab task on it to start that node, then quiz XP can land there."
        )
    else:
        result["why"] = f"{result['why']} This story has no linked skill on your graph, so no XP this time."
    message.quiz_passed = True
    return result


TREND_TERMS: list[tuple[str, tuple[str, ...]]] = [
    ("RAG evaluation", ("rag", "retrieval-augmented", "retrieval augmented")),
    ("Agentic workflows", ("agentic", "ai agent", "ai agents")),
    ("LLM fine-tuning", ("fine-tuning", "lora", "qlora", "finetuning")),
    ("Vector databases", ("vector database", "embeddings", "vector search")),
    ("MLOps", ("mlops", "model deployment", "model monitoring")),
    ("Generative AI", ("genai", "generative ai", "llm", "gemini", "chatgpt")),
    ("Cybersecurity", ("cybersecurity", "phishing", "ransomware", "breach")),
    ("Cloud and Kubernetes", ("kubernetes", "serverless", "cloud native")),
    ("SQL and databases", ("sql", "postgres", "database")),
    ("APIs and FastAPI", ("fastapi", "api")),
    ("Operating systems", ("kernel", "scheduler", "deadlock")),
    ("System design", ("system design", "scalability", "distributed")),
]
DRIFT_SHARE = 0.15
HIRING_ALERT_SHARE = 0.25


def _mentions_any(hints: tuple[str, ...], blob: str, tokens: set[str]) -> bool:
    return any(mentions(hint, blob, tokens) for hint in hints)


def curriculum_text(db: Session) -> str:
    parts = [sprint.title for sprint in db.query(Sprint).filter(Sprint.kind == "COURSE")]
    for item in (
        db.query(LearningWorkItem)
        .join(Sprint, Sprint.id == LearningWorkItem.sprint_id)
        .filter(Sprint.kind == "COURSE")
    ):
        parts.extend([item.title, item.description or "", item.skill_tag])
    return " ".join(parts).lower()


def curriculum_drift(db: Session) -> dict:
    messages = db.query(SignalMessage).all()
    total = len(messages)
    syllabus = curriculum_text(db)
    syllabus_tokens = tokens_of(syllabus)
    texts = [(message, story_text(message), tokens_of(story_text(message))) for message in messages]

    trends = []
    for term, hints in TREND_TERMS:
        count = sum(1 for _, blob, tokens in texts if _mentions_any(hints, blob, tokens))
        if not count:
            continue
        share = count / total
        covered = _mentions_any(hints, syllabus, syllabus_tokens)
        if covered:
            suggestion = "Already covered in a course sprint."
        elif share >= DRIFT_SHARE:
            suggestion = f"Not in the syllabus yet. Consider a {term} workshop."
        else:
            suggestion = "Not in the syllabus. Keep watching."
        trends.append({"term": term, "stories": count, "share": round(100 * share), "in_syllabus": covered, "suggestion": suggestion})
    trends.sort(key=lambda trend: (-trend["stories"], trend["term"]))

    subtopics: dict[str, dict[str, int]] = {}
    for message, _, _ in texts:
        label = subtopic_for(message.title, message.summary)
        bucket = subtopics.setdefault(label, {"count": 0, "critical": 0, "positive": 0, "watchful": 0})
        bucket["count"] += 1
        tone = message.sentiment.lower()
        if tone in bucket:
            bucket[tone] += 1

    alerts = []
    for trend in trends:
        if not trend["in_syllabus"] and trend["share"] >= round(100 * DRIFT_SHARE):
            alerts.append(
                {
                    "level": "watch",
                    "title": f"{trend['term']} is trending outside the syllabus",
                    "detail": f"{trend['share']}% of kept stories mention it and no course sprint covers it. Suggested: a short {trend['term']} workshop.",
                }
            )
    hiring_words = dict(TOPICS)["Placement market"]
    hiring = [message for message, blob, tokens in texts if _mentions_any(hiring_words, blob, tokens)]
    critical_hiring = sum(1 for message in hiring if message.sentiment == "Critical")
    if critical_hiring and critical_hiring / len(hiring) >= HIRING_ALERT_SHARE:
        alerts.insert(
            0,
            {
                "level": "critical",
                "title": "Hiring news is turning critical",
                "detail": f"{critical_hiring} of {len(hiring)} hiring stories read critical. Plan a placement readiness session before the drive.",
            },
        )
    for label, bucket in subtopics.items():
        if label != "Placement market" and bucket["count"] >= 2 and bucket["critical"] / bucket["count"] >= 0.5:
            alerts.append(
                {"level": "critical", "title": f"{label} stories are mostly critical", "detail": f"{bucket['critical']} of {bucket['count']} stories read critical."}
            )

    return {
        "total_stories": total,
        "students": len({message.student_id for message in messages}),
        "trends": trends[:8],
        "alerts": alerts[:5],
        "subtopics": [
            {"label": label, **bucket}
            for label, bucket in sorted(subtopics.items(), key=lambda pair: -pair[1]["count"])
            if label != "General"
        ][:6],
    }
