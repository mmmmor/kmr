"""Fechas: se guardan en UTC y se interpretan en hora de Argentina."""

from datetime import UTC, date, datetime, time, timedelta, timezone

# Argentina no usa horario de verano desde 2009: alcanza con UTC-3 fijo (y no depende de tzdata).
ZONA_ARGENTINA = timezone(timedelta(hours=-3), "ART")


def hoy_en_argentina() -> date:
    return datetime.now(ZONA_ARGENTINA).date()


def inicio_del_dia(fecha: date) -> datetime:
    """Una fecha sin hora (por ejemplo, la de un servicio) se guarda como las 00:00 de Argentina, en UTC."""
    return datetime.combine(fecha, time.min, tzinfo=ZONA_ARGENTINA).astimezone(UTC)


def ahora_en_milisegundos() -> datetime:
    """Hora actual en UTC con la precisión con que MongoDB guarda las fechas (milisegundos).

    Así el documento que se hashea al insertarlo es idéntico al que después se lee de la base.
    """
    ahora = datetime.now(UTC)
    return ahora.replace(microsecond=ahora.microsecond // 1000 * 1000)
