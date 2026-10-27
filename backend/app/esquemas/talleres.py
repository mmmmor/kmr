import re
from typing import Annotated

from pydantic import BaseModel, StringConstraints, field_validator

from app.esquemas.auth import RegistroEntrada
from app.modelos.taller import EstadoSolicitud

TextoLargo = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]

PESOS_CUIT = (5, 4, 3, 2, 7, 6, 5, 4, 3, 2)


def digito_verificador_cuit(primeros_diez: str) -> int | None:
    """Dígito verificador del CUIT (módulo 11). None si la combinación no admite dígito válido."""
    resto = sum(int(d) * p for d, p in zip(primeros_diez, PESOS_CUIT)) % 11
    digito = 11 - resto
    if digito == 11:
        return 0
    return None if digito == 10 else digito


class SolicitudTallerEntrada(RegistroEntrada):
    """Datos personales del responsable (como en el registro) más los del establecimiento."""

    razon_social: TextoLargo
    cuit: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=20)]
    domicilio: TextoLargo
    telefono: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=30)]

    @field_validator("cuit")
    @classmethod
    def normalizar_cuit(cls, cuit: str) -> str:
        digitos = re.sub(r"[\s-]", "", cuit)
        if not re.fullmatch(r"\d{11}", digitos):
            raise ValueError("El CUIT debe tener 11 dígitos (por ejemplo, 30-71589234-7).")
        if digito_verificador_cuit(digitos[:10]) != int(digitos[10]):
            raise ValueError("El CUIT no es válido: revisá los números ingresados.")
        return digitos

    @field_validator("telefono")
    @classmethod
    def validar_telefono(cls, telefono: str) -> str:
        cantidad_digitos = len(re.sub(r"\D", "", telefono))
        if not re.fullmatch(r"[\d\s()+-]+", telefono) or not 6 <= cantidad_digitos <= 15:
            raise ValueError("Ingresá un teléfono válido.")
        return telefono


class SolicitudTallerSalida(BaseModel):
    id: str
    razon_social: str
    cuit: str
    estado_solicitud: EstadoSolicitud
