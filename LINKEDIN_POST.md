# LinkedIn post — copy and publish

Visibility: **Anyone** · Tag the company pages while composing (type `@AI Geeks Chennai` and `@Hack2skill`).

---

Built CampusFlow AI for Prompt War 2026 — Theme 2: AI for Education.

The problem
Campus work is still scattered across PDF syllabi, WhatsApp deadlines, and CGPA shortlists. Generic chatbots hand out finished answers. Faculty see struggle only after midterms. Placement and curriculum lag what industry is hiring for.

The solution — one closed loop
Syllabus → agile learning tickets → Socratic Gemini tutor → AI review → faculty co-sign mastery → evidence on the skill graph → placement JD prep → industry RSS signals feeding labs, quizzes, sentiment, topics, and curriculum drift.

Main classroom workflow
1. Paste a syllabus → Gemini builds EPIC / TASK / SUBTASK tickets with story points, CO/PO tags, rubrics, and prerequisites
2. Move work on a Kanban board: BACKLOG → IN_PROGRESS → AI_REVIEW → MASTERED
3. Stuck? Socratic unblocker returns a diagnosed gap + one guiding question — never the finished answer
4. Submit a draft → rubric auditor scores readiness (pass ≥ 75)
5. Faculty co-sign the AI-reviewed ticket → mastery is recorded on the skill graph (students cannot self-master)
6. Placement Cell filters by evidence-backed skills and can turn a JD into a 14-day PLACE-1xx prep sprint

RSS + analytics workflow (My interests)
1. Subscribe to Google News / industry RSS, or one-click sample interests (ML, Placements, Databases…)
2. SSRF-safe ingest — public http(s) only, size-capped, no localhost / metadata hosts
3. Relevance filter against the student’s skill graph and open tickets (campus noise stays low)
4. Story fusion — same headline across feeds becomes one card with real outlet links + “Reported by N sources”
5. Explainable badges — matches active ticket, closes a skill gap, placement prep weight
6. Act on a story → Turn into LAB-1xx micro-lab on the sprint board · or Explain & quiz me (+2 XP on first correct, no farming)
7. Interest analytics per feed:
   • Stories tab
   • Sentiment analysis — Positive / Watchful / Critical / Neutral with donut + sortable table
   • Topic clustering — keyword clusters of what that interest is actually talking about
8. Faculty / Placement Curriculum Drift Radar — trending skills as In syllabus vs Not in syllabus, workshop suggestions, critical hiring alerts when negative placement news spikes — no student names exposed
9. Feeds re-poll every 8 hours (manual refresh respects Retry-After)

Also shipped for trust
Session auth · RBAC · PII redaction · prompt-injection guards · pinned Gemini models · golden-set fallback accuracy on /health · rate limits · production boot guards

Stack: Next.js 15 · FastAPI · SQLAlchemy · Google Gemini · Cloud Run · Vercel

Live demo: https://campusflow-ai-five.vercel.app  
Judge path: Arjun → My interests (Stories / Sentiment / Topics) → Explain & quiz or Turn into lab → Faculty / Placement in the top bar

GitHub: https://github.com/ramasamyp-aiengineer/campusflow-ai

Grateful to AI Geeks Chennai and the Hack2skill team for Prompt War 2026.

#PromptWar #PromptWars2026 #AIGeeksChennai #Hack2skill #AIforEducation #BuildWithAI #Gemini #RSS #SentimentAnalysis #TopicClustering #Nextjs #FastAPI

---

After posting, paste your LinkedIn URL here for your own records:

- LinkedIn post URL:
