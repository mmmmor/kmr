from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Response, UploadFile, status

from app.core.errores import ErrorDeCampo
from app.core.seguridad import UsuarioSesion, requiere_rol
from app.esquemas.intervenciones import CorreccionEntrada, IntervencionSalida
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
    obtener_transaccion,
)
from app.servicios import comprobantes as servicio_comprobantes
from app.servicios import correcciones as servicio_correcciones
from app.servicios import intervenciones as servicio_intervenciones

router = APIRouter(prefix="/intervenciones", tags=["intervenciones"])

TallerOPropietario = Annotated[UsuarioSesion, Depends(requiere_rol(Rol.PROPIETARIO, Rol.TALLER))]
Intervenciones = Annotated[RepositorioIntervenciones, Depends(obtener_repositorio_intervenciones)]
Vehiculos = Annotated[RepositorioVehiculos, Depends(obtener_repositorio_vehiculos)]
Talleres = Annotated[RepositorioTalleres, Depends(obtener_repositorio_talleres)]


async def leer_comprobante_adjunto(comprobante: UploadFile | None) -> tuple[bytes, str, str] | None:
    """Valida el archivo adjunto de un registro. Si no se admite, responde 422 marcando el campo."""
    if comprobante is None:
        return None
    try:
        return await servicio_comprobantes.leer(comprobante)
    except servicio_comprobantes.ComprobanteInvalido as error:
        raise ErrorDeCampo(status.HTTP_422_UNPROCESSABLE_CONTENT, "comprobante", error.mensaje)


@router.post("/{intervencion_id}/correcciones", status_code=status.HTTP_201_CREATED)
async def corregir(
    intervencion_id: str,
    datos: CorreccionEntrada,
    usuario: TallerOPropietario,
    intervenciones: Intervenciones,
    vehiculos: Vehiculos,
    talleres: Talleres,
    en_transaccion=Depends(obtener_transaccion),
) -> IntervencionSalida:
    """Registra una corrección vinculada al registro, con motivo (HU-011). El original no se modifica.

    Se envían los datos completos ya corregidos. Un taller corrige solo sus registros; un propietario,
    solo sus intervenciones autorreportadas.
    """
    try:
        return await servicio_correcciones.corregir(
            intervencion_id, datos, usuario, intervenciones, vehiculos, talleres, en_transaccion
        )
    except servicio_correcciones.RegistroNoEncontrado:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "El registro no existe o no podés corregirlo.")
    except servicio_correcciones.CorreccionNoPermitida as error:
        raise HTTPException(status.HTTP_403_FORBIDDEN, error.mensaje)
    except servicio_correcciones.RegistroYaCorregido:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Este registro ya tiene una corrección. Si hay otro error, corregí el registro de la corrección.",
        )
    except servicio_correcciones.SinCambios:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, "El valor correcto es igual al registrado: no hay nada que corregir."
        )


@router.get("/{intervencion_id}/comprobante")
async def comprobante(
    intervencion_id: str,
    usuario: TallerOPropietario,
    intervenciones: Intervenciones,
    vehiculos: Vehiculos,
    talleres: Talleres,
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
