import json
import re
import time
from typing import TypeVar

import httpx
from pydantic import BaseModel, Field, ValidationError

from app.config import get_settings
from app.schemas import EvaluationResult, RubricCheck
from app.security.pipeline import GuardedText, build_model_prompt, guard_untrusted

T = TypeVar("T", bound=BaseModel)

DIRECT_SOLUTION = re.compile(
    r"\b("
    r"write the code|give me the code|complete (this |the )?assignment|"
    r"full solution|solve this for me|do my homework|write it for me|"
    r"give me the answer|finish (this|my) (code|assignment|lab)"
    r")\b",
    re.IGNORECASE,
)

SKILL_RULES: list[tuple[str, str]] = [
    ("query optim", "SQL"),
    ("b+ tree", "Data Structures"),
    ("b tree", "Data Structures"),
    ("index", "Data Structures"),
    ("transaction", "Distributed Systems"),
    ("isolation", "Distributed Systems"),
    ("normali", "Relational Algebra"),
    ("relational", "Relational Algebra"),
    ("functional dep", "Relational Algebra"),
    ("join", "SQL"),
    ("sql", "SQL"),
    ("deadlock", "Operating Systems"),
    ("schedul", "Operating Systems"),
    ("process", "Operating Systems"),
    ("memory", "Operating Systems"),
    ("operating system", "Operating Systems"),
    ("fastapi", "FastAPI"),
    ("react", "Frontend Engineering"),
    ("kubernetes", "DevOps"),
    ("docker", "DevOps"),
    ("system design", "System Design"),
    ("security", "Security Engineering"),
    ("rbac", "Security Engineering"),
    ("api", "API Design"),
    ("python", "Python"),
    ("graph", "Data Structures"),
]

JD_SKILLS = [
    "Python",
    "FastAPI",
    "SQL",
    "Data Structures",
    "Distributed Systems",
    "Operating Systems",
    "API Design",
    "System Design",
    "DevOps",
    "Security Engineering",
    "Frontend Engineering",
    "Relational Algebra",
]

GUIDES = {
    "SQL": "Which rows must survive when the other table has no match, and which join type keeps them?",
    "Relational Algebra": "Which dependency is violated by the current table, and what smaller tables remove it?",
    "Data Structures": "Which lookup pattern is on the hot path, and which structure gives you that cost?",
    "Distributed Systems": "Which anomaly appears if this transaction runs at read committed instead of repeatable read?",
    "Operating Systems": "Which resource is held while another is requested, and how does the cycle get broken?",
    "Python": "Which input breaks the current branch, and what should the function return in that case?",
    "FastAPI": "Which status code should the client see when validation fails, and where is that raised?",
    "API Design": "Which field is part of the contract, and which field should stay off the public response?",
    "Security Engineering": "Which value is untrusted here, and where should it be checked before it reaches the model or the query?",
    "System Design": "Which component becomes the bottleneck at 10x load, and what limit protects it?",
    "DevOps": "Which secret would leak if this file were committed, and where should it live instead?",
    "Frontend Engineering": "Which state is the source of truth after this click, and what should the board show if the request fails?",
}


class GeneratedItem(BaseModel):
    title: str = Field(min_length=3, max_length=160)
    description: str = Field(min_length=8, max_length=600)
    type: str = "TASK"
    story_points: int = Field(default=3, ge=1, le=13)
    skill_tag: str = Field(min_length=2, max_length=60)
    co_tag: str = Field(default="CO1", max_length=12)
    rubric_criteria: list[str] = Field(default_factory=list)
    prerequisite_index: int | None = None


class GeneratedPlan(BaseModel):
    title: str = Field(min_length=3, max_length=160)
    course_code: str = Field(min_length=2, max_length=16)
    co_po_tags: list[str] = Field(default_factory=list)
    items: list[GeneratedItem] = Field(min_length=4, max_length=16)


class JDPlan(BaseModel):
    role_title: str = Field(min_length=3, max_length=120)
    match_percent: int = Field(ge=0, le=100)
    matched_skills: list[str]
    missing_skills: list[str]
    summary: str = Field(min_length=8, max_length=500)
    prep_items: list[GeneratedItem] = Field(min_length=3, max_length=8)


def infer_skill(text: str) -> str:
    lowered = text.lower()
    for needle, skill in SKILL_RULES:
        if needle in lowered:
            return skill
    return "Software Engineering"


def default_rubric(skill: str) -> list[str]:
    return [
        f"{skill}: explains the concept in the student's own words",
        "Names at least one edge case or failure mode",
        "States a complexity, cost, or tradeoff",
        "Describes how errors are detected or handled",
    ]


def _clean_type(value: str) -> str:
    value = value.upper().strip()
    return value if value in {"EPIC", "TASK", "SUBTASK"} else "TASK"


def _normalize_items(items: list[GeneratedItem]) -> list[GeneratedItem]:
    cleaned: list[GeneratedItem] = []
    for index, item in enumerate(items[:16]):
        prereq = item.prerequisite_index
        if prereq is not None and (prereq < 0 or prereq >= index):
            prereq = index - 1 if index else None
        cleaned.append(
            item.model_copy(
                update={
                    "type": _clean_type(item.type),
                    "skill_tag": item.skill_tag.strip() or "Software Engineering",
                    "co_tag": item.co_tag if item.co_tag.startswith("CO") else f"CO{(index % 4) + 1}",
                    "rubric_criteria": (item.rubric_criteria or default_rubric(item.skill_tag))[:5],
                    "prerequisite_index": prereq,
                    "story_points": min(13, max(1, item.story_points)),
                }
            )
        )
    return cleaned


def fallback_sprint(title: str, course_code: str, syllabus: str, weeks: int) -> GeneratedPlan:
    lines = [line.strip(" -\t") for line in re.split(r"[\r\n]+", syllabus) if line.strip()]
    units: list[tuple[str, list[str]]] = []
    current_title = None
    bucket: list[str] = []
    unit_re = re.compile(r"^(unit|module|chapter|week)\s*\d*[:.\-\s]*", re.I)
    for line in lines:
        if unit_re.match(line) or (len(line) < 80 and line.endswith(":")):
            if current_title:
                units.append((current_title, bucket))
            current_title = unit_re.sub("", line).strip(" :.-") or line.strip(" :.-")
            bucket = []
        else:
            bucket.append(line)
    if current_title:
        units.append((current_title, bucket))
    if not units:
        chunks = lines or [syllabus.strip()]
        units = [("Core concepts", chunks[:6])]

    items: list[GeneratedItem] = []
    for unit_index, (unit_name, topics) in enumerate(units[:4]):
        epic_index = len(items)
        skill = infer_skill(unit_name + " " + " ".join(topics))
        items.append(
            GeneratedItem(
                title=unit_name[:140],
                description=f"Epic for {unit_name}. Finish the tasks under this unit before treating the outcome as mastered.",
                type="EPIC",
                story_points=8,
                skill_tag=skill,
                co_tag=f"CO{(unit_index % 4) + 1}",
                rubric_criteria=default_rubric(skill),
                prerequisite_index=None if unit_index == 0 else max(0, epic_index - 1),
            )
        )
        for topic in (topics or [f"Apply {unit_name}"])[:3]:
            topic_skill = infer_skill(topic)
            advanced = any(word in topic.lower() for word in ("optimi", "transaction", "deadlock", "distributed", "index", "security"))
            items.append(
                GeneratedItem(
                    title=topic[:140],
                    description=f"Work the concept '{topic}' with an edge case and a short justification. Duration target: {weeks} weeks for the sprint.",
                    type="SUBTASK" if len(topic) < 42 else "TASK",
                    story_points=5 if advanced else 3,
                    skill_tag=topic_skill,
                    co_tag=f"CO{(unit_index % 4) + 1}",
                    rubric_criteria=default_rubric(topic_skill),
                    prerequisite_index=epic_index if advanced else None,
                )
            )
        if len(items) >= 12:
            break
    while len(items) < 4:
        items.append(
            GeneratedItem(
                title=f"Guided practice {len(items) + 1}",
                description="Explain the idea, test one edge case, and record the tradeoff in your own words.",
                type="TASK",
                story_points=3,
                skill_tag=infer_skill(syllabus),
                co_tag="CO1",
                rubric_criteria=default_rubric(infer_skill(syllabus)),
                prerequisite_index=0 if items else None,
            )
        )
    code = re.sub(r"[^A-Z0-9]", "", course_code.upper())[:8] or "GEN101"
    return GeneratedPlan(
        title=title.strip(),
        course_code=code,
        co_po_tags=["CO1", "CO2", "CO3", "PO2", "PO3", "PO5"],
        items=_normalize_items(items[:12]),
    )


def wants_direct_solution(text: str) -> bool:
    return DIRECT_SOLUTION.search(text) is not None


def fallback_evaluation(submission: str, rubric: list[str], skill: str) -> EvaluationResult:
    if wants_direct_solution(submission):
        return EvaluationResult(
            refused_direct_solution=True,
            diagnosed_gap=f"The message asks for a finished {skill} answer instead of showing where the reasoning stopped.",
            guiding_question=GUIDES.get(skill, "What have you already tried, and which input makes that attempt fail?"),
            readiness_score=None,
            checks=[],
            actionable_fixes=["Restate the goal in one sentence", "Name the case you cannot yet handle"],
            remediation_title=f"15-min: isolate one {skill} gap before writing the final answer",
        )
    lowered = submission.lower()
    signals = {
        "edge": any(word in lowered for word in ("edge", "null", "empty", "boundary", "unmatched", "zero")),
        "cost": any(word in lowered for word in ("complex", "o(n", "o(1", "tradeoff", "index", "cost", "latency")),
        "errors": any(word in lowered for word in ("error", "exception", "rollback", "status", "invalid", "fail")),
        "reasoning": any(word in lowered for word in ("because", "therefore", "so that", "instead of", "trade-off", "tradeoff")),
    }
    score = 38 + min(12, len(submission) // 40)
    score += 14 if signals["edge"] else 0
    score += 14 if signals["cost"] else 0
    score += 12 if signals["errors"] else 0
    score += 10 if signals["reasoning"] else 0
    score = max(0, min(100, score))
    checks: list[RubricCheck] = []
    fixes: list[str] = []
    for criterion in rubric or default_rubric(skill):
        key = criterion.lower()
        if "edge" in key or "failure" in key:
            passed = signals["edge"]
        elif "complex" in key or "cost" in key or "trade" in key:
            passed = signals["cost"]
        elif "error" in key or "handled" in key:
            passed = signals["errors"]
        else:
            passed = signals["reasoning"] or len(submission) > 100
        note = "Present in the submission." if passed else "Not yet visible. Add this before faculty grading."
        checks.append(RubricCheck(criterion=criterion, passed=passed, note=note))
        if not passed:
            fixes.append(f"Add: {criterion}")
    gap = "The draft covers the happy path and still needs the failing case made explicit." if score < 80 else "The draft is close. Tighten the justification before mastery."
    question = GUIDES.get(skill, "Which assumption in this draft fails first?")
    return EvaluationResult(
        refused_direct_solution=False,
        diagnosed_gap=gap,
        guiding_question=question,
        readiness_score=score,
        checks=checks,
        actionable_fixes=fixes[:4],
        remediation_title=None,
    )


def fallback_jd(job_text: str, scores: dict[str, int]) -> JDPlan:
    lowered = job_text.lower()
    found = [skill for skill in JD_SKILLS if skill.lower() in lowered or any(part in lowered for part in skill.lower().split())]
    if "sde" in lowered or "backend" in lowered:
        for skill in ("Python", "SQL", "API Design", "System Design"):
            if skill not in found:
                found.append(skill)
    if "genai" in lowered or "llm" in lowered or "gemini" in lowered:
        for skill in ("Python", "FastAPI", "Security Engineering"):
            if skill not in found:
                found.append(skill)
    if not found:
        found = ["Python", "SQL", "Data Structures", "API Design"]
    matched = [skill for skill in found if scores.get(skill, 0) >= 70]
    missing = [skill for skill in found if scores.get(skill, 0) < 70]
    if not missing:
        missing = [skill for skill, score in sorted(scores.items(), key=lambda pair: pair[1]) if score < 80][:3]
    if not missing:
        missing = ["System Design"]
    weight = sum(min(100, scores.get(skill, 35)) for skill in found)
    match = round(weight / max(1, len(found)))
    role = "Target role"
    role_match = re.search(r"(genai engineer|sde[-\s]?1[^.\n]*|backend engineer[^.\n]*|software engineer[^.\n]*)", job_text, re.I)
    if role_match:
        role = role_match.group(1).strip()
    items = []
    for index, skill in enumerate(missing[:5]):
        day = index * 3 + 1
        items.append(
            GeneratedItem(
                title=f"Close the {skill} gap",
                description=f"Days {day}–{min(14, day + 2)}: one worked example, one edge case, and a short note you can defend in an interview.",
                type="TASK",
                story_points=3,
                skill_tag=skill,
                co_tag="PO5",
                rubric_criteria=default_rubric(skill),
                prerequisite_index=index - 1 if index else None,
            )
        )
    while len(items) < 3:
        items.append(
            GeneratedItem(
                title=f"Interview drill {len(items) + 1}",
                description="Explain a verified project decision out loud, including what you rejected.",
                type="TASK",
                story_points=2,
                skill_tag="System Design",
                co_tag="PO5",
                rubric_criteria=default_rubric("System Design"),
                prerequisite_index=None,
            )
        )
    summary = (
        f"{match}% overlap with the verified skill graph. "
        + (", ".join(matched) + " already have evidence." if matched else "No skill is at the verified bar yet.")
        + f" The prep sprint targets {', '.join(missing[:4])}."
    )
    return JDPlan(
        role_title=role[:120],
        match_percent=max(0, min(100, match)),
        matched_skills=matched,
        missing_skills=missing[:5],
        summary=summary,
        prep_items=_normalize_items(items),
    )


def _extract_json(text: str) -> dict:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?", "", cleaned, flags=re.I).strip()
        cleaned = re.sub(r"```$", "", cleaned).strip()
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start >= 0 and end > start:
        cleaned = cleaned[start : end + 1]
    payload = json.loads(cleaned)
    if not isinstance(payload, dict):
        raise ValueError("Model JSON must be an object")
    return payload


MODEL_COOLDOWN_SECONDS = 300
_model_resting_until: dict[str, float] = {}


def _models_to_try() -> list[str]:
    settings = get_settings()
    now = time.monotonic()
    chain = [name for name in dict.fromkeys([settings.gemini_model, settings.gemini_fallback_model]) if name.strip()]
    awake = [name for name in chain if _model_resting_until.get(name, 0) <= now]
    return awake or chain[-1:]


def _ask_model(model: str, body: dict, timeout: float) -> dict | None:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    headers = {"x-goog-api-key": get_settings().gemini_api_key.strip()}
    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.post(url, json=body, headers=headers)
    except httpx.HTTPError:
        _model_resting_until[model] = time.monotonic() + MODEL_COOLDOWN_SECONDS
        return None
    if response.status_code in {404, 429, 500, 502, 503, 504}:
        _model_resting_until[model] = time.monotonic() + MODEL_COOLDOWN_SECONDS
        return None
    if response.status_code >= 400:
        return None
    try:
        data = response.json()
        return _extract_json(data["candidates"][0]["content"]["parts"][0]["text"])
    except (KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError):
        return None


def _gemini_json(prompt: str, timeout: float = 25) -> dict | None:
    if not get_settings().gemini_api_key.strip():
        return None
    body = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.2,
            "responseMimeType": "application/json",
            "maxOutputTokens": 4096,
        },
    }
    for model in _models_to_try():
        payload = _ask_model(model, body, timeout)
        if payload is not None:
            return payload
    return None


def complete_json(task: str, guarded: GuardedText, schema_hint: str, model: type[T]) -> tuple[T | None, str]:
    settings = get_settings()
    if not settings.gemini_api_key.strip():
        return None, "deterministic-fallback"
    prompt = build_model_prompt(task, guarded, schema_hint)
    last_error = "invalid"
    for _ in range(2):
        payload = _gemini_json(prompt if last_error == "invalid" else prompt + f"\nPrevious output failed validation: {last_error}. Return corrected JSON only.")
        if payload is None:
            return None, "deterministic-fallback"
        try:
            return model.model_validate(payload), "gemini"
        except ValidationError as exc:
            last_error = exc.errors()[0]["msg"] if exc.errors() else "schema"
    return None, "deterministic-fallback"


SPRINT_HINT = (
    '{"title":"str","course_code":"str","co_po_tags":["CO1"],'
    '"items":[{"title":"str","description":"str","type":"EPIC|TASK|SUBTASK","story_points":3,'
    '"skill_tag":"str","co_tag":"CO1","rubric_criteria":["str"],"prerequisite_index":null}]}'
)

EVAL_HINT = (
    '{"refused_direct_solution":false,"diagnosed_gap":"str","guiding_question":"str",'
    '"readiness_score":70,"checks":[{"criterion":"str","passed":true,"note":"str"}],'
    '"actionable_fixes":["str"],"remediation_title":null}'
)

JD_HINT = (
    '{"role_title":"str","match_percent":60,"matched_skills":["SQL"],"missing_skills":["System Design"],'
    '"summary":"str","prep_items":[{"title":"str","description":"str","type":"TASK","story_points":3,'
    '"skill_tag":"str","co_tag":"PO5","rubric_criteria":["str"],"prerequisite_index":null}]}'
)


def plan_sprint(title: str, course_code: str, syllabus: str, weeks: int) -> tuple[GeneratedPlan, GuardedText]:
    guarded = guard_untrusted(syllabus, "deterministic-fallback")
    model, transport = complete_json(
        f"Decompose this syllabus into 6 to 12 learning work items for a {weeks}-week sprint titled '{title}'. "
        "Course code should stay close to "
        f"{course_code}. Chain prerequisite_index only to an earlier item. Never include identifiers from the submission.",
        guarded,
        SPRINT_HINT,
        GeneratedPlan,
    )
    if model is None:
        model = fallback_sprint(title, course_code, guarded.redacted, weeks)
        transport = "deterministic-fallback"
    else:
        code = re.sub(r"[^A-Z0-9]", "", (model.course_code or course_code).upper())[:8] or "GEN101"
        model = model.model_copy(update={"course_code": code, "items": _normalize_items(model.items)})
    guarded.meta.transport = transport
    guarded.meta.schema_valid = True
    return model, guarded


def plan_evaluation(submission: str, rubric: list[str], skill: str, ticket: str) -> tuple[EvaluationResult, GuardedText]:
    guarded = guard_untrusted(submission, "deterministic-fallback")
    # Direct-solution requests are refused before the model can comply.
    if wants_direct_solution(submission):
        result = fallback_evaluation(submission, rubric, skill)
        guarded.meta.transport = "deterministic-fallback"
        return result, guarded
    model, transport = complete_json(
        f"Evaluate ticket {ticket} for skill {skill}. Rubric: {json.dumps(rubric)}. "
        "If the submission asks for a finished answer, set refused_direct_solution true and readiness_score null. "
        "Otherwise score 0-100 and mark each rubric check. Do not write a full solution.",
        guarded,
        EVAL_HINT,
        EvaluationResult,
    )
    if model is None or (model.refused_direct_solution is False and model.readiness_score is None):
        model = fallback_evaluation(guarded.redacted, rubric, skill)
        transport = "deterministic-fallback"
    if model.refused_direct_solution:
        model = model.model_copy(update={"readiness_score": None, "remediation_title": model.remediation_title or f"15-min: isolate one {skill} gap"})
    guarded.meta.transport = transport
    return model, guarded


def looks_like_full_solution(text: str) -> bool:
    if "```" in text or text.count("\n") > 8:
        return True
    return bool(re.search(r"\b(def |class |SELECT |function |import )", text))


def plan_unblock(message: str, skill: str, ticket: str) -> tuple[EvaluationResult, GuardedText]:
    guarded = guard_untrusted(message, "deterministic-fallback")
    if wants_direct_solution(message):
        result = fallback_evaluation(message, [], skill)
        return result, guarded
    model, transport = complete_json(
        f"The student is stuck on {ticket} ({skill}). "
        "Reply with a diagnosed_gap and one guiding_question. "
        "Set refused_direct_solution false, readiness_score null, checks empty, remediation_title null. "
        "Do not include code, SQL, or a finished answer.",
        guarded,
        EVAL_HINT,
        EvaluationResult,
    )
    guide = GUIDES.get(skill, "What did you expect to happen, and which input first breaks that expectation?")
    unsafe = model is None or looks_like_full_solution(model.guiding_question) or looks_like_full_solution(model.diagnosed_gap)
    if unsafe:
        model = EvaluationResult(
            refused_direct_solution=False,
            diagnosed_gap=f"{ticket} is still open on {skill}. Stay with the smallest case you can check by hand.",
            guiding_question=guide,
            readiness_score=None,
            checks=[],
            actionable_fixes=[
                "Name the input you are stuck on",
                "Write the result you expected beside the result you got",
            ],
            remediation_title=None,
        )
        transport = "deterministic-fallback"
    else:
        model = model.model_copy(update={"readiness_score": None, "remediation_title": None, "checks": []})
    guarded.meta.transport = transport
    return model, guarded


def plan_jd(job_text: str, scores: dict[str, int]) -> tuple[JDPlan, GuardedText]:
    guarded = guard_untrusted(job_text, "deterministic-fallback")
    model, transport = complete_json(
        "Compare this job description with the verified scores "
        f"{json.dumps(scores)}. Return match percent, matched skills at 70 or above, missing skills, "
        "and 3 to 5 prep tasks. Do not invent employment guarantees.",
        guarded,
        JD_HINT,
        JDPlan,
    )
    if model is None:
        model = fallback_jd(guarded.redacted, scores)
        transport = "deterministic-fallback"
    else:
        model = model.model_copy(update={"prep_items": _normalize_items(model.prep_items), "match_percent": max(0, min(100, model.match_percent))})
    guarded.meta.transport = transport
    return model, guarded
