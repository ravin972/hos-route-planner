import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { searchLocations } from '../lib/api'
import { LOCATION_SEARCH_DEBOUNCE_MS, LOCATION_SEARCH_MIN_CHARS } from '../lib/constants'
import { useDebouncedValue } from './useDebouncedValue'

export function useLocationSearch(query: string) {
  const debounced = useDebouncedValue(query.trim(), LOCATION_SEARCH_DEBOUNCE_MS)
  const enabled = debounced.length >= LOCATION_SEARCH_MIN_CHARS

  const result = useQuery({
    queryKey: ['locations-search', debounced],
    queryFn: () => searchLocations(debounced, 5),
    enabled,
    placeholderData: keepPreviousData,
    staleTime: 60_000,
  })

  return { ...result, suggestions: result.data?.results ?? [], enabled }
}
