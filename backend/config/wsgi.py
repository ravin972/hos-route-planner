"""WSGI entrypoint. Vercel's Python runtime discovers it through settings.WSGI_APPLICATION."""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

application = get_wsgi_application()
