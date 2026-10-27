from datetime import datetime

from bson import ObjectId
from pymongo.asynchronous.client_session import AsyncClientSession
from pymongo.asynchronous.database import AsyncDatabase
from pymongo.errors import DuplicateKeyError

from app.modelos.taller import EstadoSolicitud


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

    async def buscar(self, taller_id: ObjectId) -> dict | None:
        return await self._coleccion.find_one({"_id": taller_id})

    async def listar_con_responsable(self, estado: EstadoSolicitud) -> list[dict]:
        """Solicitudes en ese estado, de la más reciente a la más antigua, con los datos de su usuario."""
        cursor = await self._coleccion.aggregate([
            {"$match": {"estado_solicitud": estado.value}},
            {"$sort": {"fecha_solicitud": -1}},
            {"$lookup": {
                "from": "usuarios",
                "localField": "usuario_id",
                "foreignField": "_id",
                "as": "responsable",
                "pipeline": [{"$project": {"nombre": 1, "apellido": 1, "correo": 1}}],
            }},
            {"$unwind": "$responsable"},
        ])
        return await cursor.to_list()

    async def resolver_pendiente(
        self,
        taller_id: ObjectId,
        estado: EstadoSolicitud,
        fecha: datetime,
        aprobado_por: ObjectId | None = None,
        motivo_rechazo: str | None = None,
    ) -> bool:
        """Aprueba o rechaza la solicitud solo si sigue pendiente. Devuelve False si no lo estaba."""
        resultado = await self._coleccion.update_one(
            {"_id": taller_id, "estado_solicitud": EstadoSolicitud.PENDIENTE.value},
            {"$set": {
                "estado_solicitud": estado.value,
                "motivo_rechazo": motivo_rechazo,
                "aprobado_por": aprobado_por,
                "fecha_resolucion": fecha,
            }},
        )
        return resultado.modified_count == 1
