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


async def crear_indices(db: AsyncDatabase) -> None:
    """Crea los índices del modelo de datos (si ya existen, no hace nada)."""
    await db["usuarios"].create_index("correo", unique=True)
    await db["talleres"].create_index("usuario_id", unique=True)
    await db["talleres"].create_index("cuit", unique=True)
    await db["vehiculos"].create_index("dominio", unique=True)
    await db["vehiculos"].create_index("propietario_id")


async def en_transaccion(funcion):
    """Ejecuta `funcion(sesion)` en una transacción: se aplican todas sus escrituras o ninguna."""
    async with _cliente.start_session() as sesion:
        return await sesion.with_transaction(funcion)


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
