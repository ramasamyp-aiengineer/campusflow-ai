import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

DB_PATH = Path(__file__).resolve().parent / "tmp_test.db"
for extra in (DB_PATH, Path(str(DB_PATH) + "-wal"), Path(str(DB_PATH) + "-shm")):
    if extra.exists():
        extra.unlink()

os.environ["DATABASE_URL"] = f"sqlite:///{DB_PATH.as_posix()}"
os.environ["GEMINI_API_KEY"] = ""
os.environ["ALLOW_PERSONA_HEADER"] = "true"
os.environ["DEMO_PASSWORD"] = "test-demo-pass"

from app.main import app  # noqa: E402


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as test_client:
        yield test_client
