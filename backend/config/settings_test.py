"""Settings for the test run (pytest points DJANGO_SETTINGS_MODULE here; see pyproject.toml).

The production settings refuse to start without DJANGO_SECRET_KEY unless DJANGO_DEBUG is
true. Tests opt into debug mode explicitly instead of depending on the developer's shell.
test_settings.py imports ``config.settings`` directly, so the production rules stay tested.
"""

import os

os.environ.setdefault("DJANGO_DEBUG", "true")

from .settings import *  # noqa: E402, F403
