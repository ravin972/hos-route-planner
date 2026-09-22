"""The HOS engine (Phase 1): pure Python, standard library only.

No Django, no DRF, no HTTP client, no OpenRouteService or any other external API, and no import of
another ``trips`` package. Every duration and limit is an integer number of minutes. Enforced by
``trips/tests/test_architecture.py``.
"""
