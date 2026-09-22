# Design system — HOS Route Planner

This is the visual source of truth for the frontend. It supersedes the palette described in
`CLAUDE.md`/`architecture.md` §5.6 (deep teal/coral/pale) — see "Relationship to project docs"
at the end. Everything here is deliberate; when in doubt, prefer this document over inventing a
new pattern.

## 1. Design philosophy

1. Information hierarchy over decoration.
2. Whitespace is a structural tool, not empty space to fill.
3. Borders and dividers before shadows.
4. A card is used only when a surface genuinely needs to be visually distinct — never as a default
   wrapper. Never nest a card inside a card.
5. Numbers are operational: large, scannable, not illustrated.
6. Status color always carries meaning (compliant / warning / violation) — never decorative.
7. Typography establishes hierarchy; size and weight do the work color otherwise would.
8. Dense operational data (tables, the log grid, the timeline) stays dense — legible, not padded
   out to look "clean."
9. Every visual element must justify its existence. If removing it loses nothing, remove it.

Reference points: Linear, the Stripe Dashboard, professional fleet/ops software. Not: generic
admin-dashboard templates, glassmorphism, gradients, Dribbble concepts.

## 2. Typography

**UI typeface: IBM Plex Sans.** **Tabular/numeric typeface: IBM Plex Mono.** Both loaded from
Google Fonts (OFL-licensed, already CDN-hosted — no new npm dependency).

Considered and rejected:
- **Manrope** — friendly/geometric, reads more "startup marketing site" than "operational
  console," and has no true matched monospace sibling (metrics wouldn't line up with the sans).
- **Geist** — excellent, but is Vercel's own distributed typeface (not on Google Fonts; needs an
  npm package or a non-standard CDN) and is strongly identified with Vercel's own brand — this
  product should have its own identity, not visually cite Vercel's.
- **IBM Plex Sans (chosen)** — designed by IBM specifically for dense enterprise software and
  data-heavy interfaces, excellent number legibility (tabular figures), a genuinely matched Mono
  sibling with consistent x-height/metrics, professional without being the ubiquitous "Inter
  everywhere" look.

`--font-sans: 'IBM Plex Sans', -apple-system, sans-serif` — all UI text.
`--font-mono: 'IBM Plex Mono', ui-monospace, monospace` — timestamps, mile/hour figures inside
tables and the log grid, route coordinates. Never used for body copy or labels.

### Scale (Tailwind v4 `--text-*` tokens; size / line-height / weight)

| Token | Size | Line height | Weight | Use |
| --- | --- | --- | --- | --- |
| `text-display` | 1.5rem / 24px | 1.25 | 600 | App name in header only |
| `text-section` | 1.0625rem / 17px | 1.3 | 600 | Section titles: "Trip planner", "Route", "Daily logs", "Compliance" |
| `text-body` | 0.9375rem / 15px | 1.5 | 400 | Default paragraph/value text |
| `text-label` | 0.8125rem / 13px | 1.3 | 500 | Form labels, table headers, metric captions — muted color, never uppercase-by-default (see §10) |
| `text-caption` | 0.75rem / 12px | 1.4 | 400 | Supporting/secondary text, hints, timestamps in the timeline |
| `text-metric` | 1.75rem / 28px | 1.1 | 600 | The big scannable numbers in the trip summary strip |

Numeric values inside tables, the recap block, and the log grid use `font-mono` at `text-body` or
`text-caption` size with `font-variant-numeric: tabular-nums` (via `tabular-nums` class) so columns
align.

## 3. Color tokens

Neutral-first system with one restrained accent. All defined as Tailwind v4 `@theme` tokens in
`src/index.css`.

| Token | Value | Use |
| --- | --- | --- |
| `--color-bg` | `#f7f8fa` | App background |
| `--color-surface` | `#ffffff` | Cards, panels, the header, popovers |
| `--color-surface-muted` | `#fafbfc` | Table stripe, subtle inset panels |
| `--color-ink` | `#14181f` | Primary text |
| `--color-ink-secondary` | `#5b6472` | Secondary text, descriptions |
| `--color-ink-tertiary` | `#8b93a1` | Captions, placeholders, disabled |
| `--color-border` | `#e3e6ea` | Default 1px divider/border |
| `--color-border-strong` | `#cdd2d9` | Emphasis divider (rare) |
| `--color-accent` | `#1d4ed8` | Primary actions, links, focus ring, selected state |
| `--color-accent-hover` | `#1e40af` | Accent hover/active |
| `--color-accent-tint` | `#eef2ff` | Accent-tinted background (selected row, subtle highlight) |
| `--color-success` | `#16a34a` | Compliant / on-time |
| `--color-success-tint` | `#f0fdf4` | Success background |
| `--color-warning` | `#d97706` | Approaching a limit |
| `--color-warning-tint` | `#fffbeb` | Warning background |
| `--color-danger` | `#dc2626` | Violation / error |
| `--color-danger-tint` | `#fef2f2` | Danger background |

Rules: no gradients, no second decorative accent. Coral is retired as a CTA color entirely.
Semantic colors are reserved for compliance/status meaning — never used decoratively elsewhere
(e.g. a random icon is not tinted green just because it's near other green things).

## 4. Spacing

No new spacing scale — Tailwind v4's default 4px-based scale is used with discipline. Primary
steps in practice: `2, 3, 4, 6, 8, 12, 16, 24` (0.5rem–6rem). Section-level gaps use the larger end
(`12`–`16`, i.e. 3–4rem between major sections); dense operational data (table rows, timeline
entries, log-grid remarks) uses the smaller end (`2`–`4`). Padding is not increased just to "look
clean" — see philosophy §2.

## 5. Radius, border, shadow

| Token | Value | Use |
| --- | --- | --- |
| `--radius-sm` | 6px | Inputs, buttons, tags |
| `--radius-md` | 8px | Cards, the map container, popovers |
| `--radius-lg` | 12px | Reserved — used only for the map container currently |

Borders: `1px solid var(--color-border)` is the default way to separate content. Shadows are used
in exactly one place by default — floating surfaces that sit above content (the typeahead
suggestion list, the day-tab overflow if any) — `--shadow-sm: 0 1px 2px rgba(16,24,40,.06), 0 2px
6px rgba(16,24,40,.08)`. Cards do not carry a shadow; they're distinguished by
`var(--color-surface)` + a 1px border only.

## 6. Components

- **Button** — primary (accent fill), secondary (border, no fill), ghost (no border, text only).
  `radius-sm`, no shadow, `text-body` weight 500.
- **Input / Combobox** — `radius-sm`, 1px border, focus ring in `--color-accent`. The typeahead
  suggestion list is the one place using `--shadow-sm`, since it must visually float above the
  page. **Behavior is untouched** — `LocationCombobox`'s `useCombobox` call keeps
  `initialInputValue` (never `inputValue`) exactly as fixed in Phase 5; only class names change.
- **Tag** (replaces most `Badge` pill usage) — `radius-sm` rectangle, not a full pill, small caps
  off, 1px border or tint background matching its semantic color. A true pill is not used anywhere
  by default.
- **Table** — 1px row dividers (`--color-border`), no cell borders, numeric columns right-aligned
  and `font-mono tabular-nums`, header row `text-label` muted, `--color-surface-muted` stripe only
  if a table is long enough to need it (daily summary does not need it at 2 rows).
- **Timeline** (`StopsTimeline`) — thin connecting line, small status-colored dot markers, no
  boxes around entries. Location name at `text-body` weight 600, event type as a small `Tag`, time
  and duration as `text-caption` in `--color-ink-secondary`.
- **Compliance row** — icon + rule name + state. Default/compliant state is quiet: a small check
  in `--color-success`, no colored background, no border. Only a genuine warning or violation gets
  a tinted background and stronger visual weight.

## 7. Status semantics

`success` (green) = compliant / on schedule. `warning` (amber) = approaching a limit, not yet
violated. `danger` (red) = an actual violation (`summary.status === "cycle_exhausted"`, or a
specific HOS rule breached). Color is never the only signal — every status also has text and,
where relevant, an icon (never color-only communication, per accessibility rules).

## 8. Map treatment

Leaflet/react-leaflet unchanged. The map sits in a `radius-lg` container with a 1px border, no
card padding around the map itself (the map fills its container edge-to-edge). Markers use the
same semantic-color set as the rest of the app (start = ink, pickup/dropoff = accent, fuel/break =
ink-secondary, rest = accent, cycle_limit = danger) instead of the previous arbitrary marker
palette.

## 9. Responsive rules

Breakpoints: 1440px+ (design target), 1280px, 1024px, 768px, 390px.

- **≥1024px**: two-column route workspace (map | timeline), 4-column trip-summary metric strip,
  form fields in a 2-column grid.
- **768–1023px**: route workspace compresses to a shorter two-column layout or stacks (map above
  timeline) depending on available width; metric strip reflows to 2 columns.
- **<768px**: single column throughout. Map above timeline. Trip-form fields stack vertically.
  Metric strip reflows to 2 columns, then 1 at the narrowest. Tables get horizontal scroll only if
  content genuinely overflows (daily summary at 2 days does not). Nav collapses to a compact
  control. All interactive targets stay ≥44px touch height.

## 10. Accessibility rules

Semantic HTML first (`<nav>`, `<table>`, `<dl>`, headings in order). Every input keeps its label
association. Visible focus ring in `--color-accent` on every interactive element — never
`outline: none` without a replacement. Color always paired with text/icon. Contrast: body text on
`--color-bg`/`--color-surface` and all semantic colors are checked against WCAG AA (4.5:1 normal
text, 3:1 large text/UI components). Labels are not forced to uppercase by default — that's a
decorative pattern that hurts legibility and isn't required for hierarchy here (`text-label`'s
weight/size/color already establish it).

## 11. Forbidden patterns

Gradients (decorative), glassmorphism, neumorphism, giant rounded cards, heavy/multiple shadows,
pill badges as the default tag shape, rainbow/multi-accent color systems, oversized hero
typography, fake KPI charts, decorative illustrations/blobs, icons added purely for decoration,
excessive or hover-everywhere animation, unnecessary dark mode, a sidebar (none is needed here),
fake routes/navigation, uppercase labels by default, cards nested inside cards.

## Relationship to project docs

`CLAUDE.md`'s Conventions section and `architecture.md` §5.6 describe an earlier palette (deep
teal `#043d4c` / coral `#f84960` / teal `#008080` / pale `#bcddde`, sourced from the assessment
docx's letterhead). This document replaces that palette per explicit direction in this phase of
work. `CLAUDE.md` and `architecture.md` §5.6 are updated alongside this file so they no longer
contradict it.
