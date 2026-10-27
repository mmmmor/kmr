from bson import ObjectId
from pymongo.asynchronous.database import AsyncDatabase


class RepositorioTalleres:
    def __init__(self, db: AsyncDatabase):
        self._coleccion = db["talleres"]

    async def buscar_por_usuario(self, usuario_id: ObjectId) -> dict | None:
        return await self._coleccion.find_one({"usuario_id": usuario_id})
