from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from app.core.errores import ErrorDeCampo, validar_json
from app.core.seguridad import UsuarioSesion, requiere_rol
from app.esquemas.codigos import CodigoSalida, CodigosVehiculoSalida
from app.esquemas.historial import HistorialSalida
from app.esquemas.metricas import MetricasSalida
from app.esquemas.intervenciones import IntervencionEntrada, IntervencionSalida
from app.esquemas.vehiculos import VehiculoEntrada, VehiculoSalida
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
from app.servicios import codigos as servicio_codigos
from app.servicios import historial as servicio_historial
from app.servicios import metricas as servicio_metricas
from app.servicios import intervenciones as servicio_intervenciones
from app.servicios import vehiculos as servicio_vehiculos

router = APIRouter(prefix="/vehiculos", tags=["vehiculos"])

Propietario = Annotated[UsuarioSesion, Depends(requiere_rol(Rol.PROPIETARIO))]
Vehiculos = Annotated[RepositorioVehiculos, Depends(obtener_repositorio_vehiculos)]
Codigos = Annotated[RepositorioCodigos, Depends(obtener_repositorio_codigos)]
Intervenciones = Annotated[RepositorioIntervenciones, Depends(obtener_repositorio_intervenciones)]
Comprobantes = Annotated[AlmacenComprobantes, Depends(obtener_almacen_comprobantes)]
Talleres = Annotated[RepositorioTalleres, Depends(obtener_repositorio_talleres)]


async def obtener_vehiculo_propio(vehiculo_id: str, propietario: Propietario, vehiculos: Vehiculos) -> dict:
    """Dependencia: el vehículo de la ruta, solo si es del propietario que hace el pedido."""
    try:
        return await servicio_vehiculos.obtener_propio(vehiculo_id, propietario.id, vehiculos)
    except servicio_vehiculos.VehiculoNoEncontrado:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "El vehículo no está vinculado a tu cuenta.")


VehiculoPropio = Annotated[dict, Depends(obtener_vehiculo_propio)]


@router.post("", status_code=status.HTTP_201_CREATED)
async def vincular(datos: VehiculoEntrada, propietario: Propietario, vehiculos: Vehiculos) -> VehiculoSalida:
    """Vincula un vehículo a la cuenta por su dominio (HU-005)."""
    try:
        return await servicio_vehiculos.vincular(datos, propietario.id, vehiculos)
    except servicio_vehiculos.VehiculoDeOtroPropietario:
        # Sin más datos: no se revela quién es el otro propietario.
        raise ErrorDeCampo(
            status.HTTP_409_CONFLICT, "dominio", "Ese vehículo se encuentra vinculado a otro propietario."
        )
    except servicio_vehiculos.VehiculoYaVinculado:
        raise ErrorDeCampo(status.HTTP_409_CONFLICT, "dominio", "Ese vehículo ya está vinculado a tu cuenta.")


@router.get("")
async def mis_vehiculos(
    propietario: Propietario, vehiculos: Vehiculos, intervenciones: Intervenciones
) -> list[VehiculoSalida]:
    """Vehículos vinculados a la cuenta del propietario, con su último kilometraje registrado."""
    return await servicio_vehiculos.listar(propietario.id, vehiculos, intervenciones)


@router.get("/{vehiculo_id}/historial")
async def historial(vehiculo: VehiculoPropio, intervenciones: Intervenciones, talleres: Talleres) -> HistorialSalida:
    """Historial completo del vehículo, del más reciente al más antiguo, con correcciones e integridad (HU-012)."""
    return await servicio_historial.obtener(vehiculo, intervenciones, talleres)


@router.get("/{vehiculo_id}/metricas")
async def metricas(vehiculo: VehiculoPropio, intervenciones: Intervenciones) -> MetricasSalida:
    """Frecuencia promedio de mantenimiento, uso estimado y cantidad por tipo y por origen (HU-013)."""
    return await servicio_metricas.obtener(vehiculo, intervenciones)


@router.post("/{vehiculo_id}/intervenciones", status_code=status.HTTP_201_CREATED)
async def registrar_intervencion(
    propietario: Propietario,
    vehiculo: VehiculoPropio,
    datos: Annotated[str, Form(description="JSON con los datos del servicio.")],
    intervenciones: Intervenciones,
    comprobantes: Comprobantes,
    en_transaccion=Depends(obtener_transaccion),
    comprobante: Annotated[UploadFile | None, File(description="PDF, JPG o PNG de hasta 5 MB.")] = None,
) -> IntervencionSalida:
    """Intervención autorreportada por el propietario, sin código (HU-008).

    Se envía como multipart/form-data: `datos` (JSON) y, si hay, el archivo `comprobante`.
    """
    entrada = validar_json(IntervencionEntrada, datos)
    adjunto = await leer_comprobante_adjunto(comprobante)
    return await servicio_intervenciones.registrar_por_propietario(
        entrada, vehiculo, propietario.id, adjunto, intervenciones, comprobantes, en_transaccion
    )


@router.post("/{vehiculo_id}/codigos", status_code=status.HTTP_201_CREATED)
async def generar_codigo(
    vehiculo: VehiculoPropio, codigos: Codigos, en_transaccion=Depends(obtener_transaccion)
) -> CodigoSalida:
    """Genera un código de autorización e invalida el que estaba en uso (HU-006)."""
    return await servicio_codigos.generar(vehiculo, codigos, en_transaccion)


@router.get("/{vehiculo_id}/codigos")
async def codigos_del_vehiculo(vehiculo: VehiculoPropio, codigos: Codigos) -> CodigosVehiculoSalida:
    """Código en uso, intentos fallidos y códigos anteriores con su estado (HU-006)."""
    return await servicio_codigos.listar(vehiculo, codigos)
