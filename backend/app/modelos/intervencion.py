from enum import StrEnum


class Origen(StrEnum):
    TALLER = "taller"
    PROPIETARIO = "propietario"


# Tipos que se pueden elegir al registrar. Las métricas cuentan intervenciones por tipo,
# por eso es una lista cerrada. El frontend tiene la misma lista (src/utils/intervenciones.js).
TIPOS_INTERVENCION = (
    "Cambio de aceite y filtros",
    "Frenos",
    "Suspensión y tren delantero",
    "Neumáticos, alineación y balanceo",
    "Distribución",
    "Embrague y transmisión",
    "Batería y sistema eléctrico",
    "Refrigeración",
    "Encendido e inyección",
    "Aire acondicionado",
    "Escape",
    "Revisión general",
    "Otro",
)
