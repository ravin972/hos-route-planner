import { http, HttpResponse } from 'msw'
import s1 from './fixtures/s1-complete.json'

const SUGGESTIONS = [
  { label: 'Chicago, Illinois', lat: 41.8756, lng: -87.6244 },
  { label: 'Chicago Heights, Illinois', lat: 41.5061, lng: -87.6353 },
  { label: 'St. Louis, Missouri', lat: 38.6274, lng: -90.1982 },
]

export const handlers = [
  http.post('/api/trips/plan', () => HttpResponse.json(s1)),
  http.get('/api/locations/search', ({ request }) => {
    const url = new URL(request.url)
    const q = (url.searchParams.get('q') ?? '').toLowerCase()
    if (!q) return HttpResponse.json({ results: [] })
    return HttpResponse.json({
      results: SUGGESTIONS.filter((s) => s.label.toLowerCase().includes(q)),
    })
  }),
]
