from pymongo.errors import ServerSelectionTimeoutError

from app.core.config import obtener_settings
from app.core.db import obtener_db
from app.main import app


class BaseFalsa:
    """Reemplaza a la base: responde el ping o falla como si no hubiera servidor."""

    def __init__(self, disponible: bool):
        self.disponible = disponible

    async def command(self, nombre: str):
        if not self.disponible:
            raise ServerSelectionTimeoutError("No hay servidores disponibles")
        return {"ok": 1}


def test_salud_con_base_disponible(cliente):
    app.dependency_overrides[obtener_db] = lambda: BaseFalsa(disponible=True)

    respuesta = cliente.get("/api/salud")

    assert respuesta.status_code == 200
    assert respuesta.json() == {"api": "ok", "base_de_datos": "ok"}


def test_salud_sin_base(cliente):
    app.dependency_overrides[obtener_db] = lambda: BaseFalsa(disponible=False)

    respuesta = cliente.get("/api/salud")

    assert respuesta.status_code == 503
    assert respuesta.json() == {"api": "ok", "base_de_datos": "sin_conexion"}


def test_cors_solo_permite_el_frontend(cliente):
    frontend = obtener_settings().frontend_url
    preflight = {"Access-Control-Request-Method": "GET"}

    permitido = cliente.options("/api/salud", headers={"Origin": frontend, **preflight})
    rechazado = cliente.options(
        "/api/salud", headers={"Origin": "https://otro-sitio.com", **preflight}
    )

    assert permitido.headers.get("access-control-allow-origin") == frontend
    assert "access-control-allow-origin" not in rechazado.headers
