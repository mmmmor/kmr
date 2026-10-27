from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Response, UploadFile, status

from app.core.errores import ErrorDeCampo
from app.core.seguridad import UsuarioSesion, requiere_rol
from app.modelos.usuario import Rol
from app.repositorios.comprobantes import AlmacenComprobantes
from app.repositorios.intervenciones import RepositorioIntervenciones
from app.repositorios.talleres import RepositorioTalleres
from app.repositorios.vehiculos import RepositorioVehiculos
from app.routers.dependencias import (
    obtener_almacen_comprobantes,
    obtener_repositorio_intervenciones,
    obtener_repositorio_talleres,
    obtener_repositorio_vehiculos,
)
from app.servicios import comprobantes as servicio_comprobantes
from app.servicios import intervenciones as servicio_intervenciones

router = APIRouter(prefix="/intervenciones", tags=["intervenciones"])


async def leer_comprobante_adjunto(comprobante: UploadFile | None) -> tuple[bytes, str, str] | None:
    """Valida el archivo adjunto de un registro. Si no se admite, responde 422 marcando el campo."""
    if comprobante is None:
        return None
    try:
        return await servicio_comprobantes.leer(comprobante)
    except servicio_comprobantes.ComprobanteInvalido as error:
        raise ErrorDeCampo(status.HTTP_422_UNPROCESSABLE_CONTENT, "comprobante", error.mensaje)


@router.get("/{intervencion_id}/comprobante")
async def comprobante(
    intervencion_id: str,
    usuario: Annotated[UsuarioSesion, Depends(requiere_rol(Rol.PROPIETARIO, Rol.TALLER))],
    intervenciones: Annotated[RepositorioIntervenciones, Depends(obtener_repositorio_intervenciones)],
    vehiculos: Annotated[RepositorioVehiculos, Depends(obtener_repositorio_vehiculos)],
    talleres: Annotated[RepositorioTalleres, Depends(obtener_repositorio_talleres)],
    comprobantes: Annotated[AlmacenComprobantes, Depends(obtener_almacen_comprobantes)],
) -> Response:
    """Descarga el comprobante: solo el propietario del vehículo o el taller que cargó el registro."""
    try:
        contenido, nombre, tipo = await servicio_intervenciones.leer_comprobante(
            intervencion_id, usuario, intervenciones, vehiculos, talleres, comprobantes
        )
    except servicio_intervenciones.ComprobanteNoDisponible:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "El comprobante no existe o no tenés acceso a él.")
    return Response(
        contenido,
        media_type=tipo,
        headers={
            "Content-Disposition": f"inline; filename*=UTF-8''{quote(nombre)}",
            "X-Content-Type-Options": "nosniff",
        },
    )
