import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { lazy, Suspense } from 'react'
import { AppShell } from './components/layout/AppShell'
import { Alert } from './components/ui/Alert'
import { Skeleton } from './components/ui/Skeleton'
import { Compliance } from './features/compliance/Compliance'
import { DayTabs } from './features/daily-logs/DayTabs'
import { LogSheet } from './features/daily-logs/LogSheet'
import { RouteInstructions } from './features/stops/RouteInstructions'
import { StopsTimeline } from './features/stops/StopsTimeline'
import { DailySummaryTable } from './features/summary/DailySummaryTable'
import { TripSummary } from './features/summary/TripSummary'
import { TripForm } from './features/trip-form/TripForm'
import { usePlanTrip } from './hooks/usePlanTrip'
import { AppError } from './lib/api'

// Map + Leaflet code-split into its own chunk (architecture.md section 5.5/5.7).
const RouteMap = lazy(() =>
  import('./features/route-map/RouteMap').then((module) => ({ default: module.RouteMap })),
)

const queryClient = new QueryClient()

function errorCopy(error: Error): string {
  if (!(error instanceof AppError)) return error.message
  switch (error.code) {
    case 'unroutable':
      return `${error.message} Try different pickup or drop-off locations.`
    case 'out_of_coverage':
      return `${error.message} Try locations closer together, inside the contiguous US.`
    case 'throttled':
      return 'Too many requests right now. Please try again in a moment.'
    case 'upstream_timeout':
    case 'upstream_error':
      return `${error.message} Please try again.`
    default:
      return error.message
  }
}

function TripPlanner() {
  const planMutation = usePlanTrip()

  return (
    <div className="space-y-10">
      <section id="trip-planner">
        <h2 className="text-section mb-4 text-ink">Plan a trip</h2>
        <TripForm
          onSubmit={(payload) => planMutation.mutate(payload)}
          isSubmitting={planMutation.isPending}
        />
      </section>

      {planMutation.isPending && (
        <div className="space-y-3" aria-busy="true" aria-live="polite">
          <span className="sr-only">Planning your trip&hellip;</span>
          <Skeleton className="h-24 w-full" />
          <Skeleton className="h-96 w-full" />
        </div>
      )}

      {planMutation.isError && (
        <Alert
          variant="error"
          title="Could not plan this trip"
          action={
            <button
              type="button"
              onClick={() => planMutation.reset()}
              className="text-body font-medium text-accent underline hover:text-accent-hover"
            >
              Dismiss and try again
            </button>
          }
        >
          <p>{errorCopy(planMutation.error)}</p>
          {planMutation.error instanceof AppError && planMutation.error.fields && (
            <ul className="list-disc pl-5">
              {Object.entries(planMutation.error.fields).map(([field, messages]) => (
                <li key={field}>
                  <strong>{field}:</strong>{' '}
                  {Array.isArray(messages) ? messages.join(', ') : String(messages)}
                </li>
              ))}
            </ul>
          )}
        </Alert>
      )}

      {planMutation.isSuccess && (
        <>
          <section aria-label="Trip summary">
            <TripSummary
              summary={planMutation.data.summary}
              warnings={planMutation.data.warnings}
            />
          </section>

          <section id="route" className="space-y-4">
            <h2 className="text-section text-ink">Route</h2>
            <div className="grid gap-4 lg:grid-cols-2">
              <Suspense fallback={<Skeleton className="h-[420px] w-full" />}>
                <RouteMap route={planMutation.data.route} stops={planMutation.data.stops} />
              </Suspense>
              <div className="space-y-4">
                <StopsTimeline stops={planMutation.data.stops} />
                <RouteInstructions legs={planMutation.data.route.legs} />
              </div>
            </div>
          </section>

          <section id="daily-logs" className="space-y-4">
            <h2 className="text-section text-ink">Daily logs</h2>
            <DayTabs days={planMutation.data.daily_logs}>{(day) => <LogSheet day={day} />}</DayTabs>
          </section>

          <section className="space-y-4">
            <h2 className="text-section text-ink">Daily summary</h2>
            <DailySummaryTable days={planMutation.data.daily_logs} />
          </section>

          <section id="compliance" className="space-y-4">
            <h2 className="text-section text-ink">Compliance</h2>
            <Compliance summary={planMutation.data.summary} warnings={planMutation.data.warnings} />
          </section>
        </>
      )}

      {planMutation.isIdle && (
        <p className="text-body text-ink-tertiary">
          Fill in the form above and plan a trip to see the route, stops and daily logs.
        </p>
      )}
    </div>
  )
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AppShell>
        <TripPlanner />
      </AppShell>
    </QueryClientProvider>
  )
}
