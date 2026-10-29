from datetime import datetime

from bson import ObjectId
from pymongo import ReturnDocument
from pymongo.asynchronous.client_session import AsyncClientSession
from pymongo.asynchronous.database import AsyncDatabase
from pymongo.errors import DuplicateKeyError


class CorreoYaRegistrado(Exception):
    pass


class RepositorioUsuarios:
    def __init__(self, db: AsyncDatabase):
        self._coleccion = db["usuarios"]

    async def insertar(self, usuario: dict, sesion: AsyncClientSession | None = None) -> ObjectId:
        """Inserta el usuario. El índice único sobre `correo` evita duplicados aun con altas simultáneas."""
        try:
            resultado = await self._coleccion.insert_one(usuario, session=sesion)
        except DuplicateKeyError as error:
            raise CorreoYaRegistrado from error
        return resultado.inserted_id

    async def buscar_por_correo(self, correo: str) -> dict | None:
        return await self._coleccion.find_one({"correo": correo})

    async def sumar_intento_fallido(self, usuario_id: ObjectId) -> int:
        """Suma un intento fallido de forma atómica y devuelve el total acumulado."""
        usuario = await self._coleccion.find_one_and_update(
            {"_id": usuario_id},
            {"$inc": {"intentos_login_fallidos": 1}},
            projection={"intentos_login_fallidos": 1},
            return_document=ReturnDocument.AFTER,
        )
        return usuario["intentos_login_fallidos"]

    async def bloquear(self, usuario_id: ObjectId, hasta: datetime) -> None:
        await self._coleccion.update_one(
            {"_id": usuario_id},
            {"$set": {"bloqueado_hasta": hasta, "intentos_login_fallidos": 0}},
        )

    async def cambiar_contrasena(
        self, usuario_id: ObjectId, contrasena_hash: str, sesion: AsyncClientSession | None = None
    ) -> None:
        """Nueva contraseña (HU-015). También levanta el bloqueo por intentos fallidos."""
        await self._coleccion.update_one(
            {"_id": usuario_id},
            {"$set": {"contrasena_hash": contrasena_hash, "bloqueado_hasta": None, "intentos_login_fallidos": 0}},
            session=sesion,
        )

    async def reiniciar_intentos(self, usuario_id: ObjectId) -> None:
        await self._coleccion.update_one(
            {"_id": usuario_id},
            {"$set": {"bloqueado_hasta": None, "intentos_login_fallidos": 0}},
        )
