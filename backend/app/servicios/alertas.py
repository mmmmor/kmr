"""Alertas de servicio (HU-014), a partir de la próxima revisión recomendada en cada registro.

- Próximo: faltan menos de 30 días para la fecha, o menos de 1.000 km respecto del último
  kilometraje registrado.
- Vencido: la fecha ya pasó o el kilometraje ya fue superado.
- Sin próxima revisión, no hay alerta.

Se evalúa la recomendación del servicio vigente más reciente de cada tipo: hacer de nuevo un
servicio (otro cambio de aceite, por ejemplo) reemplaza lo que había recomendado el anterior.
"""

from datetime import date

from app.core.fechas import ZONA_ARGENTINA, hoy_en_argentina
from app.esquemas.alertas import AlertasSalida, AlertaServicioSalida, EstadoAlerta
from app.repositorios.intervenciones import RepositorioIntervenciones
from app.repositorios.talleres import RepositorioTalleres
from app.servicios import historial, kilometraje

DIAS_AVISO = 30
KM_AVISO = 1_000


def evaluar(proxima: dict, ultimo_km: int | None, hoy: date) -> tuple[EstadoAlerta | None, int | None, int | None]:
    """Estado de una próxima revisión, con los km y días que faltan (negativos si ya pasaron)."""
    km_restantes = None
    if proxima.get("kilometraje") is not None and ultimo_km is not None:
        km_restantes = proxima["kilometraje"] - ultimo_km
    dias_restantes = None
    if proxima.get("fecha") is not None:
        dias_restantes = (proxima["fecha"].astimezone(ZONA_ARGENTINA).date() - hoy).days

    if (km_restantes is not None and km_restantes < 0) or (dias_restantes is not None and dias_restantes < 0):
        estado = EstadoAlerta.VENCIDO
    elif (km_restantes is not None and km_restantes < KM_AVISO) or (
        dias_restantes is not None and dias_restantes < DIAS_AVISO
    ):
        estado = EstadoAlerta.PROXIMO
    else:
        estado = None
    return estado, km_restantes, dias_restantes


def calcular(registros: list[dict], razon_social: dict, hoy: date | None = None) -> AlertasSalida:
    hoy = hoy or hoy_en_argentina()
    vigentes = kilometraje.lecturas_validas(registros)
    ultima = kilometraje.ultima_lectura(registros)
    ultimo_km = ultima["kilometraje"] if ultima else None

    mas_reciente_por_tipo = {}
    for registro in sorted(vigentes, key=lambda r: (r["fecha_intervencion"], r["fecha_registro"], r["_id"])):
        mas_reciente_por_tipo[registro["tipo"]] = registro

    alertas = []
    for registro in mas_reciente_por_tipo.values():
        proxima = registro.get("proxima_revision")
        if not proxima:
            continue
        estado, km_restantes, dias_restantes = evaluar(proxima, ultimo_km, hoy)
        if estado is None:
            continue
        alertas.append(AlertaServicioSalida(
            estado=estado,
            intervencion_id=str(registro["_id"]),
            tipo=registro["tipo"],
            fecha_servicio=registro["fecha_intervencion"],
            taller=razon_social.get(registro.get("taller_id")),
            detalle=proxima.get("detalle"),
            kilometraje=proxima.get("kilometraje"),
            fecha=proxima.get("fecha"),
            km_restantes=km_restantes,
            dias_restantes=dias_restantes,
        ))

    def urgencia(alerta):
        # Para ordenar: lo que falta, en días (1.000 km ≈ 30 días); lo vencido, primero.
        restantes = [v for v in (alerta.dias_restantes,) if v is not None]
        if alerta.km_restantes is not None:
            restantes.append(alerta.km_restantes * DIAS_AVISO / KM_AVISO)
        return alerta.estado != EstadoAlerta.VENCIDO, min(restantes)

    return AlertasSalida(ultimo_kilometraje=ultimo_km, alertas=sorted(alertas, key=urgencia))


async def obtener(
    vehiculo: dict, intervenciones: RepositorioIntervenciones, talleres: RepositorioTalleres
) -> AlertasSalida:
    registros = await intervenciones.listar_por_vehiculo(vehiculo["_id"])
    return calcular(registros, await historial.razones_sociales(registros, talleres))
