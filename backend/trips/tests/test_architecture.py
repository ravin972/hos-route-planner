"""Architecture rules enforced as tests (architecture.md AD-2 and section 4.1, decision D-7).

* ``trips.hos`` is the pure HOS engine: it may import the standard library and itself, nothing else
  (no Django, no DRF, no HTTP client, no OpenRouteService, no other ``trips`` package).
* ``trips.routing`` (provider adapters) must never import ``trips.hos``.

The checkers are tested on synthetic source first, so the real rules cannot pass vacuously while the
packages are still nearly empty.
"""

import ast
import sys
from pathlib import Path

TRIPS_DIR = Path(__file__).resolve().parents[1]
STDLIB = frozenset(sys.stdlib_module_names)


def imported_modules(source: str) -> set[str]:
    """Absolute module names imported by ``source``; ``from a import b`` also yields ``a.b``."""
    found: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            found.add(node.module)
            found.update(f"{node.module}.{alias.name}" for alias in node.names)
    return found


def _is_inside(name: str, package: str) -> bool:
    return name == package or name.startswith(f"{package}.")


def hos_violations(source: str) -> list[str]:
    """Imports that are neither standard library nor inside ``trips.hos`` itself."""
    return sorted(
        name
        for name in imported_modules(source)
        if name.split(".")[0] not in STDLIB and not _is_inside(name, "trips.hos")
    )


def routing_violations(source: str) -> list[str]:
    """Imports of ``trips.hos`` from routing code."""
    return sorted(name for name in imported_modules(source) if _is_inside(name, "trips.hos"))


def _python_files(package: str) -> list[Path]:
    return sorted((TRIPS_DIR / package).rglob("*.py"))


# --- the checkers themselves -------------------------------------------------------------------


def test_hos_checker_flags_third_party_and_sibling_imports() -> None:
    source = "import django\nimport requests\nfrom trips.routing import base\nimport json\n"

    assert hos_violations(source) == ["django", "requests", "trips.routing", "trips.routing.base"]


def test_hos_checker_allows_stdlib_relative_and_own_package_imports() -> None:
    source = (
        "from __future__ import annotations\n"
        "import datetime\n"
        "from dataclasses import dataclass\n"
        "from . import constants\n"
        "from .types import Segment\n"
        "from trips.hos import planner\n"
    )

    assert hos_violations(source) == []


def test_routing_checker_flags_hos_imports() -> None:
    source = "from trips.hos import planner\nimport trips.hos.validator\nimport requests\n"

    assert routing_violations(source) == ["trips.hos", "trips.hos.planner", "trips.hos.validator"]


def test_routing_checker_allows_other_imports() -> None:
    assert routing_violations("import requests\nfrom trips.routing import base\n") == []


# --- the real rules ----------------------------------------------------------------------------


def test_the_packages_under_test_exist() -> None:
    assert _python_files("hos"), "trips/hos is missing"
    assert _python_files("routing"), "trips/routing is missing"


def test_hos_package_is_pure_python_stdlib_only() -> None:
    offenders = {
        str(path.relative_to(TRIPS_DIR)): hos_violations(path.read_text(encoding="utf-8"))
        for path in _python_files("hos")
    }

    assert {file: bad for file, bad in offenders.items() if bad} == {}


def test_routing_package_never_imports_the_hos_engine() -> None:
    offenders = {
        str(path.relative_to(TRIPS_DIR)): routing_violations(path.read_text(encoding="utf-8"))
        for path in _python_files("routing")
    }

    assert {file: bad for file, bad in offenders.items() if bad} == {}
