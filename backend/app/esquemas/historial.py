from datetime import datetime

from pydantic import BaseModel

from app.esquemas.intervenciones import IntervencionSalida
from app.esquemas.vehiculos import VehiculoSalida


class RegistroVinculado(BaseModel):
    """El otro extremo de una corrección: "Corrige el registro del 18/06/2026"."""

    id: str
    fecha: datetime  # la fecha con la que ese registro se muestra en el historial


class IntervencionHistorialSalida(IntervencionSalida):
    fecha: datetime  # la del servicio; en una corrección, la del día en que se cargó
    taller: str | None  # razón social del taller verificado; None si es autorreportada
    corrige_a: RegistroVinculado | None
    corregido_por: RegistroVinculado | None
    motivo_correccion: str | None
    campos_corregidos: list[str]  # en una corrección, qué datos cambian respecto del registro que corrige


class HistorialSalida(BaseModel):
    vehiculo: VehiculoSalida
    integridad_verificada: bool
    intervenciones: list[IntervencionHistorialSalida]  # del más reciente al más antiguo
