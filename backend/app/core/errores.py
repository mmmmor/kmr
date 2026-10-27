"""Formato de errores de la API: { "detail": mensaje, "campos": { campo: mensaje } }."""

from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

MENSAJES = {
    "missing": "Completá este campo.",
    "string_too_short": "Completá este campo.",
    "string_type": "Ingresá un texto.",
}


class ErrorDeCampo(Exception):
    """Error de negocio atribuible a un campo del formulario (por ejemplo, un correo ya registrado)."""

    def __init__(self, status_code: int, campo: str, mensaje: str):
        super().__init__(mensaje)
        self.status_code = status_code
        self.campo = campo
        self.mensaje = mensaje


def _mensaje(error: dict) -> str:
    tipo = error["type"]
    if tipo == "value_error":
        return str(error["ctx"]["error"])
    if tipo == "string_too_long":
        return f"Usá como máximo {error['ctx']['max_length']} caracteres."
    return MENSAJES.get(tipo, "El valor ingresado no es válido.")


async def manejar_error_validacion(request: Request, exc: RequestValidationError) -> JSONResponse:
    campos: dict[str, str] = {}
    for error in exc.errors():
        loc = [parte for parte in error["loc"] if parte != "body"]
        campo = str(loc[0]) if loc else "general"
        campos.setdefault(campo, _mensaje(error))
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content={"detail": "Revisá los datos ingresados.", "campos": campos},
    )


async def manejar_error_de_campo(request: Request, exc: ErrorDeCampo) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.mensaje, "campos": {exc.campo: exc.mensaje}},
    )
