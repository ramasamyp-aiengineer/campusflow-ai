# CampusFlow AI — agent and maintainer map

## Layered layout

```
backend/app/
  routers/     # HTTP adapters only (auth, api, signals)
  services/    # business decisions: board, blocker, ai, signals, story_actions, golden, runtime
  services/builtin_feeds.py  # sample RSS fixtures (kept out of signals.py)
  security/    # auth sessions, PII, prompt pipeline
  models.py    # SQLAlchemy tables
  schemas.py   # request/response contracts
  config.py    # env-backed settings
frontend/
  components/  # persona views and board widgets
  lib/         # api client, session, types, format helpers
```

## Quality bar

- Prefer small functions with one job. Shared cohort math lives in `board.load_cohort` / `blocked_core_counts`.
- Public helpers are named without a leading underscore (`cluster_for`, not `_cluster_for`).
- AI route failures log with `logger.exception` and fall back to the deterministic engine.
- Lint/format: `ruff check` + `ruff format --check` in `backend/`; `npm run lint` + `npm run format:check` in `frontend/`.
- Tests: `pytest -q` (backend) and `npm run test:ci` (frontend).
- Dependencies are pinned in `requirements*.txt` and `frontend/package.json`.

## Do not regress

- Faculty co-sign is the only path that writes mastery onto the skill graph.
- Sample RSS cards stay labeled; production refuses `*-latest` model aliases and the default `APP_SECRET`.
