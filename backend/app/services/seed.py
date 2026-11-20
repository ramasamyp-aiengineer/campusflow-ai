import json

from sqlalchemy.orm import Session

from app.models import LearningWorkItem, SkillNode, Sprint, User
from app.services.board import evidence_hash


def _skill(db: Session, student_id: int, name: str, score: int, tickets: list[str]) -> None:
    db.add(
        SkillNode(
            student_id=student_id,
            skill_name=name,
            proficiency_score=score,
            verified_lwi_count=len(tickets),
            evidence_tickets=json.dumps(tickets),
            evidence_hash=evidence_hash(student_id, name, tickets) if tickets else "",
            last_updated="2026-11-16T09:00:00+00:00",
        )
    )


def _pass_feedback(skill: str, score: int = 82) -> str:
    return json.dumps(
        {
            "refused_direct_solution": False,
            "diagnosed_gap": f"Seeded review for {skill}.",
            "guiding_question": "Which edge case still needs a check?",
            "readiness_score": score,
            "checks": [],
            "actionable_fixes": [],
            "remediation_title": None,
        }
    )


def _lwi(db: Session, **kwargs) -> LearningWorkItem:
    rubric = kwargs.pop("rubric")
    item = LearningWorkItem(rubric_criteria=json.dumps(rubric), **kwargs)
    db.add(item)
    db.flush()
    return item


SQL_RUBRIC = [
    "Chooses the join that preserves the rows the question asks for",
    "Names an edge case such as NULL or unmatched rows",
    "States the cost of a nested-loop join versus a hash join",
    "Describes what the query should do on invalid input",
]

RA_RUBRIC = [
    "Identifies the dependency or relational rule in play",
    "Shows a case that violates the current shape",
    "Explains the tradeoff of splitting or keeping the table",
    "Checks the result against a small hand-computed example",
]

DS_RUBRIC = [
    "Names the structure and the operation it optimizes",
    "Covers an empty or single-node edge case",
    "States the lookup or insert cost",
    "Explains what happens when the structure is full or unbalanced",
]

DIST_RUBRIC = [
    "Names the isolation level",
    "Identifies the anomaly that level still allows",
    "Describes rollback or retry when the transaction aborts",
    "Justifies the choice against a weaker level",
]

OS_RUBRIC = [
    "Names the resource and the waiting condition",
    "Shows a schedule that deadlocks or misses the deadline",
    "States the cost of the chosen policy",
    "Explains recovery after preemption or abort",
]


def seed_if_empty(db: Session) -> None:
    if db.query(User).first():
        return

    arjun = User(
        name="Arjun K.",
        role="STUDENT",
        department="CSE",
        semester=5,
        avatar_initials="AK",
        anon_token="STU_8921",
        cgpa=8.2,
        velocity_drop_pct=12,
        is_persona=True,
        program="B.Tech CSE",
    )
    faculty = User(
        name="Dr. Meenakshi",
        role="FACULTY",
        department="CSE",
        semester=0,
        avatar_initials="DM",
        anon_token="FAC_1044",
        cgpa=0,
        velocity_drop_pct=0,
        is_persona=True,
        program="DBMS & Cloud",
    )
    tpo = User(
        name="Placement Cell",
        role="TPO",
        department="Training & Placement",
        semester=0,
        avatar_initials="TP",
        anon_token="TPO_017",
        cgpa=0,
        velocity_drop_pct=0,
        is_persona=True,
        program="Recruiter Readiness",
    )
    priya = User(
        name="Priya Nair",
        role="STUDENT",
        department="CSE",
        semester=5,
        avatar_initials="PN",
        anon_token="STU_7740",
        cgpa=7.4,
        velocity_drop_pct=48,
        is_persona=False,
        program="B.Tech CSE",
    )
    rohan = User(
        name="Rohan Mehta",
        role="STUDENT",
        department="CSE",
        semester=5,
        avatar_initials="RM",
        anon_token="STU_6612",
        cgpa=9.4,
        velocity_drop_pct=6,
        is_persona=False,
        program="B.Tech CSE",
    )
    sneha = User(
        name="Sneha Iyer",
        role="STUDENT",
        department="CSE",
        semester=5,
        avatar_initials="SI",
        anon_token="STU_8801",
        cgpa=7.1,
        velocity_drop_pct=9,
        is_persona=False,
        program="B.Tech CSE",
    )
    vikram = User(
        name="Vikram Singh",
        role="STUDENT",
        department="CSE",
        semester=5,
        avatar_initials="VS",
        anon_token="STU_5408",
        cgpa=6.8,
        velocity_drop_pct=41,
        is_persona=False,
        program="B.Tech CSE",
    )
    ananya = User(
        name="Ananya Rao",
        role="STUDENT",
        department="CSE",
        semester=5,
        avatar_initials="AR",
        anon_token="STU_9033",
        cgpa=8.0,
        velocity_drop_pct=14,
        is_persona=False,
        program="B.Tech CSE",
    )
    db.add_all([arjun, faculty, tpo, priya, rohan, sneha, vikram, ananya])
    db.flush()

    dbms = Sprint(
        title="Relational Model to Transactions",
        course_code="CS301",
        start_date="2026-11-03",
        end_date="2026-11-28",
        co_po_tags=json.dumps(["CO1", "CO2", "CO3", "CO4", "PO2", "PO3", "PO5"]),
        owner_student_id=None,
        kind="COURSE",
    )
    os_sprint = Sprint(
        title="Processes, Scheduling, and Deadlock",
        course_code="CS302",
        start_date="2026-11-03",
        end_date="2026-12-05",
        co_po_tags=json.dumps(["CO1", "CO2", "CO3", "PO3", "PO4"]),
        owner_student_id=None,
        kind="COURSE",
    )
    capstone = Sprint(
        title="Full-Stack Capstone: Campus API",
        course_code="CS401",
        start_date="2026-10-20",
        end_date="2026-12-12",
        co_po_tags=json.dumps(["CO1", "CO2", "CO5", "PO5", "PO8"]),
        owner_student_id=None,
        kind="COURSE",
    )
    db.add_all([dbms, os_sprint, capstone])
    db.flush()

    epic = _lwi(
        db,
        sprint_id=dbms.id,
        student_id=arjun.id,
        ticket_code="CS301-101",
        title="Relational data model",
        description="Map the course unit to the structures a DBMS actually stores: relations, keys, and integrity.",
        type="EPIC",
        status="MASTERED",
        story_points=8,
        skill_tag="Relational Algebra",
        prerequisite_id=None,
        co_tag="CO1",
        rubric=RA_RUBRIC,
    )
    er = _lwi(
        db,
        sprint_id=dbms.id,
        student_id=arjun.id,
        ticket_code="CS301-102",
        title="ER to relational mapping",
        description="Convert the campus schema ER diagram into tables without losing cardinality.",
        type="TASK",
        status="MASTERED",
        story_points=5,
        skill_tag="SQL",
        prerequisite_id=epic.id,
        co_tag="CO1",
        rubric=SQL_RUBRIC,
    )
    fd = _lwi(
        db,
        sprint_id=dbms.id,
        student_id=arjun.id,
        ticket_code="CS301-103",
        title="Functional dependencies",
        description="List the dependencies hidden in the enrollment table and show one redundancy they create.",
        type="SUBTASK",
        status="MASTERED",
        story_points=3,
        skill_tag="Relational Algebra",
        prerequisite_id=er.id,
        co_tag="CO1",
        rubric=RA_RUBRIC,
    )
    joins = _lwi(
        db,
        sprint_id=dbms.id,
        student_id=arjun.id,
        ticket_code="CS301-104",
        title="SQL joins lab",
        description="Write the enrollment report and decide which students must remain when a match is missing.",
        type="TASK",
        status="IN_PROGRESS",
        story_points=5,
        skill_tag="SQL",
        prerequisite_id=fd.id,
        co_tag="CO2",
        rubric=SQL_RUBRIC,
    )
    _lwi(
        db,
        sprint_id=dbms.id,
        student_id=arjun.id,
        ticket_code="CS301-105",
        title="Inner versus outer joins",
        description="Hand-check one unmatched faculty row and one unmatched student row before choosing the join.",
        type="SUBTASK",
        status="IN_PROGRESS",
        story_points=2,
        skill_tag="SQL",
        prerequisite_id=fd.id,
        co_tag="CO2",
        rubric=SQL_RUBRIC,
    )
    optimize = _lwi(
        db,
        sprint_id=dbms.id,
        student_id=arjun.id,
        ticket_code="CS301-106",
        title="Query optimization",
        description="Explain why the enrollment report picks a hash join, and which predicate can use an index.",
        type="TASK",
        status="BACKLOG",
        story_points=8,
        skill_tag="SQL",
        prerequisite_id=joins.id,
        co_tag="CO3",
        rubric=SQL_RUBRIC,
    )
    _lwi(
        db,
        sprint_id=dbms.id,
        student_id=arjun.id,
        ticket_code="CS301-107",
        title="Index selection",
        description="Choose an index for the filter the optimizer cannot push down. Blocked until optimization is mastered.",
        type="SUBTASK",
        status="BACKLOG",
        story_points=3,
        skill_tag="Data Structures",
        prerequisite_id=optimize.id,
        co_tag="CO3",
        rubric=DS_RUBRIC,
    )
    _lwi(
        db,
        sprint_id=dbms.id,
        student_id=arjun.id,
        ticket_code="CS301-108",
        title="Transaction isolation lab",
        description="Show a dirty read on the fee-payment table and the isolation level that removes it.",
        type="TASK",
        status="AI_REVIEW",
        story_points=5,
        skill_tag="Distributed Systems",
        prerequisite_id=fd.id,
        co_tag="CO4",
        rubric=DIST_RUBRIC,
        ai_feedback_json=_pass_feedback("Distributed Systems"),
    )
    _lwi(
        db,
        sprint_id=dbms.id,
        student_id=arjun.id,
        ticket_code="CS301-109",
        title="Normalization workshop",
        description="Take the wide student-profile sheet to a higher normal form and name the dependency you removed.",
        type="TASK",
        status="BACKLOG",
        story_points=5,
        skill_tag="Relational Algebra",
        prerequisite_id=fd.id,
        co_tag="CO1",
        rubric=RA_RUBRIC,
    )
    _lwi(
        db,
        sprint_id=dbms.id,
        student_id=arjun.id,
        ticket_code="CS301-110",
        title="Storage and indexing",
        description="Unit epic for how pages, indexes, and buffers change query cost.",
        type="EPIC",
        status="IN_PROGRESS",
        story_points=8,
        skill_tag="Data Structures",
        prerequisite_id=epic.id,
        co_tag="CO3",
        rubric=DS_RUBRIC,
    )
    _lwi(
        db,
        sprint_id=dbms.id,
        student_id=arjun.id,
        ticket_code="CS301-111",
        title="B+ tree walkthrough",
        description="Insert eight keys into a small B+ tree and state the cost of a range scan.",
        type="SUBTASK",
        status="AI_REVIEW",
        story_points=3,
        skill_tag="Data Structures",
        prerequisite_id=epic.id,
        co_tag="CO3",
        rubric=DS_RUBRIC,
        ai_feedback_json=_pass_feedback("Data Structures"),
    )
    _lwi(
        db,
        sprint_id=dbms.id,
        student_id=arjun.id,
        ticket_code="CS301-112",
        title="Schema design note",
        description="One-page justification of the campus schema a placement reviewer could follow.",
        type="TASK",
        status="BACKLOG",
        story_points=3,
        skill_tag="SQL",
        prerequisite_id=er.id,
        co_tag="CO2",
        rubric=SQL_RUBRIC,
    )

    process = _lwi(
        db,
        sprint_id=os_sprint.id,
        student_id=arjun.id,
        ticket_code="CS302-201",
        title="Process lifecycle",
        description="Trace a process from new to terminated and name the state where it waits for I/O.",
        type="EPIC",
        status="MASTERED",
        story_points=5,
        skill_tag="Operating Systems",
        prerequisite_id=None,
        co_tag="CO1",
        rubric=OS_RUBRIC,
    )
    _lwi(
        db,
        sprint_id=os_sprint.id,
        student_id=arjun.id,
        ticket_code="CS302-202",
        title="CPU scheduling lab",
        description="Compare FCFS and round robin on a short ready queue and report average waiting time.",
        type="TASK",
        status="IN_PROGRESS",
        story_points=5,
        skill_tag="Operating Systems",
        prerequisite_id=process.id,
        co_tag="CO2",
        rubric=OS_RUBRIC,
    )
    _lwi(
        db,
        sprint_id=os_sprint.id,
        student_id=arjun.id,
        ticket_code="CS302-203",
        title="Deadlock detection",
        description="Build a resource-allocation graph that contains a cycle and show one safe recovery.",
        type="TASK",
        status="BACKLOG",
        story_points=5,
        skill_tag="Operating Systems",
        prerequisite_id=process.id,
        co_tag="CO3",
        rubric=OS_RUBRIC,
    )
    _lwi(
        db,
        sprint_id=capstone.id,
        student_id=arjun.id,
        ticket_code="CS401-301",
        title="Campus API design",
        description="Define the resource boundaries for sprints, tickets, and skill evidence.",
        type="EPIC",
        status="IN_PROGRESS",
        story_points=8,
        skill_tag="API Design",
        prerequisite_id=None,
        co_tag="CO1",
        rubric=[
            "Names the resource and the client that needs it",
            "Lists one error status the API must return",
            "States what is intentionally left out of the payload",
            "Connects the endpoint to a course outcome",
        ],
    )
    _lwi(
        db,
        sprint_id=capstone.id,
        student_id=arjun.id,
        ticket_code="CS401-302",
        title="Role boundaries",
        description="Specify which role may read cohort risk and which role may submit work.",
        type="TASK",
        status="BACKLOG",
        story_points=5,
        skill_tag="Security Engineering",
        prerequisite_id=None,
        co_tag="CO2",
        rubric=[
            "Lists the three roles and one denied action each",
            "Identifies an untrusted input",
            "States how a secret stays out of the repository",
            "Describes the failure the user should see on a denied call",
        ],
    )
    _lwi(
        db,
        sprint_id=capstone.id,
        student_id=arjun.id,
        ticket_code="CS401-303",
        title="Skill evidence sync",
        description="Show how a mastered ticket becomes a skill-graph update a recruiter can trace.",
        type="TASK",
        status="MASTERED",
        story_points=5,
        skill_tag="Python",
        prerequisite_id=None,
        co_tag="CO5",
        rubric=[
            "Names the ticket that backs the skill",
            "Explains why CGPA is not the evidence",
            "Describes an update that should not count as verified",
            "States where the evidence fingerprint is stored",
        ],
    )
    _lwi(
        db,
        sprint_id=capstone.id,
        student_id=arjun.id,
        ticket_code="CS401-304",
        title="PII redaction check",
        description="Pass a fixture containing a phone, email, and roll number and confirm the model payload is clean.",
        type="SUBTASK",
        status="AI_REVIEW",
        story_points=3,
        skill_tag="Security Engineering",
        prerequisite_id=None,
        co_tag="CO2",
        rubric=[
            "Lists the identifier types that must be stripped",
            "Shows the redacted form, not the original value",
            "Explains where the map stays if a reversal is required",
            "Names the test that would catch a regression",
        ],
        ai_feedback_json=_pass_feedback("Security Engineering"),
    )

    basics = _lwi(
        db,
        sprint_id=dbms.id,
        student_id=priya.id,
        ticket_code="CS301-201",
        title="Relation basics retry",
        description="Priya still needs a clean definition of a key before joins are useful.",
        type="TASK",
        status="BACKLOG",
        story_points=3,
        skill_tag="SQL",
        prerequisite_id=None,
        co_tag="CO1",
        rubric=SQL_RUBRIC,
    )
    priya_joins = _lwi(
        db,
        sprint_id=dbms.id,
        student_id=priya.id,
        ticket_code="CS301-202",
        title="Joins retry",
        description="Blocked until relation basics are mastered.",
        type="TASK",
        status="BACKLOG",
        story_points=5,
        skill_tag="SQL",
        prerequisite_id=basics.id,
        co_tag="CO2",
        rubric=SQL_RUBRIC,
    )
    _lwi(
        db,
        sprint_id=dbms.id,
        student_id=priya.id,
        ticket_code="CS301-203",
        title="Optimization retry",
        description="Blocked on the joins retry.",
        type="TASK",
        status="BACKLOG",
        story_points=5,
        skill_tag="SQL",
        prerequisite_id=priya_joins.id,
        co_tag="CO3",
        rubric=SQL_RUBRIC,
    )
    _lwi(
        db,
        sprint_id=dbms.id,
        student_id=priya.id,
        ticket_code="CS301-204",
        title="Isolation retry",
        description="Blocked until relation basics are mastered.",
        type="TASK",
        status="BACKLOG",
        story_points=5,
        skill_tag="Distributed Systems",
        prerequisite_id=basics.id,
        co_tag="CO4",
        rubric=DIST_RUBRIC,
    )

    v_process = _lwi(
        db,
        sprint_id=os_sprint.id,
        student_id=vikram.id,
        ticket_code="CS302-211",
        title="Process model retry",
        description="Vikram has not closed the process-state epic.",
        type="EPIC",
        status="BACKLOG",
        story_points=5,
        skill_tag="Operating Systems",
        prerequisite_id=None,
        co_tag="CO1",
        rubric=OS_RUBRIC,
    )
    v_sched = _lwi(
        db,
        sprint_id=os_sprint.id,
        student_id=vikram.id,
        ticket_code="CS302-212",
        title="Scheduling retry",
        description="Blocked until the process model is mastered.",
        type="TASK",
        status="BACKLOG",
        story_points=5,
        skill_tag="Operating Systems",
        prerequisite_id=v_process.id,
        co_tag="CO2",
        rubric=OS_RUBRIC,
    )
    _lwi(
        db,
        sprint_id=os_sprint.id,
        student_id=vikram.id,
        ticket_code="CS302-213",
        title="Deadlock retry",
        description="Blocked until scheduling is mastered.",
        type="TASK",
        status="BACKLOG",
        story_points=5,
        skill_tag="Operating Systems",
        prerequisite_id=v_sched.id,
        co_tag="CO3",
        rubric=OS_RUBRIC,
    )
    _lwi(
        db,
        sprint_id=os_sprint.id,
        student_id=vikram.id,
        ticket_code="CS302-214",
        title="Memory retry",
        description="Blocked until the process model is mastered.",
        type="TASK",
        status="BACKLOG",
        story_points=3,
        skill_tag="Operating Systems",
        prerequisite_id=v_process.id,
        co_tag="CO2",
        rubric=OS_RUBRIC,
    )

    _lwi(
        db,
        sprint_id=dbms.id,
        student_id=rohan.id,
        ticket_code="CS301-301",
        title="Read the ER notes",
        description="A shallow pass that was marked complete without a rubric defense.",
        type="TASK",
        status="MASTERED",
        story_points=2,
        skill_tag="SQL",
        prerequisite_id=None,
        co_tag="CO1",
        rubric=SQL_RUBRIC,
    )
    _lwi(
        db,
        sprint_id=dbms.id,
        student_id=sneha.id,
        ticket_code="CS301-401",
        title="Join correctness drill",
        description="Sneha defended an outer join with an unmatched row and a cost note.",
        type="TASK",
        status="MASTERED",
        story_points=5,
        skill_tag="SQL",
        prerequisite_id=None,
        co_tag="CO2",
        rubric=SQL_RUBRIC,
    )
    ananya_open = _lwi(
        db,
        sprint_id=dbms.id,
        student_id=ananya.id,
        ticket_code="CS301-501",
        title="Keys and constraints",
        description="Ananya is steady. One index task is waiting on this key check.",
        type="TASK",
        status="IN_PROGRESS",
        story_points=3,
        skill_tag="SQL",
        prerequisite_id=None,
        co_tag="CO1",
        rubric=SQL_RUBRIC,
    )
    _lwi(
        db,
        sprint_id=dbms.id,
        student_id=ananya.id,
        ticket_code="CS301-502",
        title="Secondary index note",
        description="Blocked until keys and constraints are mastered.",
        type="TASK",
        status="BACKLOG",
        story_points=3,
        skill_tag="Data Structures",
        prerequisite_id=ananya_open.id,
        co_tag="CO3",
        rubric=DS_RUBRIC,
    )

    for student_id, rows in {
        arjun.id: [
            ("SQL", 84, ["CS301-102"]),
            ("Relational Algebra", 88, ["CS301-101", "CS301-103"]),
            ("Data Structures", 70, []),
            ("Distributed Systems", 62, []),
            ("Python", 76, ["CS401-303"]),
            ("FastAPI", 58, []),
            ("Operating Systems", 64, ["CS302-201"]),
            ("API Design", 60, []),
        ],
        priya.id: [
            ("SQL", 44, []),
            ("Relational Algebra", 41, []),
            ("Distributed Systems", 36, []),
            ("Python", 55, []),
            ("Operating Systems", 48, []),
        ],
        rohan.id: [
            ("SQL", 48, ["CS301-301"]),
            ("Python", 52, []),
            ("Data Structures", 40, []),
            ("Operating Systems", 44, []),
            ("API Design", 46, []),
        ],
        sneha.id: [
            ("Python", 86, ["CS301-401"]),
            ("SQL", 80, ["CS301-401"]),
            ("Data Structures", 78, ["CS301-401"]),
            ("FastAPI", 74, ["CS301-401"]),
            ("API Design", 77, ["CS301-401"]),
        ],
        vikram.id: [
            ("Operating Systems", 38, []),
            ("SQL", 42, []),
            ("Python", 47, []),
            ("Data Structures", 35, []),
        ],
        ananya.id: [
            ("SQL", 72, []),
            ("Data Structures", 66, []),
            ("Python", 71, []),
            ("Operating Systems", 69, []),
            ("API Design", 68, []),
        ],
    }.items():
        for name, score, tickets in rows:
            _skill(db, student_id, name, score, tickets)
