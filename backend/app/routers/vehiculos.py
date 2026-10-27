from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.core.errores import ErrorDeCampo
from app.core.seguridad import UsuarioSesion, requiere_rol
from app.esquemas.vehiculos import VehiculoEntrada, VehiculoSalida
from app.modelos.usuario import Rol
from app.repositorios.vehiculos import RepositorioVehiculos
from app.routers.dependencias import obtener_repositorio_vehiculos
from app.servicios import vehiculos as servicio_vehiculos

router = APIRouter(prefix="/vehiculos", tags=["vehiculos"])

Propietario = Annotated[UsuarioSesion, Depends(requiere_rol(Rol.PROPIETARIO))]
Vehiculos = Annotated[RepositorioVehiculos, Depends(obtener_repositorio_vehiculos)]


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
