from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class CodigoSalida(BaseModel):
    id: str
    codigo: str
    # Estado para mostrar: además de los guardados, "vencido" (vigente con la fecha ya pasada).
    estado: Literal["vigente", "vencido", "utilizado", "invalidado"]
    fecha_generacion: datetime
    fecha_vencimiento: datetime
    intentos_fallidos: int
    taller: str | None  # razón social del taller que lo utilizó
    fecha_uso: datetime | None


class CodigosVehiculoSalida(BaseModel):
    vigente: CodigoSalida | None
    anteriores: list[CodigoSalida]
    max_intentos_fallidos: int
