"""uvicorn apps.research_platform.backend.main:app --host 127.0.0.1 --port 8000"""

from .app import create_app

app = create_app()
