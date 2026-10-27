"""Formato de errores de la API: { "detail": mensaje, "campos": { campo: mensaje } }.

Los campos anidados se nombran con su ruta separada por puntos, por ejemplo "items.0.cantidad".
"""

from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ValidationError

MENSAJES = {
    "missing": "Completá este campo.",
    "string_too_short": "Completá este campo.",
    "string_type": "Ingresá un texto.",
    "int_type": "Ingresá un número entero.",
    "int_parsing": "Ingresá un número entero.",
    "int_from_float": "Ingresá un número entero.",
    "date_type": "Ingresá una fecha válida.",
    "date_parsing": "Ingresá una fecha válida.",
    "date_from_datetime_parsing": "Ingresá una fecha válida.",
    "date_from_datetime_inexact": "Ingresá una fecha válida.",
    "json_invalid": "Los datos enviados no tienen un formato válido.",
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
    # Un número o una fecha sin completar llegan como null o "": es un campo vacío, no un formato inválido.
    if tipo.endswith(("_type", "_parsing")) and error.get("input") in (None, ""):
        return MENSAJES["missing"]
    return MENSAJES.get(tipo, "El valor ingresado no es válido.")


def validar_json(modelo: type[BaseModel], datos: str):
    """Valida un JSON recibido como campo de un formulario multipart, con el mismo formato de errores."""
    try:
        return modelo.model_validate_json(datos)
    except ValidationError as error:
        raise RequestValidationError(error.errors(include_url=False)) from error


async def manejar_error_validacion(request: Request, exc: RequestValidationError) -> JSONResponse:
    campos: dict[str, str] = {}
    for error in exc.errors():
        loc = [str(parte) for parte in error["loc"] if parte != "body"]
        campo = ".".join(loc) if loc else "general"
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
