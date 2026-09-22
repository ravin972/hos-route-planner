"""DRF throttle scopes (architecture.md section 4.5: ``THROTTLE_PLAN`` / ``THROTTLE_SEARCH``).

No auth exists (AD-1), so every client is anonymous -- rate-limited by IP, the only identity DRF
has to work with here.
"""

from rest_framework.throttling import AnonRateThrottle


class PlanRateThrottle(AnonRateThrottle):
    scope = "plan"


class SearchRateThrottle(AnonRateThrottle):
    scope = "search"
