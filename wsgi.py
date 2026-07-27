"""Production WSGI entrypoint."""

from backend.blotguard import create_app


app = create_app()
