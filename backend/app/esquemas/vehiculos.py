import re
from datetime import UTC, datetime
from typing import Annotated

from pydantic import AfterValidator, BaseModel, StringConstraints, field_validator

# AAA111 (formato anterior) o AA111AA (Mercosur), ya normalizado.
PATRON_DOMINIO = re.compile(r"^([A-Z]{3}\d{3}|[A-Z]{2}\d{3}[A-Z]{2})$")
ANIO_MINIMO = 1900


def normalizar_dominio(dominio: str) -> str:
    """Mayúsculas, sin espacios ni guiones: " ae-123 cd " → "AE123CD"."""
    return re.sub(r"[\s-]", "", dominio).upper()


def validar_dominio(dominio: str) -> str:
    normalizado = normalizar_dominio(dominio)
    if not PATRON_DOMINIO.match(normalizado):
        raise ValueError("El dominio no es válido: usá el formato AAA 111 o AA 111 AA.")
    return normalizado


# Dominio de entrada: se valida y se devuelve normalizado.
Dominio = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=20),
    AfterValidator(validar_dominio),
]

TextoCorto = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=50)]


class VehiculoEntrada(BaseModel):
    dominio: Dominio
    marca: TextoCorto
    modelo: TextoCorto
    anio: int

    @field_validator("anio")
    @classmethod
    def validar_anio(cls, anio: int) -> int:
        # Hasta el año que viene: los modelos salen a la venta antes de su año.
        maximo = datetime.now(UTC).year + 1
        if not ANIO_MINIMO <= anio <= maximo:
            raise ValueError(f"Ingresá un año entre {ANIO_MINIMO} y {maximo}.")
        return anio


class VehiculoSalida(BaseModel):
    id: str
    dominio: str
    marca: str
    modelo: str
    anio: int
    fecha_vinculacion: datetime
