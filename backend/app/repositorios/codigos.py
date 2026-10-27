from datetime import datetime

from bson import ObjectId
from pymongo.asynchronous.client_session import AsyncClientSession
from pymongo.asynchronous.database import AsyncDatabase

from app.modelos.codigo import EstadoCodigo

VIGENTE = EstadoCodigo.VIGENTE.value


class RepositorioCodigos:
    def __init__(self, db: AsyncDatabase):
        self._coleccion = db["codigos_autorizacion"]

    async def insertar(self, codigo: dict, sesion: AsyncClientSession | None = None) -> ObjectId:
        resultado = await self._coleccion.insert_one(codigo, session=sesion)
        return resultado.inserted_id

    async def invalidar_vigentes(
        self, vehiculo_id: ObjectId, ahora: datetime, sesion: AsyncClientSession | None = None
    ) -> None:
        """Invalida los códigos del vehículo que siguen en uso. Los ya vencidos quedan como están."""
        await self._coleccion.update_many(
            {"vehiculo_id": vehiculo_id, "estado": VIGENTE, "fecha_vencimiento": {"$gt": ahora}},
            {"$set": {"estado": EstadoCodigo.INVALIDADO.value}},
            session=sesion,
        )

    async def buscar_vigente(self, vehiculo_id: ObjectId, ahora: datetime) -> dict | None:
        """El código en uso del vehículo (vigente y sin vencer), o None."""
        return await self._coleccion.find_one(
            {"vehiculo_id": vehiculo_id, "estado": VIGENTE, "fecha_vencimiento": {"$gt": ahora}},
            sort=[("fecha_generacion", -1)],
        )

    async def listar_por_vehiculo(self, vehiculo_id: ObjectId) -> list[dict]:
        """Códigos del vehículo, del más reciente al más antiguo, con la razón social del taller que usó cada uno."""
        cursor = await self._coleccion.aggregate([
            {"$match": {"vehiculo_id": vehiculo_id}},
            {"$sort": {"fecha_generacion": -1}},
            {"$lookup": {
                "from": "talleres",
                "localField": "taller_id",
                "foreignField": "_id",
                "as": "taller",
                "pipeline": [{"$project": {"razon_social": 1}}],
            }},
            {"$set": {"taller": {"$first": "$taller.razon_social"}}},
        ])
        return await cursor.to_list()

    async def registrar_intento_fallido(self, codigo_id: ObjectId, maximo: int) -> None:
        """Suma un intento fallido y, si supera el máximo, invalida el código. Es una sola operación atómica."""
        await self._coleccion.update_one(
            {"_id": codigo_id, "estado": VIGENTE},
            [
                {"$set": {"intentos_fallidos": {"$add": ["$intentos_fallidos", 1]}}},
                {"$set": {"estado": {"$cond": [
                    {"$gt": ["$intentos_fallidos", maximo]}, EstadoCodigo.INVALIDADO.value, "$estado"
                ]}}},
            ],
        )

    async def marcar_utilizado(
        self,
        codigo_id: ObjectId,
        taller_id: ObjectId,
        ahora: datetime,
        sesion: AsyncClientSession | None = None,
    ) -> bool:
        """Consume el código si sigue vigente y sin vencer. Devuelve False si ya no lo estaba."""
        resultado = await self._coleccion.update_one(
            {"_id": codigo_id, "estado": VIGENTE, "fecha_vencimiento": {"$gt": ahora}},
            {"$set": {"estado": EstadoCodigo.UTILIZADO.value, "taller_id": taller_id, "fecha_uso": ahora}},
            session=sesion,
        )
        return resultado.modified_count == 1
