import re
from typing import Annotated

from pydantic import BaseModel, StringConstraints, field_validator

from app.core.seguridad import validar_politica_contrasena
from app.modelos.usuario import Rol

Texto = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]

PATRON_CORREO = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class RegistroEntrada(BaseModel):
    nombre: Texto
    apellido: Texto
    correo: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=254)]
    contrasena: Annotated[str, StringConstraints(min_length=1)]

    @field_validator("correo")
    @classmethod
    def normalizar_correo(cls, correo: str) -> str:
        if not PATRON_CORREO.match(correo):
            raise ValueError("Ingresá un correo electrónico válido.")
        return correo.lower()

    @field_validator("contrasena")
    @classmethod
    def validar_contrasena(cls, contrasena: str) -> str:
        if error := validar_politica_contrasena(contrasena):
            raise ValueError(error)
        return contrasena


class LoginEntrada(BaseModel):
    correo: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=254)]
    # Sin política acá: solo se compara contra el hash guardado.
    contrasena: Annotated[str, StringConstraints(min_length=1, max_length=256)]

    @field_validator("correo")
    @classmethod
    def normalizar_correo(cls, correo: str) -> str:
        return correo.lower()


class RecuperarEntrada(BaseModel):
    correo: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=254)]

    @field_validator("correo")
    @classmethod
    def normalizar_correo(cls, correo: str) -> str:
        if not PATRON_CORREO.match(correo):
            raise ValueError("Ingresá un correo electrónico válido.")
        return correo.lower()


class RestablecerEntrada(BaseModel):
    token: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
    contrasena: Annotated[str, StringConstraints(min_length=1)]

    @field_validator("contrasena")
    @classmethod
    def validar_contrasena(cls, contrasena: str) -> str:
        if error := validar_politica_contrasena(contrasena):
            raise ValueError(error)
        return contrasena


class MensajeSalida(BaseModel):
    mensaje: str


class SesionSalida(BaseModel):
    token: str
    rol: Rol
    nombre: str
    apellido: str
    razon_social: str | None = None  # solo talleres: el panel muestra el establecimiento


class UsuarioSalida(BaseModel):
    id: str
    nombre: str
    apellido: str
    correo: str
    rol: Rol
