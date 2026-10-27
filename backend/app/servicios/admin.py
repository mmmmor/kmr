from datetime import UTC, datetime

from bson import ObjectId
from bson.errors import InvalidId

from app.esquemas.admin import Responsable, SolicitudSalida
from app.modelos.taller import EstadoSolicitud
from app.repositorios.talleres import RepositorioTalleres


class SolicitudNoEncontrada(Exception):
    pass


class SolicitudYaResuelta(Exception):
    pass


async def listar_solicitudes(estado: EstadoSolicitud, talleres: RepositorioTalleres) -> list[SolicitudSalida]:
    return [_a_salida(t) for t in await talleres.listar_con_responsable(estado)]


async def aprobar(solicitud_id: str, administrador_id: str, talleres: RepositorioTalleres) -> None:
    """Aprueba una solicitud pendiente: desde ese momento el taller puede iniciar sesión (HU-004)."""
    await _resolver(solicitud_id, EstadoSolicitud.APROBADO, administrador_id, talleres)


async def rechazar(solicitud_id: str, motivo: str, administrador_id: str, talleres: RepositorioTalleres) -> None:
    """Rechaza una solicitud pendiente con un motivo, que el taller ve al intentar iniciar sesión (HU-004)."""
    await _resolver(solicitud_id, EstadoSolicitud.RECHAZADO, administrador_id, talleres, motivo)


async def _resolver(solicitud_id, estado, administrador_id, talleres, motivo=None) -> None:
    taller_id = _object_id(solicitud_id)
    resuelta = await talleres.resolver_pendiente(
        taller_id, estado, _object_id(administrador_id), datetime.now(UTC), motivo
    )
    if not resuelta:
        if await talleres.buscar(taller_id) is None:
            raise SolicitudNoEncontrada
        raise SolicitudYaResuelta


def _object_id(valor: str):
    try:
        return ObjectId(valor)
    except (InvalidId, TypeError):
        raise SolicitudNoEncontrada


def _a_salida(taller: dict) -> SolicitudSalida:
    return SolicitudSalida(
        id=str(taller["_id"]),
        razon_social=taller["razon_social"],
        cuit=taller["cuit"],
        domicilio=taller["domicilio"],
        telefono=taller["telefono"],
        estado_solicitud=taller["estado_solicitud"],
        fecha_solicitud=taller["fecha_solicitud"],
        motivo_rechazo=taller.get("motivo_rechazo"),
        fecha_resolucion=taller.get("fecha_resolucion"),
        responsable=Responsable(**{k: taller["responsable"][k] for k in ("nombre", "apellido", "correo")}),
    )
