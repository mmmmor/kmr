from bson import ObjectId
from pymongo.asynchronous.database import AsyncDatabase
from pymongo.errors import DuplicateKeyError


class DominioYaVinculado(Exception):
    pass


class RepositorioVehiculos:
    def __init__(self, db: AsyncDatabase):
        self._coleccion = db["vehiculos"]

    async def insertar(self, vehiculo: dict) -> ObjectId:
        """Inserta el vehículo. El índice único sobre `dominio` impide vincularlo a dos cuentas."""
        try:
            resultado = await self._coleccion.insert_one(vehiculo)
        except DuplicateKeyError as error:
            raise DominioYaVinculado from error
        return resultado.inserted_id

    async def buscar(self, vehiculo_id: ObjectId) -> dict | None:
        return await self._coleccion.find_one({"_id": vehiculo_id})

    async def buscar_por_dominio(self, dominio: str) -> dict | None:
        return await self._coleccion.find_one({"dominio": dominio})

    async def listar_por_propietario(self, propietario_id: ObjectId) -> list[dict]:
        """Vehículos del propietario, en el orden en que los vinculó."""
        cursor = self._coleccion.find({"propietario_id": propietario_id}).sort("fecha_vinculacion", 1)
        return await cursor.to_list()
