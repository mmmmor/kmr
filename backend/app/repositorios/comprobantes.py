from bson import ObjectId
from gridfs import AsyncGridFSBucket
from pymongo.asynchronous.database import AsyncDatabase


class AlmacenComprobantes:
    """Archivos de los comprobantes, en GridFS (bucket `comprobantes`)."""

    def __init__(self, db: AsyncDatabase):
        self._bucket = AsyncGridFSBucket(db, bucket_name="comprobantes")

    async def guardar(self, nombre: str, contenido: bytes, tipo: str) -> ObjectId:
        return await self._bucket.upload_from_stream(nombre, contenido, metadata={"tipo": tipo})

    async def leer(self, comprobante_id: ObjectId) -> tuple[bytes, str, str]:
        """Contenido, nombre del archivo y tipo MIME."""
        archivo = await self._bucket.open_download_stream(comprobante_id)
        return await archivo.read(), archivo.filename, archivo.metadata["tipo"]

    async def eliminar(self, comprobante_id: ObjectId) -> None:
        """Solo para un comprobante que quedó sin registro porque la carga falló."""
        await self._bucket.delete(comprobante_id)
