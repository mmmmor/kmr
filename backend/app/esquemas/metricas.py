from datetime import datetime

from pydantic import BaseModel


class CantidadPorTipo(BaseModel):
    tipo: str
    cantidad: int


class LecturaMetrica(BaseModel):
    """Un punto del gráfico de kilometraje: la versión vigente de cada servicio."""

    fecha: datetime
    kilometraje: int
    valor_corregido: bool  # el kilometraje viene de una corrección y no es el que se cargó al principio


class MetricasSalida(BaseModel):
    servicios: int  # sin contar las correcciones: cada servicio una vez, con sus datos vigentes
    correcciones: int
    # Con menos de 2 servicios la frecuencia no se puede calcular: None. Las de kilómetros tampoco
    # si el último kilometraje es menor al primero.
    frecuencia_km: int | None
    frecuencia_dias: int | None
    uso_km_mes: int | None  # None también si todos los servicios son del mismo día
    por_tipo: list[CantidadPorTipo]  # de mayor a menor
    por_taller: int
    autorreportados: int
    lecturas: list[LecturaMetrica]  # por fecha de servicio, del más antiguo al más reciente
