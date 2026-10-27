import os

# Clave solo para tests; tiene que estar definida antes de importar la app.
os.environ["JWT_SECRET"] = "clave-de-prueba-que-no-se-usa-en-ningun-entorno-real"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


@pytest.fixture
def cliente():
    # Sin "with" no corre el lifespan: los tests no abren una conexión real a MongoDB.
    yield TestClient(app)
    app.dependency_overrides.clear()
