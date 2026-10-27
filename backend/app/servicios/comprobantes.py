"""Validación de los comprobantes adjuntos: PDF, JPG o PNG de hasta 5 MB, según su contenido real."""

from fastapi import UploadFile

TAMANO_MAXIMO = 5 * 1024 * 1024

# Primeros bytes de cada formato admitido: la extensión y el Content-Type los decide quien envía.
FIRMAS = (
    (b"%PDF-", "application/pdf"),
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"\x89PNG\r\n\x1a\n", "image/png"),
)


class ComprobanteInvalido(Exception):
    def __init__(self, mensaje: str):
        super().__init__(mensaje)
        self.mensaje = mensaje


def tipo_real(contenido: bytes) -> str | None:
    return next((tipo for firma, tipo in FIRMAS if contenido.startswith(firma)), None)


async def leer(archivo: UploadFile) -> tuple[bytes, str, str]:
    """Contenido, tipo MIME real y nombre del archivo. Lanza ComprobanteInvalido si no se admite."""
    contenido = await archivo.read(TAMANO_MAXIMO + 1)
    if len(contenido) > TAMANO_MAXIMO:
        raise ComprobanteInvalido("El comprobante no puede superar los 5 MB.")
    tipo = tipo_real(contenido)
    if tipo is None:
        raise ComprobanteInvalido("El comprobante tiene que ser un archivo PDF, JPG o PNG.")
    # Los últimos 100 caracteres conservan la extensión de un nombre largo.
    nombre = (archivo.filename or "comprobante")[-100:]
    return contenido, tipo, nombre
