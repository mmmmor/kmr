from bson import ObjectId
from pymongo.asynchronous.client_session import AsyncClientSession
from pymongo.asynchronous.database import AsyncDatabase
from pymongo.errors import DuplicateKeyError


class CadenaModificada(Exception):
    """Otro registro del mismo vehículo ya encadenó sobre ese hash_anterior: hay que recalcular."""


class RepositorioIntervenciones:
    """Acceso a `intervenciones`. Solo inserción y consultas: un registro nunca se modifica ni se elimina."""

    def __init__(self, db: AsyncDatabase):
        self._coleccion = db["intervenciones"]

    async def insertar(self, intervencion: dict, sesion: AsyncClientSession | None = None) -> ObjectId:
        """Inserta al final de la cadena del vehículo.

        El índice único (vehiculo_id, hash_anterior) rechaza un segundo registro sobre el mismo
        anterior, como pasaría con dos cargas simultáneas: en ese caso lanza CadenaModificada.
        """
        try:
            resultado = await self._coleccion.insert_one(intervencion, session=sesion)
        except DuplicateKeyError as error:
            raise CadenaModificada from error
        return resultado.inserted_id

    async def buscar(self, intervencion_id: ObjectId) -> dict | None:
        return await self._coleccion.find_one({"_id": intervencion_id})

    async def ultima_registrada(self, vehiculo_id: ObjectId, sesion: AsyncClientSession | None = None) -> dict | None:
        """El último registro del vehículo según fecha_registro: el que cierra su cadena de hash.

        El _id desempata dos registros del mismo milisegundo (crece con cada inserción).
        """
        return await self._coleccion.find_one(
            {"vehiculo_id": vehiculo_id}, sort=[("fecha_registro", -1), ("_id", -1)], session=sesion
        )

    async def listar_por_vehiculo(self, vehiculo_id: ObjectId, sesion: AsyncClientSession | None = None) -> list[dict]:
        """Registros del vehículo en el orden de la cadena (por fecha de registro)."""
        cursor = self._coleccion.find({"vehiculo_id": vehiculo_id}, session=sesion).sort(
            [("fecha_registro", 1), ("_id", 1)]
        )
        return await cursor.to_list()

    async def listar_por_taller(self, taller_id: ObjectId) -> list[dict]:
        """Registros del taller, del más reciente al más antiguo, con el dominio de cada vehículo."""
        cursor = await self._coleccion.aggregate([
            {"$match": {"taller_id": taller_id}},
            {"$sort": {"fecha_registro": -1}},
            {"$lookup": {
                "from": "vehiculos",
                "localField": "vehiculo_id",
                "foreignField": "_id",
                "as": "vehiculo",
                "pipeline": [{"$project": {"dominio": 1}}],
            }},
            {"$set": {"dominio": {"$first": "$vehiculo.dominio"}}},
            {"$unset": "vehiculo"},
        ])
        return await cursor.to_list()
