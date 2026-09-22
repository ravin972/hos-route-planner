# HOS Rules & Planning Spec

> **Status:** **rev 3** — 2026-09-21. G0 approved; decisions Q1–Q19 are recorded in §3. Phase 0 scaffolding exists; no HOS code yet.
> **Role:** This is the executable specification for `backend/trips/hos/`. Code, tests and this file must
> agree. If behaviour changes, change this file, the tests and the code **in the same commit**.

---

## 1. Sources and precedence

When sources disagree, the lower number wins.

| # | Source | Used for |
| --- | --- | --- |
| 1 | `new-full-stack-dev-assessment.docx` (Spotter) | What we must build. **Authoritative for requirements.** |
| 2 | **Product-owner decisions D-1 … D-6** (§3.1, from the 2026-09-21 review) | Define *our implementation*. Where they differ from the FMCSA guide (notably D-1), **they win**. |
| 3 | *FMCSA Interstate Truck Driver's Guide to Hours of Service* (Apr 2022), `fmcsa-hos-395-drivers-guide-…pdf` | Meaning of each HOS rule, duty-status definitions, log/grid/remarks format. Page numbers below are the guide's printed page numbers. |
| 4 | `blank-paper-log.png` | Layout of the log sheet we draw (see §9.4 — the form has a labelling error). |
| 5 | Kickoff assumptions | **15-minute pre-trip inspection** and **55–60 mph average speed**. These are *not* in the docx (§3.2). |

**Provenance note.** The docx says only: property-carrying driver, 70 hrs/8 days, no adverse driving conditions,
fuel at least every 1,000 miles, 1 hour for pickup and drop-off. It contains **no wording about a 34-hour restart or
about flagging cycle violations** (searched, zero hits). Those behaviours (D-1, D-2) are recorded here as
**product-owner decisions**, not as docx requirements. The highlighted table-of-contents screenshot
`fmsca-image.png` marks "34-Hour Restart" and "Sleeper Berth Provision" among the guide sections it highlights.

The FMCSA guide states it is guidance, "not a substitute for FMCSA's published regulations". The underlying
regulation is 49 CFR Part 395 (§395.1, §395.2, §395.3, §395.8). This app is a **planning tool**, not a compliance
certification, and the UI footer should say so.

## 2. Scope

**In scope** (docx + kickoff + product-owner decisions): property-carrying CMV · single driver · **70-hour / 8-day
on-duty cycle, where driving *and* on-duty-not-driving both count** · no adverse driving conditions · 11-hour driving
limit · 14-hour window · 30-minute interruption · 10-hour off-duty reset · 1 h pickup · 1 h drop-off · fuel at least
every 1,000 miles · 15-min pre-trip · multi-day trips split into 24-hour logs · US contiguous roads.

**Modelled but OFF by default — the 34-hour restart.** It exists only as an internal planner option,
`allow_34_hour_restart` (default `False`, D-2). It is **not** exposed in the API, the environment or the UI, and
**no plan the app returns contains one**. It exists so the rule can be tested and switched on deliberately later.

**Out of scope — do not build:** authentication or accounts · database persistence / saved trips · traffic · weather ·
real truck-stop/fuel-station lookup · team drivers · sleeper-berth split (7/3, 8/2) · adverse-driving-conditions
extension · PDF export · short-haul exceptions · 60/7 schedule · personal conveyance · yard moves · post-trip
inspection · state intrastate rules · hazmat · Canadian/Mexican rules · **automatic 34-hour restart insertion**.

## 3. Decisions and assumptions

### 3.1 Product-owner decisions (2026-09-21 review)

| ID | Decision | Specified in |
| --- | --- | --- |
| **D-1** | The 70-hour cycle tracks **all on-duty time — driving *and* on-duty-not-driving**. The planner never schedules on-duty time beyond the remaining allowance. **This is a deliberate product constraint, not an FMCSA requirement:** FMCSA's regulatory limit is framed around *driving* after the applicable on-duty limit (guide p.10). | §5 HOS-5 · §7 · §8 |
| **D-2** | **No automatic 34-hour restart.** The planner has an internal option `allow_34_hour_restart` (default `False`). By default, when the remaining cycle cannot cover the next step it **stops scheduling**, returns status `cycle_exhausted`, and emits a clear cycle warning/violation state. A restart is never silently invented. | §5 HOS-6 · §7 · §8 |
| **D-3** | The 30-minute interruption may be satisfied by Off Duty, Sleeper Berth, On Duty Not Driving, or any consecutive combination totalling ≥ 30 minutes. Pickup, drop-off and fueling satisfy it when long enough. **No redundant break** is inserted after a qualifying activity. | §5 HOS-4 · §8 |
| **D-4** | **All HOS calculations use integer minutes.** Floating-point hours are presentation-only. | §6 |
| **D-5** | Planning speed is a **configurable parameter** with a **single documented default of 55 mph** (agreed assessment envelope 55–60). Tests may use 50 mph. | A-8 |
| **D-6** | Planner and validator are **independent**; the validator checks the list in §10. | §10 |

D-7 … D-10 (routing abstraction, frontend responsibility, approval gates G0–G7, unchanged scope) are
architecture/process decisions: see `architecture.md` AD-3 / AD-5 / AD-14 and `implementation-plan.md` §3 and §7.

### 3.2 Assumptions

Every number the planner uses that is *not* a regulation lives here and in `trips/hos/constants.py`.
Status: **D** = stated in the docx; **approved (Qn)** = explicitly confirmed at G0 (2026-09-21); **P** = our assumption, approved with these docs at G0 but not individually queried.

| ID | Assumption | Default | Source | Status |
| --- | --- | --- | --- | --- |
| A-1 | Pickup duration, logged **On Duty (Not Driving)** | 60 min | docx | D |
| A-2 | Drop-off duration, logged On Duty (Not Driving) | 60 min | docx | D |
| A-3 | Fuel at least once every N miles (max miles between fuelings) | 1,000 mi | docx | D |
| A-4 | Fuel stop duration, logged On Duty (Not Driving) — fueling is on-duty per guide p.5; FMCSA's sample log uses ½ h (p.18) | 30 min | guide sample | approved (Q3) |
| A-5 | Tank is full at departure | true | — | **P** |
| A-6 | Pre-trip inspection, logged On Duty (Not Driving) | 15 min | kickoff (not in docx) | **P** |
| A-7 | Pre-trip is performed at the start of **every** duty period (after each 10 h rest), not only on day 1 | every shift | — | approved (Q1): once at the beginning of every driving shift |
| A-8 | Planning speed — used for **all** drive time; routing-engine durations are ignored. A parameter (`PlanParams.avg_speed_mph`, fed from `AVG_TRUCK_SPEED_MPH`), positive and ≤ 80. **Tests use 50 mph** so limits land on whole minutes | **55 mph** | kickoff says 55–60; D-5 | approved (Q2) — single documented default |
| A-9 | Driver has had ≥ 10 consecutive hours off before departure → 11 h / 14 h / break clocks start fresh | true | — | **P** |
| A-10 | Before departure on day 1 the driver is **Off Duty** (log shows Off Duty 00:00 → departure) | true | — | **P** |
| A-11 | After the **last scheduled activity** (the final drop-off, or the stop point of a `cycle_exhausted` plan) the driver is **Off Duty** until 24:00 of that day | true | — | **P** |
| A-12 | Mandatory 10 h rests are logged **Sleeper Berth**; 30-min breaks (and 34 h restarts, if ever enabled) are logged **Off Duty** | as stated | — | approved (Q6) |
| A-13 | **"Current cycle used" is the starting consumed cycle hours.** The assessment does not provide the previous 8 daily totals, so no drop-off of old days is modelled: the value is treated as already consumed for the whole plan | true | D-1 | **P** |
| A-14 | **No 34-hour restart is applied** (D-2). `PlanParams.allow_34_hour_restart = False`; see §7.5 for what changes if it is ever `True` | `False` | D-2 | decision |
| A-15 | Home-terminal time zone = time zone of the **trip origin (current location)**; no terminal input exists. **Convention:** the origin's IANA zone is resolved from its coordinates, one fixed UTC offset (taken at departure) applies to the whole trip, and every date, time and log day is expressed in that zone | origin zone | guide p.16 requires home-terminal time | approved (Q9) |
| A-16 | **No user-configurable departure time.** Departure is a fixed, deterministic convention: **08:00 local time on the current calendar date in the trip origin's time zone**. The date comes from the server clock converted to that zone (injected, so tests are deterministic); the time of day is a constant | 08:00 origin-local | Q4, Q9 | approved (Q4) |
| A-17 | **On-duty activities are atomic.** Pre-trip, fuel, pickup and drop-off are scheduled only if their **whole** duration fits in the remaining allowance; none is ever partially performed. Driving is divisible | atomic | — | approved (Q16) |
| A-18 | **Cycle exhaustion is a result state, not an error.** The plan returned is the longest legal prefix, flagged `cycle_exhausted` (§7.4) | as stated | D-2 | approved (Q17): HTTP 200 |

## 4. Duty statuses and how activities are logged

The log grid has exactly four rows (guide p.16; form rows 1–4).

| Code | Grid row | Activities in this planner |
| --- | --- | --- |
| `OFF` | 1 Off Duty | time before departure · 30-min break · time after the last scheduled activity · 34 h restart *(only if the internal option is on)* |
| `SB` | 2 Sleeper Berth | 10 h mandatory rest |
| `D` | 3 Driving | moving the CMV |
| `ON` | 4 On Duty (not driving) | pre-trip · pickup · fueling · drop-off |

Definitions that matter (guide p.5–6): fueling, inspecting and loading/unloading are **on duty**. Time resting in
a parked CMV or sleeper is **not** on duty. On-duty time counts toward the 14-hour window; **both** `D` and `ON` count
toward the 70-hour cycle (D-1); only `D` counts toward the 11-hour limit and the 8-hour break clock.

## 5. Limits and implementation rules

Each rule has an ID used in tests (`test_hos_rules.py::test_HOS_3_…`) and in the validator's violation codes.

| ID | Rule | Source | Precise semantics we implement |
| --- | --- | --- | --- |
| **HOS-1** | **10-hour reset** | §395.3(a)(1) · p.6 | A period of ≥ 600 consecutive minutes of `OFF`/`SB` **only**. `ON` inside the period breaks it. It resets HOS-2, HOS-3 and HOS-4 clocks. |
| **HOS-2** | **11-hour driving limit** | §395.3(a)(3)(i) · p.6 | ≤ 660 minutes of `D` since the last HOS-1 reset. |
| **HOS-3** | **14-hour window** | §395.3(a)(2) · p.6 | Window opens at the first `ON` or `D` minute after an HOS-1 reset and closes 840 minutes later. **Time is not paused** by breaks, meals or fueling. No `D` minute may start at or after the close. `ON` work after the close is legal (guide p.6 example). |
| **HOS-4** | **30-minute interruption** | §395.3(a)(3)(ii) · p.10 · **D-3** | A `D` minute may not start if ≥ 480 minutes of `D` have accumulated since the last **uninterrupted run of ≥ 30 non-driving minutes**. The run may be `OFF`, `SB`, `ON`, **or any consecutive combination** of them totalling ≥ 30 min (guide p.10: 15 min on-duty + 15 min off-duty satisfies it). Two separated runs never combine. The counter is *cumulative driving*, not wall-clock and not "consecutive driving". **Qualifying activities:** pickup (60), drop-off (60) and fueling (30) each qualify on their own; a pre-trip (15) qualifies only when directly adjacent to other non-driving time totalling ≥ 30. |
| **HOS-5** | **70-hour / 8-day cycle** | §395.3(b) · p.10–11 (FMCSA: no *driving* after 70 h on duty in 8 days) · **D-1** (our constraint) | **Product constraint, stricter than FMCSA:** every on-duty minute — `D` and `ON` — consumes the cycle. `cycle` = carry-in + all `D` + `ON` minutes. The planner **never schedules an on-duty minute when `cycle ≥ 4,200`, and never schedules an activity that would take `cycle` above 4,200.** Rolling over 8 log-days in the validator (§7.6). |
| **HOS-6** | **34-hour restart** | §395.3(c) · p.11 · **D-2** | ≥ 2,040 consecutive minutes of `OFF`/`SB` (any mix) resets `cycle` to 0 and also satisfies HOS-1. The **planner does not schedule one** unless `allow_34_hour_restart = True` (§7.5). The validator always honours a real ≥ 2,040-min run as a reset. |
| **FUEL-1** | **Fuel ≤ 1,000 mi apart** | docx | Miles driven since the last fueling (or departure, A-5) never exceed 1,000. |

**HOS-5 is deliberately stricter than the guide.** The guide (p.10) says a violation of the 70-hour rule "can only
occur if you drive a CMV past these limits as you can remain on-duty not driving". Our implementation rule (D-1) is
that scheduled on-duty time of *any* kind may not exceed the allowance. It only ever errs on the safe side: it can never
produce a plan the guide would reject. It is a **product constraint of this planner, not an FMCSA requirement** — never present it to users as one.

**HOS-4 is the one most often implemented wrongly.** A 1-hour pickup, a 30-min fuel stop or a 1-hour drop-off
already satisfies it and must reset the counter — the planner must *not* insert a redundant break after them.

## 6. Clock model and the integer-minute rule

**Rule M-1 (D-4).** Every duration, timestamp, clock and limit inside `trips/hos` is an `int` number of **minutes**.
No float is ever compared against a limit. Floats exist only for *miles* (distance) and at the two boundaries:

1. **Input:** `cycle_used_hours` (a float from the API) is converted **once**, in `services.py`, to
   `cycle_used_min = round_half_up(hours × 60)`; from then on the engine sees integers only.
2. **Output:** decimal-hour fields (`*_h`, e.g. totals `1.75`) are derived from minutes when serializing. They are
   presentation only and never fed back into any decision.

```text
State (all int minutes, except the two float mile counters)
  t                  current minute from departure
  window_open        minute the 14 h window opened, or None (no active shift)
  drive_shift        D minutes since the last 10 h reset                  (limit 660)
  drive_since_break  D minutes since the last >= 30-min non-driving run    (limit 480)
  nondrive_run       length of the current non-driving run
  cycle              carry-in + all on-duty minutes, D + ON                (limit 4200)
  R                  remaining allowance = 4200 - cycle                    (derived)
  miles_since_fuel   float miles since the last fueling                    (limit 1000)
  pos                float miles along the route
```

Update rules per activity. `drive` and `ON` both require `m ≤ R` (D-1).

| Activity | `t` | `drive_shift` | `drive_since_break` | `nondrive_run` | `cycle` | `miles_since_fuel` |
| --- | --- | --- | --- | --- | --- | --- |
| drive *m* min | += m | += m | += m | = 0 | += m | += m·mph/60 |
| ON *m* min | += m | — | — | += m; if ≥ 30 → `drive_since_break = 0` | += m | — (reset to 0 if fueling) |
| OFF/SB *m* min | += m | if run ≥ 600 → 0 and `window_open = None` | if run ≥ 30 → 0 | += m | if run ≥ 2,040 → 0 | — |

**Rounding — always toward the safe side:**

- Minutes needed to drive *D* miles = `ceil(D·60/mph)`.
- Minutes of driving allowed by a *mile* limit (fuel) = `floor(limit_miles·60/mph)`.
- Miles are derived from minutes at constant speed, then clamped to the milestone on arrival.

## 7. The 70-hour cycle

### 7.1 The input

The docx gives one input, **Current Cycle Used (Hrs)**. It represents the **starting consumed cycle hours** because the
assessment does not provide the previous 8 daily totals (A-13). Accepted range `0 ≤ x ≤ 70`; `70` is valid (nothing can
be scheduled). Above 70 → 400 `validation_error`. Converted to minutes once (M-1). The remaining allowance is
`R = 4,200 − cycle`, in minutes.

### 7.2 What consumes the allowance

Every on-duty minute: pre-trip, driving, fueling, pickup, drop-off. Off Duty, Sleeper Berth and breaks consume nothing.

### 7.3 When each activity may be scheduled

| Activity | Length (min) | Consumes cycle? | Scheduled only if |
| --- | --- | --- | --- |
| Pre-trip | 15 | yes | `R ≥ 15` |
| Driving | up to *n* | yes | `R ≥ 1`; each drive segment is **capped at `R`** (divisible) |
| Fuel stop | 30 | yes | `R ≥ 30` |
| Pickup / drop-off | 60 each | yes | `R ≥ 60` |
| 30-min break | 30 | no (`OFF`) | `R ≥ 1` — a break with no driving after it is pointless |
| 10-hour rest | 600 | no (`SB`) | `R ≥ 16` — the next shift needs a pre-trip (15) plus ≥ 1 min of driving; otherwise the planner stops **instead of** resting ("no dangling rest") |
| 34-hour restart | 2,040 | no (`OFF`) | only if `allow_34_hour_restart` |

Pre-trip, fuel, pickup and drop-off are **atomic** (A-17): if 45 minutes remain and the drop-off needs 60, the plan stops
before the drop-off — it does not perform a partial one.

### 7.4 When the allowance runs out (default behaviour, D-2)

The planner **stops** — the stop is terminal, nothing is scheduled after it — and returns a `PlanResult` with
`status = "cycle_exhausted"` and a `CycleStop`:

| Field | Meaning |
| --- | --- |
| `minute`, `mile` | where scheduling stopped (end of the last scheduled segment; route mile) |
| `blocked` | the step that did not fit: `pretrip` · `drive` · `fuel` · `pickup` · `dropoff` · `next_shift` |
| `pending` | milestones not performed, in order (`pickup`, `dropoff`) |
| `unplanned_miles` | route miles not driven |
| `shortfall_min` | lower bound on the extra cycle minutes still needed: (drive minutes for `unplanned_miles` + minutes of pending pickup/drop-off) − `R`. Excludes pre-trips, fuel stops and breaks. **≥ 1 by construction** |

What the caller sees: `summary.status = "cycle_exhausted"`, a warning `cycle_exhausted` of severity `violation`,
`arrival_at = null`, daily logs that end on the day of the stop (a remark marks the stop), and a `cycle_limit` stop
marker. **HTTP 200** — it is a valid, useful, partial result (A-18).

> **The violation is of the *request*, never of the *timeline*.** "This trip needs more cycle than you have" is what is
> flagged. The schedule returned is always the longest legal prefix and always passes the validator. A restart is never
> invented to hide the problem.

### 7.5 The restart option (internal, default off)

With `allow_34_hour_restart = True`, every "STOP" in §8 becomes: insert a 34 h `OFF` restart, reset `cycle` to 0, begin a
new shift (pre-trip), continue. The plan is then `complete` and carries an `info` warning `cycle_restart_applied`.
The option is **not reachable** from the API, environment or UI. It exists for tests (S4b) and for a deliberate future
product decision.

### 7.6 No old days drop off during a plan

With restarts disabled, a plan schedules at most `70 h − carry-in` of on-duty time, i.e. under 6 days including
10-hour rests (worst case ≈ 70 h on duty + ≤ 6 rests ≈ 5.5 days), so the 8-day window never rolls. The **validator still
implements the general rolling sum** so hand-edited plans, or plans built with the restart option, are checked correctly.

## 8. Planning algorithm

Deterministic, greedy, event-driven. Greedy = do as much as legally possible, rest only when a limit binds. This yields
the shortest legal schedule and a single explainable answer. **`plan(...)` is a pure function of its arguments.**

```text
plan(legs, cycle_used_min, departure, params) -> PlanResult
    # params: avg_speed_mph, durations, allow_34_hour_restart (default False)
    init state per A-9; cycle = cycle_used_min
    milestones = [pickup @ leg1.miles, dropoff @ leg1.miles + leg2.miles]
    begin_shift()                                       # pre-trip; opens the 14 h window
    for m in milestones:
        while pos < m.miles:
            R = 4200 - cycle                            # remaining allowance (D-1)
            if R <= 0:                                  cycle_wall(drive)         # more driving needed
            elif drive_shift >= 660 or window_expired:  rest_10h(); begin_shift()
            elif miles_since_fuel >= 1000:              on_duty(fuel, 30)
            elif drive_since_break >= 480:              off_duty(break, 30)
            else:
                n = min( ceil((m.miles-pos)*60/mph), 660-drive_shift, 480-drive_since_break,
                         window_open+840-t, R, floor((1000-miles_since_fuel)*60/mph) )
                drive(n)
        on_duty(m.kind, 60)                             # pickup / drop-off, atomic

begin_shift():    on_duty(pretrip, 15)                  # every duty period (A-7)

on_duty(kind, d): # every ON activity goes through here
    if d > 4200 - cycle:  cycle_wall(kind)              # does not fit
    schedule d minutes of ON; cycle += d

rest_10h():       # never a dangling rest
    if 4200 - cycle < 16:  cycle_wall(next_shift)
    schedule 600 minutes of SB

cycle_wall(blocked):
    if params.allow_34_hour_restart:  restart_34h(); begin_shift(); retry the blocked step
    else:                             STOP(status = cycle_exhausted, blocked)    # terminal
```

**Precedence when several limits are hit at once:** (1) the cycle wall · (2) 10 h rest (it also resets the break clock,
so a separate break would be redundant) · (3) fuel (a 30-min `ON` stop also satisfies HOS-4, so a due break is then
skipped) · (4) break.

**Behaviours the planner must get right:**

1. **STOP is terminal** and yields a legal prefix; `shortfall_min ≥ 1`.
2. **No restart is ever inserted** unless the internal option is on (D-2). No `restart` segment appears in any plan the app returns.
3. **No redundant break (D-3):** a `break` is scheduled only when `drive_since_break` has actually reached 480. Pickup,
   drop-off and fueling reset that counter, so they are never followed by a needless break.
4. With default durations the 14 h window **cannot bind**: the worst-case non-driving time *before the last driving
   minute* of a shift is 0.25 pre-trip + 1 pickup + 0.5 fuel + 0.5 break = 2.25 h (the drop-off is always last), and
   11 + 2.25 = 13.25 h < 14 h. HOS-3 is still enforced and validated; tests exercise it by raising durations (e.g. a 4 h pickup).
5. Pickup/drop-off may run past the 14 h close (they are not driving).
6. Exactly reaching 70 h **at the end of the final drop-off is a `complete` plan**; the wall is only hit if something
   *more* must be scheduled.
7. The planner has no clock, no I/O, no randomness. "Now" is resolved by the caller.

**Output:** `PlanResult(segments, status ∈ {complete, cycle_exhausted}, stop: CycleStop | None)`. `segments` is an ordered,
contiguous list of `Segment(start, end, status, kind, pos_start, pos_end, note)` with
`kind ∈ {pretrip, drive, pickup, dropoff, fuel, break, rest, restart, idle}` (`restart` only with the option on).
Stops for the UI and rows for the logs are both *derived* from this one list (single source of truth).

## 9. Daily log construction

### 9.1 Day slicing

- Log day = local calendar day in the home-terminal zone (A-15). One fixed UTC offset per trip; DST changes
  mid-trip are ignored so **every log is exactly 1,440 minutes** (documented limitation).
- Segments crossing local midnight are split; the status continues on the next log.
- Day 1 is padded `OFF` from 00:00 to departure (A-10); the last day is padded `OFF` to 24:00 after the last scheduled
  activity (A-11). In a `cycle_exhausted` plan the last log is the day of the stop and carries a remark
  ("70-hour cycle exhausted — trip not completed").
- **Invariant:** for every log, `OFF + SB + D + ON = 24.00 h` exactly, with no gaps and no overlaps (guide p.15).

### 9.2 Totals

Per-row totals are computed from the *same* segments that are drawn — never separately — and shown in decimal hours
(FMCSA sample p.19 shows `10`, `1.75`, `7.75`, `4.5` = 24). Decimal hours are derived from integer minutes (M-1).

### 9.3 Remarks

One remark per **change of duty status**: local time, `City, ST`, and the activity. Locations come from the
offline nearest-place lookup (architecture.md AD-7); the guide (p.17) allows "nearest city, town, or village and
State abbreviation" for changes that happen away from a town.

### 9.4 Form fields → data (`blank-paper-log.png`)

| Form field | Filled with |
| --- | --- |
| Date (month/day/year) | log date |
| From / To | place at 00:00-or-first-activity / place at 24:00-or-last-activity |
| Total Miles Driving Today | sum of `D` miles that day |
| Total Mileage Today | same value (we have no odometer) |
| Truck/Tractor & Trailer numbers, Carrier, Main office, Home terminal | blank lines — not provided by any input (configurable defaults, empty) |
| 24-hour grid + Total Hours | four step-lines from the segments; per-row totals |
| Remarks | §9.3 |
| Shipping documents / commodity | blank — not provided |
| Recap: on-duty hours today (lines 3 + 4) | `D + ON` for the day |
| Recap 70 h/8 day **A** (total on duty in last 8 days incl. today) | `cycle` at 24:00 (carry-in + all on-duty minutes so far). **Never exceeds 70** (D-1) |
| Recap 70 h/8 day **B** (70 − A) | `70 − A` (≥ 0 by construction) |
| Recap 70 h/8 day **C** (last 5 days) | **"—"** — needs day-by-day history we don't collect |
| Recap 60 h/7 day column | greyed out, "not applicable" |

> **Form defect — do not copy blindly.** The provided form prints "*last 7 days*" under **70 Hour/8 Day** and
> "*last 8 days*" under **60 Hour/7 Day** — the two are transposed (the 70-hour rule is 8 days; guide p.10–11). We
> label the 70 h column **"last 8 days"** and note the deviation in the README.
>
> **G0 decision Q7, recorded verbatim:** "Recap column C represents the 70-hour / last-8-days value. Preserve the known
> image-label defect correction documented in the rules." **Clarification needed before Phase 1:** in the table above the
> 70 h / last-8-days total is box **A** and box **C** is the last-5-days value. Which box should carry the 8-day total?
> Until you answer, this section stands (A = last 8 days, B = 70 − A, C = "—").

## 10. Independent validator (D-6)

`trips/hos/validator.py` is a **second implementation**, written differently on purpose. It shares **no logic** with the
planner: it imports only the limit values from `constants.py` and the dataclasses from `types.py`, never calls a planner
function, and steps **minute by minute** through the finished segments (the planner is event-driven). A test asserts
that `constants.py` equals the literal numbers in this document. Two dissimilar implementations agreeing is our main
defence against correlated logic bugs.

`validate(segments, carry_in_min, params) -> list[Violation]` checks:

| Code | Check |
| --- | --- |
| `V_DRIVE_11` | **11-hour driving limit** — driving since the last ≥ 600-min `OFF/SB` run never exceeds 660 |
| `V_WINDOW_14` | **14-hour window** — no `D` minute starts at or after `window_open + 840` |
| `V_BREAK_30` | **30-minute interruption** — no `D` minute starts with ≥ 480 driving minutes since the last ≥ 30-min non-driving run (any mix of `OFF`/`SB`/`ON`) |
| `V_RESET_10` | **10-hour reset** — every planner-labelled `rest` is ≥ 600 consecutive `OFF/SB` minutes, and no `D` minute follows an exhausted 11 h limit or closed 14 h window without an intervening ≥ 600-min `OFF/SB` run (the validator derives resets itself and never trusts labels) |
| `V_CYCLE_70` | **70-hour on-duty cycle** — carry-in + all `D` + `ON` minutes since the last real ≥ 2,040-min `OFF/SB` run never exceed 4,200 **at any on-duty minute** (product constraint D-1; FMCSA's own limit is on driving), over the trailing 8 log-days |
| `V_RESTART_34` | a `restart` segment exists only if `allow_34_hour_restart` is on, and is ≥ 2,040 consecutive `OFF/SB` minutes |
| `V_FUEL_1000` | miles between fuelings ≤ 1,000 |
| `V_DAY_1440` | each daily log covers **exactly 1,440 minutes** |
| `V_OVERLAP` | no two segments overlap |
| `V_GAP` | no gaps in the timeline (contiguous, including the padding) |
| `V_INTEGER` | every segment boundary is an integer number of minutes |
| `V_STATUS` | valid status codes, positive durations, sorted order |

The validator runs in every test, in the property tests, and in production as a self-check: a failing self-check
is a **500 `plan_self_check_failed`** — we never return a plan we know is illegal. A `cycle_exhausted` plan is a legal
prefix and **must validate clean**.

## 11. Golden scenarios (test oracles, hand-computed)

Tests parameterise `mph = 50` (D-5) so every limit lands on whole minutes (11 h = 550 mi, 8 h = 400 mi, 1,000 mi = 20 h).
All times local, `hh:mm`. `allow_34_hour_restart = False` unless stated. S1–S3 have `status = complete`.

### S1 — single short day

Depart **06:00**, cycle **0**, leg 1 = **100 mi**, leg 2 = **200 mi**.

| Time | Status | Activity |
| --- | --- | --- |
| 00:00–06:00 | OFF | before departure |
| 06:00–06:15 | ON | pre-trip |
| 06:15–08:15 | D | 100 mi |
| 08:15–09:15 | ON | pickup |
| 09:15–13:15 | D | 200 mi |
| 13:15–14:15 | ON | drop-off |
| 14:15–24:00 | OFF | after trip |

Totals: **OFF 15.75 · SB 0 · D 6 · ON 2.25 = 24.00**. Miles 300. Recap: on-duty today 8.25, A = 8.25, B = 61.75. **No break inserted** (D-3).

### S2 — break after pickup; 11 h limit hit exactly at arrival

Depart **05:00**, cycle **0**, leg 1 = **50 mi**, leg 2 = **500 mi**.

| Time | Status | Activity |
| --- | --- | --- |
| 05:00–05:15 | ON | pre-trip |
| 05:15–06:15 | D | 50 mi |
| 06:15–07:15 | ON | pickup (resets break clock) |
| 07:15–15:15 | D | 400 mi (8 h) |
| 15:15–15:45 | OFF | 30-min break (HOS-4) |
| 15:45–17:45 | D | 100 mi → D total 11 h (HOS-2 exactly met) |
| 17:45–18:45 | ON | drop-off (window closes 19:00) |

Totals: **OFF 10.75 · SB 0 · D 11 · ON 2.25 = 24.00**. Miles 550.

### S3 — two days: 11 h limit, 10 h rest, fuel at 1,000 mi

Depart **06:00**, cycle **0**, leg 1 = **100 mi**, leg 2 = **1,000 mi** (route = 1,100 mi).

| Day | Time | Status | Activity |
| --- | --- | --- | --- |
| 1 | 06:00–06:15 | ON | pre-trip |
| 1 | 06:15–08:15 | D | 100 mi |
| 1 | 08:15–09:15 | ON | pickup |
| 1 | 09:15–17:15 | D | 400 mi (8 h) |
| 1 | 17:15–17:45 | OFF | 30-min break |
| 1 | 17:45–18:45 | D | 50 mi → D = 11 h |
| 1→2 | 18:45–04:45 | SB | 10 h rest (crosses midnight) |
| 2 | 04:45–05:00 | ON | pre-trip (new shift) |
| 2 | 05:00–13:00 | D | 400 mi → route mile 950 |
| 2 | 13:00–13:30 | OFF | 30-min break |
| 2 | 13:30–14:30 | D | 50 mi → route mile **1,000** |
| 2 | 14:30–15:00 | ON | **fuel** (FUEL-1; also resets break clock) |
| 2 | 15:00–17:00 | D | 100 mi → D = 11 h |
| 2 | 17:00–18:00 | ON | drop-off (window closes 18:45) |

Day 1: **OFF 6.5 · SB 5.25 · D 11 · ON 1.25 = 24**, miles 550.
Day 2: **OFF 6.5 · SB 4.75 · D 11 · ON 1.75 = 24**, miles 550. Trip cycle used: 25 h.

### S4 — cycle exhausted mid-route (default: **no restart**)

Depart **06:00**, cycle **60** (R = 600 min), leg 1 = **50 mi**, leg 2 = **800 mi**.

| Time | Status | Activity |
| --- | --- | --- |
| 00:00–06:00 | OFF | before departure |
| 06:00–06:15 | ON | pre-trip (R 600 → 585) |
| 06:15–07:15 | D | 50 mi (R → 525) |
| 07:15–08:15 | ON | pickup (R → 465) |
| 08:15–16:00 | D | 7.75 h = 387.5 mi, **capped by R** (R → 0) |
| 16:00–24:00 | OFF | after the last scheduled activity |

Result: **`status = cycle_exhausted`**, `blocked = drive`, stopped at route mile **437.5**, `pending = [dropoff]`,
`unplanned_miles = 412.5`, `shortfall_min = 495 + 60 = 555` (9.25 h). One daily log: **OFF 14 · ON 1.25 · D 8.75 = 24**,
on-duty today 10, **A = 70, B = 0**. `arrival_at = null`. **No restart segment. The plan validates clean.**

### S4b — same trip with the internal option `allow_34_hour_restart = True` (tests only)

At 16:00 the wall is hit and more driving is needed → restart.

| Day | Time | Status | Activity |
| --- | --- | --- | --- |
| 1 | 06:00–16:00 | — | identical to S4 |
| 1→3 | 16:00–02:00 | OFF | **34 h restart** (all of day 2 is OFF); cycle → 0 |
| 3 | 02:00–02:15 | ON | pre-trip |
| 3 | 02:15–10:15 | D | 8 h |
| 3 | 10:15–10:45 | OFF | 30-min break |
| 3 | 10:45–11:00 | D | 12.5 mi → arrive |
| 3 | 11:00–12:00 | ON | drop-off |

Day 1: OFF 14 · ON 1.25 · D 8.75 = 24 (A = 70, B = 0). Day 2: OFF 24 (A = 70, B = 0 — the restart completes at 02:00 next day).
Day 3: OFF 14.5 · ON 1.25 · D 8.25 = 24 (on-duty 9.5, **A = 9.5, B = 60.5**). `status = complete`, warning `cycle_restart_applied`. Miles 850, no fuel stop.

### S5 — almost no allowance

Depart **06:00**, legs 100 / 200 mi (as S1).

- **S5a — cycle 69.9 h** (4,194 min, R = 6): the pre-trip needs 15 → nothing fits. Day 1 = **OFF 24**. `cycle_exhausted`,
  `blocked = pretrip`, mile 0, `pending = [pickup, dropoff]`, `unplanned_miles = 300`, `shortfall_min = 360 + 60 + 60 − 6 = 474`.
- **S5b — cycle 69.7 h** (4,182 min, R = 18): ON 06:00–06:15 pre-trip (R → 3), **D 06:15–06:18** (2.5 mi, R → 0), OFF to 24:00.
  Totals **OFF 23.7 · ON 0.25 · D 0.05 = 24**. `cycle_exhausted`, `blocked = drive`, mile 2.5, `unplanned_miles = 297.5`,
  `shortfall_min = 357 + 120 − 0 = 477`.

### S6 — the drop-off does not fit (atomic activity, A-17)

Depart **06:00**, cycle **62** (R = 480), legs 100 / 200 mi.

| Time | Status | Activity | R after |
| --- | --- | --- | --- |
| 06:00–06:15 | ON | pre-trip | 465 |
| 06:15–08:15 | D | 100 mi | 345 |
| 08:15–09:15 | ON | pickup | 285 |
| 09:15–13:15 | D | 200 mi | 45 |
| 13:15–24:00 | OFF | drop-off needs 60 > 45 → **not performed** | — |

Result: `cycle_exhausted`, `blocked = dropoff`, mile 300, `pending = [dropoff]`, `unplanned_miles = 0`, `shortfall_min = 60 − 45 = 15`.
Totals **OFF 16.75 · ON 1.25 · D 6 = 24**; on-duty today 7.25, **A = 69.25, B = 0.75**.

### Boundary cases (each gets a test)

- **Cycle:** `cycle_used = 70` → nothing scheduled · `69.75` (R = 15) → pre-trip fits exactly, then `blocked = drive` ·
  `70.01` → 400 · `69.999` rounds to 4,200 min · exactly exhausted **by** the final drop-off → **`complete`** · drop-off with
  R = 59 → blocked, with R = 60 → complete · fuel due with R = 29 → blocked, R = 30 → fuel then wall · 11 h limit reached with
  R = 15 → `next_shift`, no rest · R = 16 → rest, pre-trip, 1 min of driving · each of these again with the restart option on → restart inserted.
- **30-minute interruption:** two separate 15-min stops **do not** satisfy HOS-4 · 15 min `ON` + 15 min `OFF` adjacent **do** ·
  a 60-min pickup, 30-min fuel stop and 60-min drop-off each reset the counter and **no `break` follows** · exactly 480 min
  driven then arrival at a stop · a 29-min `OFF` does not reset.
- **Reset and limits:** a 9 h 59 min `SB` **does not** reset · `SB` interrupted by `ON` does not reset · exactly 660 min driven ·
  exactly 1,000.0 mi.
- **Structure and inputs:** 0-mile leg 1 (pickup = current) · 0-mile leg 2 · segment ending exactly at 24:00 · departure at 23:50 ·
  every boundary an `int`.

### Property-based invariants (Hypothesis)

Random legs 0–3,000 mi, cycle 0–70, mph 45–65, arbitrary departure ⇒ for **every** plan (complete *or* truncated):

1. `validate(plan) == []`
2. segments are contiguous, sorted, integer-minute; the first starts at departure
3. Σ`D` miles == route miles when `complete`, and ≤ route miles when `cycle_exhausted` (± 1 min of rounding)
4. every daily log sums to 1,440 min; per-row totals equal the drawn segments
5. stop mileage is non-decreasing; ≥ 1 fuel stop per 1,000 planned miles
6. deterministic: same input → byte-identical output
7. metamorphic: shifting departure by +24 h shifts every timestamp by +24 h and changes nothing else
8. **cycle cap:** with the option off, scheduled on-duty minutes (`D + ON`) ≤ 4,200 − carry-in
9. **status consistency:** `complete` ⇔ drop-off performed ⇔ `stop is None`; `cycle_exhausted` ⇒ `shortfall_min ≥ 1`; no `restart` segment exists with the option off
10. **prefix property:** for `cycle_b ≥ cycle_a`, plan *b* is plan *a* cut at some minute (its last segment possibly shortened) and is never `complete` when *a* is not
11. **no redundant break:** every `break` starts exactly when `drive_since_break` reached 480

## 12. HOS correctness risks

| # | Risk | Mitigation |
| --- | --- | --- |
| 1 | HOS-4 mis-modelled as wall-clock or "consecutive driving"; redundant breaks after pickup/fuel/drop-off | §5 note (D-3), S1–S3, boundary tests, property 11, validator |
| 2 | HOS-3 mis-modelled as "14 h on duty" (pausing on breaks) | Non-pausing clock in §6; test with a 4 h pickup so it binds |
| 3 | 10 h reset counted with `ON` time inside it | HOS-1 counts `OFF/SB` only; boundary tests; `V_RESET_10` |
| 4 | Cycle counted for driving only, or a restart silently invented | D-1/D-2 in §3.1; `V_CYCLE_70`, `V_RESTART_34`; S4–S6; properties 8, 9 |
| 5 | Reviewer reads guide p.10 and objects that D-1 is stricter than the regulation | Documented as a deliberate, conservative rule (§5); README states it; it can never yield an illegal plan |
| 6 | A truncated (`cycle_exhausted`) plan is mistaken for a complete trip | `status`, warning, `arrival_at = null`, `unplanned` block, UI banner; API and component tests |
| 7 | Atomic / no-dangling-rest rules (A-17) produce surprising edge timelines | Goldens S5, S6; boundary list; flagged for your confirmation (§13) |
| 8 | Off-by-one at exact limits (`<` vs `≤`) | Boundary cases; limits expressed as "may not *start* a D minute when ≥ limit" |
| 9 | Floats leaking into decisions; miles/minutes drift | Rule M-1; integer-minute clock; floor/ceil convention §6; `V_INTEGER`; property 3 |
| 10 | Midnight / DST / time-zone day slicing | Fixed offset A-15; midnight boundary tests |
| 11 | Log totals disagree with drawing | Derive both from one segment list; `V_DAY_1440`; property 4 |
| 12 | Hidden dependence on "now" | Planner is pure; tests always pass explicit departure |
| 13 | Correlated bugs between planner and its tests | Independent minute-stepping validator (§10) + hand-computed goldens |
| 14 | Users read ETAs as authoritative | Speed assumption shown in UI; "planning estimate" footer |

## 13. Open items

All assumptions above were approved at G0 (decisions Q1–Q19 are recorded in `implementation-plan.md` §7.3). One item
remains open: the **Q7 clarification** — which recap box carries the 70 h / last-8-days total (§9.4).
