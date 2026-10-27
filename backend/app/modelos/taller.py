from enum import StrEnum


class EstadoSolicitud(StrEnum):
    PENDIENTE = "pendiente"
    APROBADO = "aprobado"
    RECHAZADO = "rechazado"
