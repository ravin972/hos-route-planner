# Implementation Plan

> **Status:** **rev 3** — 2026-09-21. **G0 approved. Phase 0 is built and verified; awaiting your G1 review.** Phases 1–7 have not started (§9).
> Companion docs: [`architecture.md`](architecture.md) · [`hos-rules.md`](hos-rules.md).

---

## 1. Reconnaissance

### 1.1 Environment

| Item | Finding |
| --- | --- |
| OS / shell | Windows 11 Home (10.0.26200). Primary shell **PowerShell 7.6.6**; Git Bash (POSIX) also available. `pdftotext` exists under Git's `mingw64`. |
| Python | **3.12.8** (`python`) and **3.14.0** (`py` launcher default), plus a 3.8 Store stub. pip 26.0.1. → **Use 3.12** (`py -3.12 -m venv`). |
| Node | **22.23.2**, npm **11.6.2**, pnpm 10.25.0 (yarn absent). |
| Git / GitHub | git **2.55.0** (user "Ravin Pandey"); `gh` **2.101.0** logged in as `ravin972` (HTTPS; scopes `repo`, `gist`, `read:org`). |
| Claude Code | **2.1.278** |
| Hosting CLIs | Vercel CLI **50.4.0** (Django deploys need **≥ 50.38.0** → upgrade); gcloud 578.0.0; flyctl / railway / render absent. |
| Other | Docker 29.8.0 (daemon not checked), psql 17.11 (**not needed** — no DB), uv 0.11.2, poetry absent. |

### 1.2 Repository state

- `R:\spotter-hos-planner` is **not a git repository** and is **not empty**.
- **Reference files (5):** the assessment docx, `fmsca-image.png` (a *highlighted* table of contents of the FMCSA guide),
  `blank-paper-log.png` (the log form), the FMCSA driver's guide PDF (4.3 MB).
- **The highlighted TOC** marks, among others, *60/70-Hour On-Duty Limit*, *rolling 8-day total*, **34-Hour Restart** and
  **Sleeper Berth Provision**, and does **not** mark the adverse-driving or short-haul exceptions. (Split sleeper stays out of scope
  per D-10; see Q18.)
- **An empty scaffold created today at 12:55–12:56**, every file 1–2 bytes (newline placeholders): `.gitignore`, `README.md`, `CLAUDE.md`,
  `docs/{architecture,hos-rules,api-contract}.md`, `backend/{manage.py,requirements.txt,.env.example}`, `frontend/{package.json,.env.example}`,
  plus `.gitkeep` in `backend/config`, `backend/trips/{api,hos,routing,tests}` and `frontend/src/{components,features,hooks,lib,types}`.
  **No application code. No dependencies installed. No Django project.**
- **Implications**
  1. We adopt the scaffold's structure rather than fight it (architecture.md §4.1, §5.1).
  2. `.gitignore` is empty → populate it **before** the first commit (secrets, `.venv`, `node_modules`, `.env*`).
  3. `manage.py` / `package.json` are empty placeholders and will be replaced. Vite's scaffolder balks at non-empty dirs → scaffold in a scratch dir and copy in.
  4. Reference files: recommend moving them to `docs/reference/` and **not committing the docx** (Spotter's assessment; not ours to republish in a public repo). The FMCSA PDF is public but heavy — link to it instead. *(decision Q12)*
- **Files changed so far:** only the four planning docs (`CLAUDE.md`, `docs/architecture.md`, `docs/hos-rules.md`, `docs/implementation-plan.md`), in
  two revisions (§9). `docs/api-contract.md` is an intentionally empty placeholder. *(Superseded by Phase 0: code, installs and `git init` now exist. Nothing is committed, pushed or deployed.)*

### 1.3 Kickoff prompt vs. the assessment docx

You said the docx is authoritative. It is **shorter** than the kickoff. Anything not in the docx is flagged here rather than added silently.

| Item | In docx? | Handling |
| --- | --- | --- |
| 4 inputs (current, pickup, dropoff, cycle used) | Yes | Built as specified |
| Map with route + stop/rest info; free map API | Yes | ORS + OSM tiles (no paid keys) |
| Daily log sheets, drawn and filled, multiple for long trips | Yes | Server-built logs, SVG sheet |
| 70 h / 8 days, property-carrying, no adverse conditions | Yes | **Cycle counts driving *and* on-duty-not-driving (D-1)** |
| Fuel at least every 1,000 mi; 1 h pickup; 1 h drop-off | Yes | |
| **"Route instructions"** as an output | **Yes** (Objective), absent from kickoff | Included: collapsible turn-by-turn per leg (cheap — the router returns steps) |
| 11 h driving · 14 h window · 30-min interruption · 10 h off | **No** — from FMCSA guide + kickoff | Included (they *are* the log rules); source: guide |
| **15-min pre-trip** | **No** — kickoff only | Assumption A-6 / A-7 |
| **55–60 mph** | **No** — kickoff only | Assumption A-8 / D-5: one documented default (**55**), configurable; tests use 50 |
| **Daily summaries** | **No** — kickoff only | Included (derived from logs, ~free) |
| **34-hour restart** | **No** | **Modelled internally, OFF by default; never present in a returned plan (D-2)** |
| **"Flag a cycle violation if the trip exceeds the remaining cycle"** | **No — not in the docx text** (searched: zero hits for restart / 34 / violation / flag / exceed) | **Product-owner decision D-2**, implemented as `status = cycle_exhausted` + warning. If it comes from another Spotter message, tell me and I will cite it |
| Live hosted version ("can use Vercel.app"), Loom 3–5 min, GitHub code | Yes | Phase 7 |
| "Accuracy must be up to standards"; UI/UX weighs heavily and "can compensate for some inaccuracies" | Yes | Drives priorities: correctness first, polish second |
| **Form defect:** the provided log form transposes "last 7 / last 8 days" between its 70 h and 60 h recap columns | — | We label the 70 h column "last 8 days"; noted in README (hos-rules §9.4) |

## 2. Requirements traceability

| Requirement | Component | Phase | Verified by |
| --- | --- | --- | --- |
| Input: current, pickup, dropoff | `TripForm`, `POST /api/trips/plan` | 3, 4 | form tests, API tests |
| Input: current cycle used (h) | `cycle_used_hours` → integer minutes → allowance `R` (D-1, D-4) | 1, 3, 4 | boundary tests (0, 69.75, 70, 70.01), rule M-1 tests |
| Route map | `RouteMap`, ORS geometry via `RoutingService` | 2, 5 | fixture tests, manual QA |
| Stops / rests / fuel points | `stops[]`, `StopsTimeline`, map markers | 1, 3, 5 | goldens S1–S6 |
| Route instructions | `route.legs[].steps`, `RouteInstructions` | 2, 5 | adapter + component tests |
| Daily FMCSA-style logs, multi-day | `hos.logs`, `LogSheet` SVG | 1, 5 | goldens, property 4, DOM tests |
| Daily summaries | `daily_logs[].summary`, `DailySummaryTable` | 3, 5 | API + component tests |
| 70 h on-duty cycle, 11 h, 14 h, 30-min interruption, 10 h | `hos.planner` + independent `hos.validator` (D-6) | 1 | rule tests, properties, validator self-tests |
| **Cycle-violation flag, no silent restart (D-2)** | `PlanResult.status`, `summary.status`, warning, banner | 1, 3, 5 | goldens S4–S6, API + component tests |
| Fuel ≥ every 1,000 mi | FUEL-1 | 1 | S3, property 5 |
| 1 h pickup / drop-off, 15-min pre-trip | A-1, A-2, A-6 | 1 | S1–S6 |
| Routing behind an abstraction (D-7) | `RoutingService`, `GeocodingService` | 2 | adapter tests, import-graph test |
| React does not implement HOS (D-8) | architecture §5.0 | 4, 5 | guard test, review at G4 |
| Hosted, GitHub, Loom | Vercel ×2, repo, §8 | 7 | smoke checklist, G6, G7 |
| UI/UX quality | architecture §5 | 4, 5, 6 | visual QA vs paper form, axe, phone-width pass |

## 3. Phases and approval gates

Effort = focused engineering hours with AI assistance; a range, not a promise. **Total ≈ 25–34 h.**

### 3.1 Gates (D-9)

**Stop and wait at every gate.** No gate is implied by the previous one. Creating the GitHub repo, pushing, and deploying each
need your explicit go-ahead at **G6**; the optional Phase-2 deploy spike needs its own explicit approval when we reach it.

| Gate | Name | Follows | You verify |
| --- | --- | --- | --- |
| **G0** | Docs / rules approval | **approved 2026-09-21** | These four docs; decisions Q1–Q19 are recorded in §7.3 |
| **G1** | Bootstrap verification | Phase 0 — **built; awaiting your review** | Both toolchains run; all gate commands green; layout matches architecture §4.1 / §5.1; `git status` clean of secrets; `trips/hos` stdlib-only test passes |
| **G2** | HOS engine verification | Phase 1 | Goldens S1–S6 + S4b, boundary tests and 11 properties pass; the validator's 12 checks each fire on a mutated plan; you hand-check S3, S4, S6; no `restart` in any default plan |
| **G3** | Routing / API verification | Phases 2–3 | ORS adapter on recorded fixtures **and** one live call; geometry / places / time-zone tests; API contract incl. `cycle_exhausted` = HTTP 200; OpenAPI; a real `curl` plan |
| **G4** | Frontend verification | Phases 4–5 | Form, map, stops, log sheets, summary and banners at desktop and phone width; a11y pass; **client contains no HOS logic** (guard test + your review) |
| **G5** | End-to-end verification | Phase 6 | Manual QA matrix (§4.3) on the local stack; Playwright smoke; every gate command green |
| **G6** | Deployment verification | Phase 7a | Hosted frontend + backend; env vars; CORS; hosted smoke passes |
| **G7** | Final submission verification | Phase 7b | README, repo hygiene (no secrets, no docx), Loom recorded, links in README; §6 checklist complete |

### Phase 0 — Bootstrap · **done — awaiting G1**

- `git init` (`main`); real `.gitignore`; README skeleton (setup, run, test, **assumptions**, attributions: GeoNames CC BY 4.0, © OpenStreetMap).
- Backend: `py -3.12 -m venv backend\.venv`; install Django 5.2 LTS and DRF (+ pytest, pytest-django, ruff, mypy) — every other library arrives in the phase that first uses it, and `python-dotenv` is dropped (environment variables only, Q14); Django project in `backend/config`, app `trips`; **minimal settings** (architecture §4.6); `GET /api/health`; ruff / mypy / pytest config; **import-graph test** (`trips/hos` is stdlib-only; `routing` ↛ `hos`).
- Frontend: Vite + React + TS + Tailwind v4 (scaffolded in scratch, copied in); ESLint / Prettier; Vitest + RTL (MSW arrives in Phase 4); Vite `/api` proxy.
- ~~CI workflow skeleton.~~ **Not created** — the G0 answer to Q11 was "do not add optional features".
- **Exit:** `pytest`, `vitest`, `tsc`, `eslint`, `npm run build` all green; both dev servers start; `git status` shows no secrets. **Met on 2026-09-21** — the actual command output is in the G1 report.
- **Deviations from the plan:** (1) tests run on `config.settings_test`, because pytest-django initialises Django before any `conftest.py` runs; (2) only what Phase 0 exercises was installed (architecture §9); (3) no CI workflow (Q11); (4) `frontend/` was scaffolded with `create-vite` 9.2.1 (ESLint variant) in a scratch directory and copied in; (5) the `.gitkeep` placeholders were removed from backend folders that now hold real files.

### Phase 1 — HOS engine (pure Python) · 5–7 h → **G2**

TDD, in this order:

1. `constants` + `types` (`PlanParams` incl. `allow_34_hour_restart = False`, `PlanResult`, `CycleStop`, `Segment`, `Violation`); minutes are `int` everywhere (rule M-1).
2. **`validator` first** — the independent oracle, all twelve checks in hos-rules §10.
3. Golden tests **S1–S6 and S4b** written *red*.
4. `planner` to green: the cycle wall, atomic on-duty activities, "no dangling rest", no redundant break, greedy precedence (hos-rules §8).
5. Boundary tests, then the 11 Hypothesis properties.
6. `logs` (day slicing, totals, remarks, the `cycle_exhausted` remark), then `recap`.

- **Exit:** every scenario, boundary and property in hos-rules §11 passes · `trips/hos` ≥ 95 % branch coverage · stdlib-only · a `cycle_exhausted` plan validates clean · hos-rules.md matches behaviour.

### Phase 2 — Routing, geo and hosting spikes · 3–4 h → **G3** (with Phase 3)

- **ORS spike** — first re-verify the current HeiGIT/ORS docs, use `https://api.heigit.org/openrouteservice` and **never** the deprecated `api.openrouteservice.org` (shuts down 2026-09-28) — with your key (environment variable only): real Chicago→St. Louis→Dallas and a cross-country route; record sanitized fixtures; check latency, response size, snapping of rural/odd coordinates, unit options, step shape; **confirm the actual free quota**.
- `routing/base.py` (**`RoutingService`**, `GeocodingService` Protocols), `routing/ors.py`, `routing/photon.py`, `routing/geometry.py` (polyline decode/encode/simplify, mile→coordinate index), `routing/places.py` + `scripts/build_places.py` + committed CSV, `routing/timezone.py` (**size check** for `timezonefinder`, else `tzfpy`), caching, error mapping.
- **Document and test that `driving-hgv` is an external dependency that can fail** (429, 5xx, timeout, malformed, unroutable) and that each failure becomes a typed error at the adapter boundary.
- **Deploy spike — moved earlier (Q13): proposed right after G1, before Phase 1.** A walking skeleton (`/api/health` + the Phase 0 page) on Vercel ×2, to surface Python-runtime, bundle-size and settings-without-DB surprises **now**. It needs your explicit go-ahead, a Vercel login, and Vercel CLI ≥ 50.38.0 (installed: 50.4.0). Nothing is deployed until you approve it.
- **Exit:** adapter contract tests pass on recorded fixtures · opt-in `pytest -m live` passes · interpolated route points lie on the polyline · place lookup passes a ~30-point known-answer set.

### Phase 3 — API layer · 2–3 h → **G3**

Serializers · `services.plan_trip` (hours → integer minutes once; `PlanParams` from settings with `allow_34_hour_restart=False`; departure from the fixed start-time convention, A-16) · views · error envelope · throttles · CORS · drf-spectacular schema + `/api/docs/` · write `docs/api-contract.md` · API tests with a fake `RoutingService`.

- **Exit:** a real `curl` returns a valid plan · **a `cycle_exhausted` request returns HTTP 200 with `summary.status`, the `cycle_exhausted` warning, `unplanned` and `arrival_at = null`** · every error code in architecture §4.4 has a test · response validates against the OpenAPI schema · `plan_self_check_failed` path tested.

### Phase 4 — Frontend foundation and form · 3–4 h → **G4** (with Phase 5)

Design tokens · `AppShell` · `TripForm` (3 comboboxes with typeahead + cycle used; **no departure-time field**, Q4) · Zod schema · API client · loading / error states · "Try an example" · MSW handlers · tests. **No HOS logic** (architecture §5.0).

- **Exit:** form drives the real local API and shows the raw summary · keyboard-only operable.

### Phase 5 — Results UI · 6–8 h (largest) → **G4**

Summary strip · `RouteMap` (lazy chunk; `cycle-limit` marker) · `StopsTimeline` · `RouteInstructions` · `DailySummaryTable` · **`LogSheet` SVG** (grid, ticks, step-lines + connectors, totals, remarks, recap, header) · `DayTabs` · **cycle-violation banner** · responsive polish · empty/edge states · visual QA against `blank-paper-log.png` and the FMCSA sample (guide p.19).

- **Exit:** the S3 fixture renders a sheet whose totals and drawn lines match the goldens · the S4 fixture renders the banner and one truncated log · flow works at phone width · axe reports no serious issues · guard test finds no HOS constants in `frontend/src`.

### Phase 6 — Hardening and QA · 3–4 h → **G5**

Run the manual trip matrix (§4.3) · hand-audit three plans against the spec · Playwright smoke · perf / bundle check · error-UX pass · README with screenshots · security checklist · dead-code sweep.

- **Exit:** no known correctness bugs · all checks green in CI.

### Phase 7a — Deploy · 1.5–2 h → **G6**

Upgrade Vercel CLI → create GitHub repo (**private initially, Q12; nothing is pushed without your explicit go-ahead**) → two Vercel projects → env vars + CORS → hosted smoke. Review the Phase 0 `manage.py check --deploy` baseline (W002 X-Frame-Options, W003 CSRF middleware, W004 HSTS, W008 SSL redirect) and decide each.

- **Exit:** hosted URL passes the §6 smoke items.

### Phase 7b — Submit · ~1 h → **G7**

README with live URLs and the assumptions list · repo hygiene check · Loom rehearsal and recording (§8).

- **Exit:** §6 checklist complete · repo link and Loom link in hand.

### Cut list (if time-boxed, drop in this order)

1. Hover-linking timeline ↔ map · 2. OSRM fallback adapter · 3. `openapi-typescript` generation (hand-type instead) · 4. Playwright ·
5. CI · 6. Photon typeahead → plain submit-time geocode · 7. Route-instructions list. **Never cut:** the validator, goldens, properties,

cycle-exhausted flagging, the log sheet.

## 4. Testing strategy

**Principles.** (1) Test the rules, not the framework. (2) Two *independent* HOS implementations — event-driven planner vs minute-stepping validator (D-6).
(3) Hand-computed goldens are the oracle. (4) Property-based tests for invariants. (5) No network in CI. (6) No hidden clock or randomness.
(7) Integer minutes everywhere in `hos` (D-4).

### 4.1 Backend

| Layer | Tooling | What | Target |
| --- | --- | --- | --- |
| HOS rules | pytest | one test per rule ID (HOS-1…6, FUEL-1) and every boundary in hos-rules §11 | ~70–90 tests |
| HOS goldens | pytest | **S1–S6 and S4b**: full timelines, per-day totals, recap, `status` and `CycleStop` fields; JSON exported as shared fixtures | 7 scenarios |
| HOS properties | Hypothesis | the 11 invariants in hos-rules §11 (cycle cap, status consistency, prefix, no redundant break, …); ≥ 500 examples in CI | seeds printed on failure |
| Validator self-test | pytest | take a valid plan, mutate by 1 minute → the **exact** violation code, for each of the 12 codes | 12 |
| Integer-minute guard | pytest + mypy | `Minutes` type; floats rejected at `plan()`; every boundary an `int`; a test that `constants.py` equals the literals in hos-rules | — |
| Routing adapters | pytest + `responses` | recorded fixtures; 429 / 5xx / timeout / malformed / unroutable → typed errors; provider failure never reaches `hos` | all paths |
| Geometry / places / tz | pytest | polyline round-trip, haversine, interpolation, simplify keeps endpoints; place known-answers; Arizona (no DST) and cross-zone cases | unit |
| API | DRF `APIClient` + fake `RoutingService` | happy path; **`cycle_exhausted` → 200 with status / warning / `unplanned`**; each error code; throttling; OpenAPI conformance | every endpoint |
| Architecture | pytest | import-graph: `hos` is stdlib-only (no `routing`, `api`, Django, DRF, `requests`, `httpx`); `routing` ↛ `hos` | 1 test |
| Live smoke | `pytest -m live` | 2 tests against real ORS / Photon (opt-in, needs key) | manual / CI-off |

Coverage gates: **`trips/hos` ≥ 95 % branch**, backend overall ≥ 85 %.

### 4.2 Frontend

| Layer | Tooling | What |
| --- | --- | --- |
| Pure logic | Vitest | `logGeometry` (minute→x, status→row, path building incl. midnight edges) |
| Components | RTL + MSW | form validation and roles; combobox keyboard flow; loading / error / success; `LogSheet` renders 4 rows, correct totals text and expected `<path d>` for the S3 fixture; **the cycle banner and truncated log render from the S4 fixture's API fields only**; map marker count incl. `cycle_limit` (Leaflet mocked; jsdom has no layout) |
| Guard | Vitest | greps `frontend/src` for HOS constants (`660`, `840`, `480`, `4200`, `2040`) so no rule creeps into the client (D-8) |
| E2E | Playwright | 1 happy-path against mocked API; 1 optional pass against the hosted URL |

**Shared fixtures:** the backend test suite produces `plan_s3.json` and `plan_s4.json`; a script copies them into `frontend/src/test/fixtures/`, and a check fails if they diverge.

### 4.3 Manual QA matrix (Phase 6)

| # | Trip (current → pickup → dropoff) | Cycle | Expect (approximate — confirm against real routes) |
| --- | --- | --- | --- |
| 1 | Chicago → Milwaukee → Madison | 0 | one log, ~3 h driving, no rest / fuel / break, `complete` |
| 2 | Chicago → St. Louis → Dallas | 32.5 | ~900–950 mi, 2 logs, ≥ 1 rest and ≥ 1 break, `complete` |
| 3 | Los Angeles → Denver → New York | 0 | ~2,800 mi, ~6 logs, ≥ 2 fuel stops, `complete` (≈ 55 on-duty h ≤ 70) |
| 4 | same as 3 | 20 | **`cycle_exhausted`**: schedule stops when the allowance runs out (≈ 55 h needed, 50 h available); banner, `cycle_limit` marker, `arrival_at` null; **no restart** |
| 5 | any ~850 mi trip | 60 | S4-like: `cycle_exhausted` after ~10 h on duty; single log; unplanned miles shown |
| 6 | any | 70 | nothing scheduled: one 24 h `OFF` log, `cycle_exhausted`, map shows the route only |
| 7 | short trip whose drop-off just misses the allowance | 62 (S6 legs) | `blocked = dropoff`; drop-off not performed |
| 8 | pickup = current | 10 | 0-mile first leg; pre-trip → pickup back-to-back; no break inserted after the pickup |
| 9 | pickup = dropoff | 10 | 0-mile second leg |
| 10 | New York → Chicago → Denver | 0 | logs stay in origin (Eastern) time; every log = 24 h |
| 11 | Alaska/Hawaii/non-US point; bad ORS key; forced timeout | — | 400 / 422 / 502 / 504 with readable messages; nothing crashes |

The restart option is **not** reachable from the UI; it is covered by unit test S4b only.

### 4.4 Gate commands (every phase exit)

`ruff check` · `mypy` (scoped) · `pytest` · `eslint` · `tsc --noEmit` · `vitest run` · `npm run build`. Exact invocations live in `CLAUDE.md` once they exist.

## 5. Risk register

L = likelihood, I = impact (H/M/L). HOS-specific risks are in `hos-rules.md` §12.

| ID | Risk | L | I | Mitigation | Phase |
| --- | --- | --- | --- | --- | --- |
| R-1 | HOS logic error (wrong interruption / window / reset / cycle semantics) | M | **H** | independent validator · hand goldens · Hypothesis · G2 review | 1 |
| R-2 | Ambiguous inputs/assumptions change visible output (pre-trip cadence, fuel length, departure time, atomic activities) | H | M | all listed in §7.2; shown in the UI `assumptions` block and README | 0 |
| R-3 | **`driving-hgv` (OpenRouteService) is an external provider dependency and may fail** — quota, outage, 5xx, timeout, unroutable; **the old `api.openrouteservice.org` host is deprecated and shuts down 2026-09-28** | M | **H** | `RoutingService` abstraction · typed 502/504/422 · verify quota in spike · cache · throttle · timeouts · optional OSRM fallback · the HOS engine is unaffected | 2 |
| R-4 | **Photon throttles** typeahead (all users share one Vercel egress IP; no availability guarantee) | M | M | debounce ≥ 250 ms · min 3 chars · 24 h cache · ORS-geocode fallback · free-text submit still works | 2, 4 |
| R-5 | Vercel Python surprises (cold start, `timezonefinder` size, settings must import without DB/.env, CLI too old) | M | M | **deploy spike in Phase 2** · Render + gunicorn fallback documented | 2 |
| R-6 | Log SVG is illegible/inaccurate on busy days | M | M | leader labels **plus** remarks table · visual QA vs FMCSA sample · DOM tests on goldens | 5 |
| R-7 | Time-zone / DST edge cases | L | M | one fixed offset per trip (documented) · midnight and Arizona tests | 1, 2 |
| R-8 | Tooling churn: TypeScript 7, Vite 8, ESLint 10, Vitest 5 are new majors | M | L | pin exact versions; drop to previous major on first real friction | 0 |
| R-9 | Scope creep beyond the docx | M | M | scope guard in `CLAUDE.md`; every extra flagged in §1.3 / §7 | all |
| R-10 | Time overrun (Phase 5 is the long pole) | M | M | cut list in §3 | 5 |
| R-11 | Secrets or the assessment docx committed | L | **H** | `.gitignore` first · `.env.example` only · review `git status` before every commit · **no push without your go-ahead** | 0, 7 |
| R-12 | Environment friction (PowerShell vs bash, Python 3.14 default, Windows lacks tz database) | M | L | pin 3.12 venv · `tzdata` · commands documented in `CLAUDE.md` | 0 |
| R-13 | Reviewer compares ETAs to Google Maps | L | M | speed assumption stated in the UI; "planning estimate" footer | 5 |
| R-14 | OSM tile policy / tiles unavailable | L | M | tile URL is one constant; CARTO as alternative | 5 |
| R-15 | Offline places dataset: licence and size | L | L | GeoNames CC BY 4.0 attribution; trimmed CSV | 2 |
| R-16 | **A truncated (`cycle_exhausted`) plan is mistaken for a complete trip** | M | M | `status`, warning, `arrival_at = null`, `unplanned` block, prominent banner; API and component tests | 3, 5 |
| R-17 | **D-1 is stricter than FMCSA guide p.10**; a reviewer may object | L | M | documented as a deliberate, conservative rule (hos-rules §5); README states it; it can never yield a plan the guide would reject | 1 |
| R-18 | **HOS logic creeps into React** (constants, totals, cycle status) | M | M | architecture §5.0 · guard test · G4 review | 4, 5 |

## 6. Definition of done (submission)

- [ ] Gates **G0 → G7** each passed, in order, with your sign-off
- [ ] Hosted frontend and backend both reachable; `/api/health` OK; one canned plan **and** one `cycle_exhausted` plan render end-to-end on the hosted URL
- [ ] Manual QA matrix (§4.3) passed on the **hosted** build, including phone width
- [ ] Validator returns no violations across the property suite; goldens S1–S6 and S4b green; CI green
- [ ] No restart segment in any plan returned by the app; no HOS constants in `frontend/src`
- [ ] README: what it is, live URLs, run/test instructions, **assumptions list**, the D-1 stricter-than-guide note, the form-label deviation, attributions
- [ ] GitHub repo with clean history, no secrets, no assessment docx
- [ ] Loom recorded (3–5 min), link in README

## 7. Decisions and open questions

### 7.1 Resolved by the 2026-09-21 review

| ID | Decision | Where specified |
| --- | --- | --- |
| **D-1** | The 70 h cycle counts **all on-duty time (driving + on-duty-not-driving)** and caps all scheduled on-duty time — **a deliberate product constraint, not an FMCSA requirement**; the single "cycle used" input is the starting consumed hours | hos-rules §3.1, §5 HOS-5, §7 |
| **D-2** | **No automatic 34-hour restart.** Internal option `allow_34_hour_restart` defaults to `False`; exhaustion → stop + `cycle_exhausted` + warning/violation state | hos-rules §7, §8; architecture AD-14 |
| **D-3** | 30-min interruption satisfiable by Off Duty, Sleeper Berth, On Duty Not Driving or any consecutive combination ≥ 30 min; pickup/drop-off/fuel satisfy it; no redundant break | hos-rules HOS-4, §8 |
| **D-4** | All HOS calculations in integer minutes; float hours are presentation-only | hos-rules §6 (rule M-1) |
| **D-5** | Configurable planning speed, single documented default (55 mph; envelope 55–60); tests use 50 | hos-rules A-8; architecture §4.5 |
| **D-6** | Planner and validator independent; validator checks 11 h, 14 h, 30-min interruption, 10 h reset, 70 h cycle, 1,440-min coverage, no overlaps, no gaps (12 checks) | hos-rules §10 |
| **D-7** | OpenRouteService behind a `RoutingService` abstraction; HOS engine has no HTTP-client / ORS / Django / external-API dependency; `driving-hgv` may fail | architecture AD-2, AD-5, §4.3, §7 |
| **D-8** | React validates forms, renders, handles interaction, map, loading/error states — and **does not** implement HOS rules or compute the authoritative schedule | architecture AD-3, §5.0 |
| **D-9** | Approval gates G0–G7 | §3.1 |
| **D-10** | Scope unchanged: no authentication, accounts, database persistence, traffic, weather, real fuel-station lookup, team drivers, split sleeper, adverse conditions, PDF export | hos-rules §2; architecture §1 |

### 7.2 Questions asked at G0 (all answered — kept for the record)

These were the questions and proposed defaults put to you before G0. **All were answered on 2026-09-21; the outcomes in §7.3 override any default below.** Items marked ◆ were the ones that visibly change output. (Q5 — auto-restart — was retired earlier: resolved by D-2.)

| # | Question | Default | Ref |
| --- | --- | --- | --- |
| Q1 ◆ | Pre-trip inspection: every duty period, or only at trip start? | **Every duty period** | A-7 |
| Q2 | D-5 asks for one documented speed default; I documented **55**. Prefer 60? | **55** | A-8 |
| Q3 ◆ | Fuel stop length (docx silent; FMCSA sample uses ½ h)? | **30 min** | A-4 |
| Q4 | Optional "departure time" field (else "now")? Not in docx, but logs need a clock. | **Yes, optional** | A-16 |
| Q6 ◆ | Log rows: 10 h rests as Sleeper Berth; 30-min breaks as Off Duty? | **Yes** | A-12 |
| Q7 | Recap block: fill "on-duty today", A, B; show "—" for C; grey the 60/7 column? | **Yes** | hos-rules §9.4 |
| Q8 | Carrier / truck / home-terminal fields on the sheet: blank lines, or demo defaults? | **Blank** | hos-rules §9.4 |
| Q9 | Time base: origin's zone as home terminal, one fixed offset per trip? | **Yes** | A-15 |
| Q10 | Keep "daily summaries" (kickoff, not docx) and turn-by-turn "route instructions" (docx, not kickoff)? | **Keep both** | §1.3 |
| Q11 | Extras — CI: **yes**; hover-link, print/PDF, OSRM fallback: **no** | as stated | §3 cut list |
| Q12 | GitHub: **public or private + invite**? Move reference files to `docs/reference/` and **exclude the docx**? | **Private until you say; exclude docx** | R-11 |
| Q13 | Hosting: Vercel ×2 (recommended) vs. Render for the backend? | **Vercel ×2** | AD-9 |
| Q14 | Do you already have an **OpenRouteService API key**? (I can't create accounts.) | needed by Phase 2 | architecture §7 |
| Q15 | OK to install dependencies, `git init` and scaffold in Phase 0 once you approve at **G0**? | **Yes, after G0** | §3 |
| Q16 ◆ | **Atomic on-duty activities and "no dangling rest"**: pre-trip, fuel, pickup and drop-off are all-or-nothing against the remaining cycle (e.g. 45 min left, drop-off needs 60 → the plan stops before it, no partial drop-off); a 10 h rest is not scheduled if the next shift couldn't pre-trip and drive | **Atomic; no dangling rest** | A-17 |
| Q17 ◆ | **`cycle_exhausted` is returned as HTTP 200** with a `violation` warning and the partial schedule (not a 4xx) | **200** | A-18, AD-14 |
| Q18 | **Sleeper-berth split** stays out of scope (your D-10) although the highlighted TOC marks "Sleeper Berth Provision". Conscious confirmation only | **Out** | §1.2 |
| Q19 | **Provenance of D-1/D-2:** neither the cycle-violation flag nor the no-restart rule is in the docx text; they are recorded as your decisions. If they come from another Spotter message, share it and I'll cite it | **Recorded as product-owner decisions** | §1.3 |

### 7.3 G0 outcomes (2026-09-21)

| Q | Outcome | Recorded in |
| --- | --- | --- |
| Q1 | Pre-trip inspection once at the beginning of **every driving shift** | hos-rules A-7 |
| Q2 | Default speed **55 mph** | hos-rules A-8 |
| Q3 | Fueling takes **30 minutes** | hos-rules A-4 |
| Q4 | **No user-configurable departure time.** Deterministic convention: **08:00 local time on the current date in the trip origin's time zone** | hos-rules A-16 |
| Q6 | The 10-hour reset is rendered as **Sleeper Berth** | hos-rules A-12 |
| Q7 | "Recap column C represents the 70-hour / last-8-days value"; the image-label defect correction is preserved. **Clarification pending** (§7.4) | hos-rules §9.4 |
| Q8 | Carrier / truck fields stay blank or N/A | hos-rules §9.4 |
| Q9 | Time zone = trip origin / current location; convention documented | hos-rules A-15 |
| Q10 | Keep daily summaries and route instructions | §1.3 |
| Q11 | **No optional features** — so no CI workflow, hover-link, print/PDF or OSRM fallback | §3 (Phase 0, cut list) |
| Q12 | Repository **private initially**; the assessment DOCX is never committed (git-ignored) | `.gitignore` |
| Q13 | **Validate deployment early**; architecture unchanged (Vercel ×2); deploy spike proposed right after G1 | §3 Phase 2; architecture §8 |
| Q14 | `ORS_API_KEY` is provided through environment variables only | architecture §4.5 |
| Q15 | Phase 0 approved | — |
| Q16 | Atomic on-duty activities approved | hos-rules A-17 |
| Q17 | `cycle_exhausted` is HTTP 200 | hos-rules A-18 |
| Q18 | Split sleeper remains out of scope | hos-rules §2 |
| Q19 | D-1 and D-2 are product-owner decisions unless another authoritative Spotter source is provided | hos-rules §1 |
| Routing | Verify current ORS/HeiGIT docs before writing the client; **never** architect around the deprecated `api.openrouteservice.org` (shutdown 2026-09-28). Verified 2026-09-21: `https://api.heigit.org/openrouteservice` | architecture AD-5, §4.5, §7 |
| Wording | The 70-hour behaviour is a **deliberate product constraint**; never describe it as an FMCSA requirement (FMCSA's limit is framed around driving) | hos-rules D-1, HOS-5; README |

### 7.4 Still open

- **Q7 clarification (needed before Phase 1 builds the recap).** In the recap as documented, the 70 h / last-8-days total is box **A** and box **C** is the last-5-days value. Which box should carry the 8-day total? Until you answer, hos-rules §9.4 stands.
- **Reference files.** `blank-paper-log.png`, `fmsca-image.png` and the FMCSA PDF are untracked but **not** git-ignored (only the DOCX is). Decide at the first commit; recommendation: keep them out of the repo and link to the public guide.
- **Deploy spike go-ahead.** Needs your explicit approval, a Vercel login, and upgrading the Vercel CLI (installed 50.4.0; Django deploys need ≥ 50.38.0).

## 8. Loom outline (3–5 min)

| Time | Beat |
| --- | --- |
| 0:00–0:30 | The problem and a live demo trip (the "Try an example" button) |
| 0:30–1:30 | UI walk-through: form → map and stops → daily log sheets → daily summary |
| 1:30–2:45 | **HOS engine**: greedy planner, independent validator, the S3 golden on screen, a `cycle_exhausted` case (S4), property tests |
| 2:45–3:30 | Architecture: stateless Django API, `RoutingService` abstraction, React only renders, SVG log sheet |
| 3:30–4:15 | Trade-offs and assumptions: single-number cycle input, on-duty-counted cycle and an **explicit violation flag instead of a silent restart**, fixed time offset, form-label defect |
| 4:15–4:45 | Deployment, and what I'd do next |

## 9. Revision history

- **rev 1 — 2026-09-21.** Initial recon and the four planning docs.
- **rev 2 — 2026-09-21.** Product-owner review, documentation only:
  - **D-1** cycle counts all on-duty time and caps scheduled on-duty time (HOS-5 rewritten; §7 allowance table; `on_duty()` gate in the algorithm); recap A can never exceed 70.
  - **D-2** no automatic restart: `allow_34_hour_restart = False`; `cycle_exhausted` result state (`CycleStop`, `shortfall_min`), HTTP 200, warning severity `violation`, `cycle_limit` marker; old S4 replaced, **S4b, S5, S6** added; architecture **AD-14**; A-14 rewritten; Q5 retired.
  - **D-3** HOS-4 wording aligned; property "no redundant break" added.
  - **D-4** rule **M-1** (integer minutes; floats only for miles and at the two boundaries); `V_INTEGER`.
  - **D-5** single documented speed default (55), configurable, tests at 50.
  - **D-6** validator expanded to 12 named checks; independence rules made explicit.
  - **D-7** `RoutingProvider`/`GeocodingProvider` renamed **`RoutingService`/`GeocodingService`**; `hos` is stdlib-only; `driving-hgv` documented as an external dependency that may fail (R-3).
  - **D-8** new architecture §5.0 and guard test; risk R-18.
  - **D-9** gates renamed **G0–G7** and mapped to phases; Phase 7 split into 7a/7b.
  - **D-10** scope wording: "authentication" added to the out-of-scope lists.
  - Derived additions for your confirmation: assumptions **A-17** (atomic activities, no dangling rest) and **A-18** (HTTP 200); questions **Q16–Q19**; risks **R-16, R-17**; provenance finding (§1.3).
- **rev 3 — 2026-09-21.** G0 approved; Phase 0 executed:
  - Decisions Q1–Q19 recorded (§7.3). **Q4** removes the departure-time field (deterministic 08:00 origin-local convention, A-16). **Q7** clarification is pending.
  - ORS routing re-verified: the deprecated `api.openrouteservice.org` (shutdown 2026-09-28) is replaced by `https://api.heigit.org/openrouteservice` in AD-5, §4.5 and §7; `ORS_BASE_URL` added.
  - Regulatory wording fixed: the 70 h behaviour is a product constraint, not an FMCSA requirement (D-1, HOS-5, `V_CYCLE_70`, AD-14, CLAUDE.md, README).
  - Dependencies: only what Phase 0 exercises was installed; `python-dotenv` dropped (environment variables only); TypeScript stays on the template's 6.0.x; no CI workflow (Q11).
  - Layout: `config/settings_test.py` added; deploy spike moved to right after G1 (Q13).
