import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, type RenderResult } from '@testing-library/react'
import type { ReactElement } from 'react'

/** Any component using TanStack Query hooks (usePlanTrip, useLocationSearch) needs a
 * QueryClientProvider ancestor -- this wraps `render` with a fresh, retry-disabled client per
 * call so tests don't share cache state or wait out retry backoff. */
export function renderWithProviders(ui: ReactElement): RenderResult {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>)
}
