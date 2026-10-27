from pymongo.asynchronous.database import AsyncDatabase
from pymongo.errors import DuplicateKeyError


class CorreoYaRegistrado(Exception):
    pass


class RepositorioUsuarios:
    def __init__(self, db: AsyncDatabase):
        self._coleccion = db["usuarios"]

    async def insertar(self, usuario: dict) -> str:
        """Inserta el usuario. El índice único sobre `correo` evita duplicados aun con altas simultáneas."""
        try:
            resultado = await self._coleccion.insert_one(usuario)
        except DuplicateKeyError as error:
            raise CorreoYaRegistrado from error
        return str(resultado.inserted_id)
