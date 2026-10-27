from bson import ObjectId
from pymongo.asynchronous.client_session import AsyncClientSession
from pymongo.asynchronous.database import AsyncDatabase
from pymongo.errors import DuplicateKeyError


class CuitYaRegistrado(Exception):
    pass


class RepositorioTalleres:
    def __init__(self, db: AsyncDatabase):
        self._coleccion = db["talleres"]

    async def insertar(self, taller: dict, sesion: AsyncClientSession | None = None) -> ObjectId:
        """Inserta el taller. El índice único sobre `cuit` evita solicitudes duplicadas."""
        try:
            resultado = await self._coleccion.insert_one(taller, session=sesion)
        except DuplicateKeyError as error:
            raise CuitYaRegistrado from error
        return resultado.inserted_id

    async def buscar_por_usuario(self, usuario_id: ObjectId) -> dict | None:
        return await self._coleccion.find_one({"usuario_id": usuario_id})
