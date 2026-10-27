from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, StringConstraints

from app.modelos.taller import EstadoSolicitud


class Responsable(BaseModel):
    nombre: str
    apellido: str
    correo: str


class SolicitudSalida(BaseModel):
    id: str
    razon_social: str
    cuit: str
    domicilio: str
    telefono: str
    estado_solicitud: EstadoSolicitud
    fecha_solicitud: datetime
    motivo_rechazo: str | None
    fecha_resolucion: datetime | None
    responsable: Responsable


class RechazoEntrada(BaseModel):
    motivo: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]
