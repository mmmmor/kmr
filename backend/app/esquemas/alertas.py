from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel


class EstadoAlerta(StrEnum):
    PROXIMO = "proximo"
    VENCIDO = "vencido"


class AlertaServicioSalida(BaseModel):
    estado: EstadoAlerta
    intervencion_id: str  # el servicio que recomendó la revisión
    tipo: str
    fecha_servicio: datetime
    taller: str | None  # razón social si la recomendó un taller; None si es autorreportada
    detalle: str | None
    kilometraje: int | None  # recomendado
    fecha: datetime | None  # recomendada
    km_restantes: int | None  # negativo si ya se superó
    dias_restantes: int | None  # negativo si la fecha ya pasó


class AlertasSalida(BaseModel):
    ultimo_kilometraje: int | None
    alertas: list[AlertaServicioSalida]  # primero las vencidas, después la más cercana
