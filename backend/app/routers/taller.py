"""Endpoints del rol taller (distintos de /talleres/solicitud, que es el alta pública)."""

from typing import Annotated

from bson import ObjectId
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from app.core.errores import ErrorDeCampo, validar_json
from app.core.seguridad import UsuarioSesion, requiere_rol
from app.esquemas.historial import IntervencionHistorialSalida
from app.esquemas.intervenciones import (
    AutorizacionEntrada,
    AutorizacionSalida,
    IntervencionSalida,
    IntervencionTallerEntrada,
)
from app.modelos.taller import EstadoSolicitud
from app.modelos.usuario import Rol
from app.repositorios.codigos import RepositorioCodigos
from app.repositorios.comprobantes import AlmacenComprobantes
from app.repositorios.intervenciones import RepositorioIntervenciones
from app.repositorios.talleres import RepositorioTalleres
from app.repositorios.vehiculos import RepositorioVehiculos
from app.routers.dependencias import (
    obtener_almacen_comprobantes,
    obtener_repositorio_codigos,
    obtener_repositorio_intervenciones,
    obtener_repositorio_talleres,
    obtener_repositorio_vehiculos,
    obtener_transaccion,
)
from app.routers.intervenciones import leer_comprobante_adjunto
from app.servicios import historial as servicio_historial
from app.servicios import intervenciones as servicio_intervenciones
from app.servicios.codigos import MENSAJE_CODIGO_INVALIDO, CodigoInvalido

router = APIRouter(prefix="/taller", tags=["taller"])

UsuarioTaller = Annotated[UsuarioSesion, Depends(requiere_rol(Rol.TALLER))]
Talleres = Annotated[RepositorioTalleres, Depends(obtener_repositorio_talleres)]
Vehiculos = Annotated[RepositorioVehiculos, Depends(obtener_repositorio_vehiculos)]
Codigos = Annotated[RepositorioCodigos, Depends(obtener_repositorio_codigos)]
Intervenciones = Annotated[RepositorioIntervenciones, Depends(obtener_repositorio_intervenciones)]
Comprobantes = Annotated[AlmacenComprobantes, Depends(obtener_almacen_comprobantes)]


async def obtener_taller_aprobado(usuario: UsuarioTaller, talleres: Talleres) -> dict:
    """Dependencia: el taller del usuario, solo si su solicitud está aprobada."""
    taller = await talleres.buscar_por_usuario(ObjectId(usuario.id))
    if taller is None or taller["estado_solicitud"] != EstadoSolicitud.APROBADO:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Tu taller no está habilitado para registrar intervenciones.")
    return taller


TallerAprobado = Annotated[dict, Depends(obtener_taller_aprobado)]


@router.post("/autorizacion")
async def autorizacion(
    datos: AutorizacionEntrada, taller: TallerAprobado, vehiculos: Vehiculos, codigos: Codigos,
    intervenciones: Intervenciones,
) -> AutorizacionSalida:
    """Valida dominio + código y devuelve el vehículo con su último kilometraje (HU-007, paso 1).

    No consume el código: eso pasa al registrar la intervención. Un código incorrecto sí suma un intento fallido.
    """
    try:
        vehiculo, _ = await servicio_intervenciones.autorizar_taller(datos, vehiculos, codigos)
    except CodigoInvalido:
        raise _codigo_invalido()
    return await servicio_intervenciones.resumen_autorizado(vehiculo, intervenciones)


@router.post("/intervenciones", status_code=status.HTTP_201_CREATED)
async def registrar_intervencion(
    usuario: UsuarioTaller,
    taller: TallerAprobado,
    datos: Annotated[str, Form(description="JSON con dominio, código y datos del servicio.")],
    vehiculos: Vehiculos,
    codigos: Codigos,
    intervenciones: Intervenciones,
    comprobantes: Comprobantes,
    en_transaccion=Depends(obtener_transaccion),
    comprobante: Annotated[UploadFile | None, File(description="PDF, JPG o PNG de hasta 5 MB.")] = None,
) -> IntervencionSalida:
    """Registra la intervención con la identificación del taller y consume el código (HU-007, paso 2).

    Se envía como multipart/form-data: `datos` (JSON) y, si hay, el archivo `comprobante`.
    """
    entrada = validar_json(IntervencionTallerEntrada, datos)
    adjunto = await leer_comprobante_adjunto(comprobante)
    try:
        return await servicio_intervenciones.registrar_por_taller(
            entrada, taller, usuario.id, adjunto, vehiculos, codigos, intervenciones, comprobantes, en_transaccion
        )
    except CodigoInvalido:
        raise _codigo_invalido()


@router.get("/intervenciones")
async def registros_realizados(
    taller: TallerAprobado, intervenciones: Intervenciones
) -> list[IntervencionHistorialSalida]:
    """Intervenciones registradas por el taller, de la más reciente a la más antigua."""
    return await servicio_historial.listar_del_taller(taller, intervenciones)


def _codigo_invalido() -> ErrorDeCampo:
    return ErrorDeCampo(status.HTTP_403_FORBIDDEN, "codigo", MENSAJE_CODIGO_INVALIDO)
