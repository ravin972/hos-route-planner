# Spotter HOS Planner

A trip planner and FMCSA-style driver-log generator for the Spotter full-stack assessment.
Enter a current location, a pickup, a drop-off and the hours already used on the 70-hour cycle; get a
route map with stops, daily 24-hour log sheets and daily summaries.

> **Status — Phase 0 (development foundation).** The project skeleton, tooling and tests are in place.
> **No planner, routing or UI features exist yet.** See [`docs/implementation-plan.md`](docs/implementation-plan.md).

| Layer | Stack |
| --- | --- |
| Backend | Python 3.12 · Django 5.2 LTS · Django REST Framework · stateless, no database |
| Frontend | React 19 · TypeScript · Vite · Tailwind CSS v4 |
| Tests | pytest · Vitest + Testing Library |

## Repository layout

```text
backend/    Django project (config/) and the trips app: api/, hos/ (pure Python), routing/, tests/
frontend/   Vite + React + TypeScript app
docs/       hos-rules.md (rules spec) · architecture.md · implementation-plan.md
CLAUDE.md   Working rules for AI-assisted development
```

## Prerequisites

- **Python 3.12** — not 3.14. On Windows the `py` launcher defaults to 3.14, so always ask for 3.12: `py -3.12`.
- **Node.js 22** and npm 11.

## Run it locally

Backend (PowerShell, from `backend\`):

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
$env:DJANGO_DEBUG = "true"        # local development only; see Configuration
python manage.py runserver        # http://127.0.0.1:8000/api/health
```

Frontend (from `frontend\`):

```powershell
npm install
npm run dev                       # http://localhost:5173 — proxies /api to the backend
```

## Test and check

```powershell
# backend (virtual environment active)
pytest ; ruff check . ; ruff format --check . ; mypy

# frontend
npm run lint ; npm run typecheck ; npm test ; npm run format:check ; npm run build
```

## Configuration

Everything is a **real environment variable**. Nothing loads a `.env` file and no secret is ever committed;
`backend/.env.example` and `frontend/.env.example` only list the names.

| Variable | Purpose | Default |
| --- | --- | --- |
| `DJANGO_SECRET_KEY` | Django secret key | required unless `DJANGO_DEBUG=true` |
| `DJANGO_DEBUG` | development mode | `false` |
| `DJANGO_ALLOWED_HOSTS` | comma-separated host allow-list | `localhost,127.0.0.1` |
| `VITE_API_BASE_URL` | API origin used by the frontend | empty (the dev server proxies `/api`) |

Later phases add `AVG_TRUCK_SPEED_MPH`, `ORS_API_KEY` and `ORS_BASE_URL`; the routing key is provided through
the environment only.

## Assumptions and product constraints

The rules and every assumption live in [`docs/hos-rules.md`](docs/hos-rules.md). Two things are worth stating
precisely here:

- **The 70-hour cycle is a deliberate product constraint, not an FMCSA requirement.** FMCSA's regulatory limit is
  framed around *driving* after the applicable on-duty limit (70 hours in 8 days). This planner is intentionally
  stricter: it counts driving **and** on-duty-not-driving time toward the cycle, and it stops scheduling any further
  on-duty activity once the remaining cycle allowance is exhausted, reporting the trip as `cycle_exhausted`. It never
  invents a 34-hour restart.
- **This is a planning tool, not a compliance certification.**

## Not in this repository

The Spotter assessment document (`new-full-stack-dev-assessment.docx`) is deliberately git-ignored and is never
committed.

## Attributions

Map tiles © OpenStreetMap contributors and place data from GeoNames (CC BY 4.0) will be credited here when they
are added.
