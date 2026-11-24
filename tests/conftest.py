import os

os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"
os.environ["JWT_SECRET"] = "test-secret-with-at-least-32-bytes"
os.environ["REDIS_URL"] = ""
os.environ["SENTRY_DSN"] = ""

import pytest
from fastapi.testclient import TestClient

from app.cache import cache
from app.config import get_settings
from app.db import Base, engine
from app.main import app

get_settings.cache_clear()


@pytest.fixture()
def client():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    cache.clear()
    with TestClient(app) as test_client:
        yield test_client


def auth(client: TestClient, email: str, name: str = "Ada") -> dict:
    response = client.post("/auth/register", json={"email": email, "name": name, "password": "correct-horse"})
    assert response.status_code == 201, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}
