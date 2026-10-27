from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.seguridad import UsuarioSesion, requiere_rol
from app.esquemas.admin import RechazoEntrada, SolicitudSalida
from app.modelos.taller import EstadoSolicitud
from app.modelos.usuario import Rol
from app.repositorios.talleres import RepositorioTalleres
from app.routers.dependencias import obtener_repositorio_talleres
from app.servicios import admin as servicio_admin

router = APIRouter(prefix="/admin", tags=["admin"])

Administrador = Annotated[UsuarioSesion, Depends(requiere_rol(Rol.ADMINISTRADOR))]
Talleres = Annotated[RepositorioTalleres, Depends(obtener_repositorio_talleres)]


@router.get("/solicitudes")
async def solicitudes(
    administrador: Administrador,
    talleres: Talleres,
    estado: EstadoSolicitud = EstadoSolicitud.PENDIENTE,
) -> list[SolicitudSalida]:
    """Solicitudes de alta de talleres en el estado pedido (HU-004)."""
    return await servicio_admin.listar_solicitudes(estado, talleres)


@router.post("/solicitudes/{solicitud_id}/aprobar", status_code=status.HTTP_204_NO_CONTENT)
async def aprobar(solicitud_id: str, administrador: Administrador, talleres: Talleres) -> None:
    try:
        await servicio_admin.aprobar(solicitud_id, administrador.id, talleres)
    except (servicio_admin.SolicitudNoEncontrada, servicio_admin.SolicitudYaResuelta) as error:
        raise _a_http(error)


@router.post("/solicitudes/{solicitud_id}/rechazar", status_code=status.HTTP_204_NO_CONTENT)
async def rechazar(
    solicitud_id: str, datos: RechazoEntrada, administrador: Administrador, talleres: Talleres
) -> None:
    """Rechaza la solicitud. El motivo es obligatorio y se le muestra al taller al iniciar sesión."""
    try:
        await servicio_admin.rechazar(solicitud_id, datos.motivo, talleres)
    except (servicio_admin.SolicitudNoEncontrada, servicio_admin.SolicitudYaResuelta) as error:
        raise _a_http(error)


def _a_http(error: Exception) -> HTTPException:
    if isinstance(error, servicio_admin.SolicitudNoEncontrada):
        return HTTPException(status.HTTP_404_NOT_FOUND, "La solicitud no existe.")
    return HTTPException(status.HTTP_409_CONFLICT, "Esta solicitud ya fue resuelta. Actualizá la lista.")
