from datetime import datetime

from pymongo.asynchronous.client_session import AsyncClientSession
from pymongo.asynchronous.database import AsyncDatabase


class RepositorioTokensRecuperacion:
    """Acceso a `tokens_recuperacion`. Solo se guarda el hash del token, nunca el token."""

    def __init__(self, db: AsyncDatabase):
        self._coleccion = db["tokens_recuperacion"]

    async def insertar(self, token: dict) -> None:
        await self._coleccion.insert_one(token)

    async def invalidar_vigentes(self, usuario_id) -> None:
        """Al pedir un enlace nuevo, los anteriores de la misma cuenta dejan de servir."""
        await self._coleccion.update_many({"usuario_id": usuario_id, "utilizado": False}, {"$set": {"utilizado": True}})

    async def consumir(self, token_hash: str, ahora: datetime, sesion: AsyncClientSession | None = None) -> dict | None:
        """Marca el token como utilizado si existe, no se usó y no venció, de forma atómica.

        Devuelve el token, o None si no sirve: dos pedidos simultáneos con el mismo enlace no
        pueden usarlo los dos.
        """
        return await self._coleccion.find_one_and_update(
            {"token_hash": token_hash, "utilizado": False, "fecha_vencimiento": {"$gt": ahora}},
            {"$set": {"utilizado": True}},
            session=sesion,
        )
