"""Endpoints sin sesión (HU-010)."""

from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.core.errores import ErrorDeCampo
from app.esquemas.publico import ConsultaPublicaSalida
from app.esquemas.vehiculos import validar_dominio
from app.repositorios.intervenciones import RepositorioIntervenciones
from app.repositorios.talleres import RepositorioTalleres
from app.repositorios.vehiculos import RepositorioVehiculos
from app.routers.dependencias import (
    obtener_repositorio_intervenciones,
    obtener_repositorio_talleres,
    obtener_repositorio_vehiculos,
)
from app.servicios import publico as servicio_publico

router = APIRouter(prefix="/publico", tags=["publico"])


@router.get("/vehiculos/{dominio}")
async def consultar_vehiculo(
    dominio: str,
    vehiculos: Annotated[RepositorioVehiculos, Depends(obtener_repositorio_vehiculos)],
    intervenciones: Annotated[RepositorioIntervenciones, Depends(obtener_repositorio_intervenciones)],
    talleres: Annotated[RepositorioTalleres, Depends(obtener_repositorio_talleres)],
) -> ConsultaPublicaSalida:
    """Historial público de un vehículo por dominio, sin datos personales del titular (HU-010)."""
    try:
        normalizado = validar_dominio(dominio)
    except ValueError as error:
        raise ErrorDeCampo(status.HTTP_422_UNPROCESSABLE_CONTENT, "dominio", str(error))
    return await servicio_publico.consultar(normalizado, vehiculos, intervenciones, talleres)
