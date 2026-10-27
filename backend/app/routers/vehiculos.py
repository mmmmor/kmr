from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.errores import ErrorDeCampo
from app.core.seguridad import UsuarioSesion, requiere_rol
from app.esquemas.codigos import CodigoSalida, CodigosVehiculoSalida
from app.esquemas.vehiculos import VehiculoEntrada, VehiculoSalida
from app.modelos.usuario import Rol
from app.repositorios.codigos import RepositorioCodigos
from app.repositorios.vehiculos import RepositorioVehiculos
from app.routers.dependencias import (
    obtener_repositorio_codigos,
    obtener_repositorio_vehiculos,
    obtener_transaccion,
)
from app.servicios import codigos as servicio_codigos
from app.servicios import vehiculos as servicio_vehiculos

router = APIRouter(prefix="/vehiculos", tags=["vehiculos"])

Propietario = Annotated[UsuarioSesion, Depends(requiere_rol(Rol.PROPIETARIO))]
Vehiculos = Annotated[RepositorioVehiculos, Depends(obtener_repositorio_vehiculos)]
Codigos = Annotated[RepositorioCodigos, Depends(obtener_repositorio_codigos)]


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
async def mis_vehiculos(propietario: Propietario, vehiculos: Vehiculos) -> list[VehiculoSalida]:
    """Vehículos vinculados a la cuenta del propietario."""
    return await servicio_vehiculos.listar(propietario.id, vehiculos)


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
