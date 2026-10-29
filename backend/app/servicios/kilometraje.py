"""Validación del kilometraje (HU-009). Nunca rechaza un registro: lo guarda con una alerta visible.

Todo se calcula sobre los registros del vehículo en el orden de la cadena (por fecha de registro).
Como los registros solo se insertan, la lectura contra la que se comparó cada uno se puede
reconstruir en cualquier momento con los registros anteriores a él: no hace falta guardarla.
"""

from datetime import datetime

from app.core.config import obtener_settings
from app.modelos.intervencion import AlertaKilometraje


def lecturas_validas(registros: list[dict]) -> list[dict]:
    """Registros cuyo kilometraje cuenta: si uno fue corregido, cuenta la corrección y no el original."""
    corregidos = {r["corrige_a"] for r in registros if r.get("corrige_a") is not None}
    return [r for r in registros if r["_id"] not in corregidos]


def ultima_lectura(registros: list[dict]) -> dict | None:
    """La lectura válida con la fecha de servicio más reciente (no la última cargada)."""
    return max(
        lecturas_validas(registros),
        key=lambda r: (r["fecha_intervencion"], r["fecha_registro"], r["_id"]),
        default=None,
    )


def lectura_de_referencia(anteriores: list[dict], intervencion: dict) -> dict | None:
    """La última lectura válida contra la que se compara `intervencion`, dados los registros previos.

    Si `intervencion` es una corrección, el registro que corrige deja de contar: se compara con
    lo que había antes de él.
    """
    corregido = intervencion.get("corrige_a")
    return ultima_lectura([r for r in anteriores if r["_id"] != corregido])


def evaluar(
    kilometraje: int, fecha_intervencion: datetime, referencia: dict | None, km_max_por_dia: int | None = None
) -> AlertaKilometraje | None:
    """Alerta del registro frente a la última lectura válida. La primera intervención no se valida.

    El incremento es incompatible si supera `km_max_por_dia` por cada día transcurrido. Un servicio
    del mismo día admite hasta un día de uso; uno con fecha anterior a la última lectura no admite
    ningún incremento (el odómetro no puede haber avanzado hacia atrás en el tiempo).
    """
    if referencia is None:
        return None
    if kilometraje < referencia["kilometraje"]:
        return AlertaKilometraje.KILOMETRAJE_INFERIOR
    if km_max_por_dia is None:
        km_max_por_dia = obtener_settings().km_max_por_dia
    dias = (fecha_intervencion - referencia["fecha_intervencion"]).days
    permitido = km_max_por_dia * max(dias, 1) if dias >= 0 else 0
    if kilometraje - referencia["kilometraje"] > permitido:
        return AlertaKilometraje.INCREMENTO_INCOMPATIBLE
    return None


def referencias(registros: list[dict]) -> dict:
    """Para cada registro (por _id), la lectura contra la que se validó al cargarlo."""
    return {r["_id"]: lectura_de_referencia(registros[:i], r) for i, r in enumerate(registros)}
