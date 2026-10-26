import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def cliente():
    # Sin "with" no corre el lifespan: los tests no abren una conexión real a MongoDB.
    yield TestClient(app)
    app.dependency_overrides.clear()
