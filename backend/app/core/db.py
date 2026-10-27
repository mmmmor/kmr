from pymongo import AsyncMongoClient
from pymongo.asynchronous.database import AsyncDatabase

from app.core.config import obtener_settings

_cliente: AsyncMongoClient | None = None


def conectar() -> None:
    global _cliente
    _cliente = AsyncMongoClient(
        obtener_settings().mongodb_uri,
        serverSelectionTimeoutMS=5000,
        tz_aware=True,
    )


async def cerrar() -> None:
    global _cliente
    if _cliente is not None:
        await _cliente.close()
        _cliente = None


def obtener_db() -> AsyncDatabase:
    """Dependencia de FastAPI que devuelve la base de la aplicación."""
    if _cliente is None:
        raise RuntimeError("El cliente de MongoDB no fue inicializado.")
    return _cliente[obtener_settings().mongodb_db]
