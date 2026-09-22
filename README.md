# HOS Route Planner

A trip planner and FMCSA-style driver daily-log generator for property-carrying commercial drivers.
Enter a current location, a pickup, a drop-off and the hours already used on the current 70-hour/8-day
cycle, and get back a routed map with fuel and rest stops, one 24-hour log sheet per day of the trip,
and a daily summary of drive/on-duty/off-duty time.

## Status

Feature-complete for its scope: the HOS planning engine, routing integration, API and log-sheet UI are
implemented and covered by automated tests. It runs locally (see [Run it locally](#run-it-locally)) and
is not currently hosted anywhere — there is no live demo link.

## Features

- **HOS-compliant trip planning** — given a start, pickup, drop-off and cycle hours already used, computes
  a day-by-day schedule of driving, on-duty, sleeper-berth and off-duty segments that respects the 11-hour
  driving limit, 14-hour on-duty window, 30-minute break rule, 10-hour reset and the 70-hour/8-day cycle.
- **Independent validator** — a second, minute-stepping implementation with 12 named checks re-verifies
  every plan the event-driven planner produces; a plan the validator rejects is never returned.
- **Route map** — driving directions and stop markers rendered on an OpenStreetMap base layer, using
  OpenRouteService (`driving-hgv` profile) for the route geometry and drive times.
- **Location typeahead** — address/place search backed by Photon.
- **FMCSA-style daily log sheets** — a hand-built SVG rendering of the standard 24-hour grid (not a canvas
  or image overlay), one per day, with duty-status lines, totals, remarks (`City, ST` from an offline
  GeoNames lookup) and the 70-hour/60-hour recap.
- **Multi-day planning** — trips that span more than one day produce one log sheet and daily summary per
  day, all derived from the same underlying segment list the totals are computed from.
- **Cycle-exhaustion handling** — if a trip cannot be completed within the driver's remaining 70-hour
  allowance, the planner stops rather than inventing a restart, and returns the plan built so far with a
  `cycle_exhausted` status and the unplanned remainder (HTTP 200 — this is a result, not an error).

## Tech stack

| Layer | Stack |
| --- | --- |
| Backend | Python 3.12 · Django 5.2 LTS · Django REST Framework · stateless, no database |
| Routing / geocoding | OpenRouteService (`driving-hgv`) · Photon (typeahead) · offline GeoNames CSV (log remarks) |
| Frontend | React 19 · TypeScript (strict) · Vite · Tailwind CSS v4 · TanStack Query · react-hook-form + Zod |
| Map | Leaflet / react-leaflet over OpenStreetMap tiles |
| Tests | pytest + Hypothesis (backend) · Vitest + React Testing Library (frontend) |

## Architecture

- **Stateless** Django + DRF API, no database, no authentication. One main endpoint, `POST /api/trips/plan`,
  plus `GET /api/health`, `GET /api/locations/search` and an OpenAPI schema at `/api/docs/`.
- `backend/trips/hos/` is pure Python, stdlib-only — no Django, no HTTP client, no external API calls, no
  wall-clock reads. It contains two **independent** HOS implementations that share no logic: an event-driven
  planner and a minute-stepping validator with 12 named checks, so a bug in one is unlikely to be masked by
  the other.
- Routing and geocoding sit behind a `RoutingService` abstraction, isolating the HOS engine from any
  particular provider and from network failure modes.
- **The server computes everything that has to be correct** — schedule, segment minute-of-day placement,
  totals, remarks, the 70/60-hour recap and trip status. The React frontend handles form validation,
  rendering, interaction, map display and loading/error states; it does not implement HOS rules or
  recompute the schedule (enforced by an import-graph guard test).

Full design rationale, API contract and rules spec:

| Doc | Purpose |
| --- | --- |
| [`docs/hos-rules.md`](docs/hos-rules.md) | The HOS rules spec: decisions, assumptions, the planner algorithm, the validator's 12 checks, and the golden test scenarios. |
| [`docs/architecture.md`](docs/architecture.md) | System design, API contract at a glance, service boundaries, dependency choices. |
| [`docs/api-contract.md`](docs/api-contract.md) | Field-by-field request/response contract for `POST /api/trips/plan`, matching the running code. |
| [`docs/implementation-plan.md`](docs/implementation-plan.md) | Build phases, testing strategy, risk register, and the open questions/decisions log. |
| `GET /api/docs/` | Live, browsable OpenAPI 3 schema for the running backend. |

## Repository layout

```text
backend/    Django project (config/) and the trips app: api/, hos/ (pure Python), routing/, tests/
frontend/   Vite + React + TypeScript app (src/features/, src/components/, src/lib/)
docs/       hos-rules.md (rules spec) · architecture.md · api-contract.md · implementation-plan.md
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

Routing and typeahead need an OpenRouteService API key (free tier) — see Configuration below. Without one,
the backend still runs, but `/api/trips/plan` and `/api/locations/search` calls that need live routing will
fail.

## Testing

```powershell
# backend (virtual environment active, from backend\)
pytest ; ruff check . ; ruff format --check . ; mypy

# frontend (from frontend\)
npm run lint ; npm run typecheck ; npm test ; npm run format:check ; npm run build
```

The backend test suite includes hand-computed "golden" scenarios (S1–S6 and a boundary variant), explicit
boundary-condition tests, and property-based tests (Hypothesis) asserting invariants like "every daily log
sums to exactly 1,440 minutes" and "the plan the validator accepts is the plan the planner produced." Live
network calls to OpenRouteService/Photon are opt-in only (`pytest -m live`) and excluded from the default run.

## Configuration

All configuration is read from real environment variables — nothing is hardcoded and no secret is ever
committed. For local development, `backend/config/settings.py` also loads a `backend/.env` file if one
exists (via `python-dotenv`), so you can keep local values in a git-ignored file instead of exporting them
in every shell; values already set in the real environment always take precedence, and no `.env` file is
ever read outside that local convenience path. `backend/.env.example` and `frontend/.env.example` document
the variable names only — never fill them in and commit the result.

| Variable | Purpose | Default |
| --- | --- | --- |
| `DJANGO_SECRET_KEY` | Django secret key | required unless `DJANGO_DEBUG=true` |
| `DJANGO_DEBUG` | development mode | `false` |
| `DJANGO_ALLOWED_HOSTS` | comma-separated host allow-list | `localhost,127.0.0.1` |
| `CORS_ALLOWED_ORIGINS` | comma-separated origins allowed to call the API | `http://localhost:5173` |
| `ORS_API_KEY` | OpenRouteService key — **environment only**, never a file, the repo or the frontend | none (routing calls fail without it) |
| `ORS_BASE_URL` | OpenRouteService base URL | `https://api.heigit.org/openrouteservice` |
| `PHOTON_BASE_URL` | Photon typeahead base URL | public Photon instance |
| `AVG_TRUCK_SPEED_MPH` | average speed used for drive-time estimates | `55` |
| `UPSTREAM_TIMEOUT_S` | timeout for routing/geocoding HTTP calls | `10` |
| `THROTTLE_PLAN` / `THROTTLE_SEARCH` | DRF throttle rates for the plan/search endpoints | `30/min` / `120/min` |
| `LOG_CARRIER_NAME`, `LOG_MAIN_OFFICE`, `LOG_HOME_TERMINAL`, `LOG_TRUCK_NUMBER` | optional header fields printed on the log sheet | empty |
| `VITE_API_BASE_URL` | API origin used by the frontend | empty (the dev server proxies `/api`) |

## Assumptions and limitations

The full rules spec and every assumption live in [`docs/hos-rules.md`](docs/hos-rules.md). Worth stating
precisely here:

- **The 70-hour cycle counting driving *and* on-duty-not-driving time is a deliberate product constraint,
  not a claim about FMCSA's exact regulatory wording.** FMCSA's on-duty limit is framed around driving
  after a given number of on-duty hours; this planner is intentionally stricter — it counts all on-duty
  time toward the 70-hour/8-day allowance and stops scheduling further on-duty activity once that
  allowance is exhausted, returning `cycle_exhausted` rather than continuing. It never invents an automatic
  34-hour restart.
- **This is a planning tool, not a compliance certification.** It does not replace an ELD or a carrier's
  own HOS compliance program.
- Out of scope by design: authentication/accounts, saved trips or any database persistence, real-time fuel
  station lookup, live traffic or weather, team drivers, split-sleeper, the 60-hour/7-day cycle, short-haul
  exceptions, PDF export, and post-trip inspection.
- The trip start time is a fixed convention (08:00 local time on the trip origin's date), not a
  user-supplied field.
- Average speed (default 55 mph) and stop durations (e.g. a 15-minute pre-trip) are configurable
  assumptions used for scheduling, not FMCSA requirements.

## Attributions

- Map tiles © [OpenStreetMap](https://www.openstreetmap.org/copyright) contributors, attributed in-app on
  the route map.
- Offline US place lookup (used to render `City, ST` in log remarks) built from
  [GeoNames](https://www.geonames.org/) data, licensed [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
