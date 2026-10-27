"""Traduce los errores de validación de Pydantic al formato { "campos": { campo: mensaje } }."""

from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

MENSAJES = {
    "missing": "Completá este campo.",
    "string_too_short": "Completá este campo.",
    "string_type": "Ingresá un texto.",
}


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
