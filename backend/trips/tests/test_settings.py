"""Settings must be safe by default and importable the way Vercel imports them.

That means no database, and importing cleanly with no backend/.env file present (config/settings.py
loads one if it exists, for local-dev convenience, but must not require it).
"""

import os
import subprocess
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[2]

_PROBE = (
    "import os; os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'; "
    "import django; django.setup(); "
    "from django.conf import settings; "
    "print(settings.DEBUG, settings.DATABASES, settings.INSTALLED_APPS)"
)


def _run_probe(**env: str) -> subprocess.CompletedProcess[str]:
    """Import the settings in a clean interpreter that sees ONLY the given DJANGO_* variables."""
    clean_env = {k: v for k, v in os.environ.items() if not k.startswith("DJANGO_")}
    clean_env.update(env)
    return subprocess.run(
        [sys.executable, "-c", _PROBE],
        cwd=BACKEND_DIR,
        env=clean_env,
        capture_output=True,
        text=True,
        check=False,
    )


def test_production_settings_import_with_no_database() -> None:
    result = _run_probe(DJANGO_SECRET_KEY="test-secret", DJANGO_DEBUG="false")

    assert result.returncode == 0, result.stderr
    assert result.stdout.startswith("False {}"), result.stdout  # debug off, no databases


def test_missing_secret_key_is_refused_outside_debug() -> None:
    result = _run_probe(DJANGO_DEBUG="false")

    assert result.returncode != 0
    assert "DJANGO_SECRET_KEY" in result.stderr


def test_debug_mode_falls_back_to_a_development_key() -> None:
    result = _run_probe(DJANGO_DEBUG="true")

    assert result.returncode == 0, result.stderr
    assert result.stdout.startswith("True {}"), result.stdout
