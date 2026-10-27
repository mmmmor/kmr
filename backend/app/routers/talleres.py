from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.core.errores import ErrorDeCampo
from app.esquemas.talleres import SolicitudTallerEntrada, SolicitudTallerSalida
from app.repositorios.talleres import CuitYaRegistrado, RepositorioTalleres
from app.repositorios.usuarios import CorreoYaRegistrado, RepositorioUsuarios
from app.routers.auth import MENSAJE_CORREO_REGISTRADO
from app.routers.dependencias import (
    obtener_repositorio_talleres,
    obtener_repositorio_usuarios,
    obtener_transaccion,
)
from app.servicios import talleres as servicio_talleres

router = APIRouter(prefix="/talleres", tags=["talleres"])


@router.post("/solicitud", status_code=status.HTTP_201_CREATED)
async def solicitud(
    datos: SolicitudTallerEntrada,
    usuarios: Annotated[RepositorioUsuarios, Depends(obtener_repositorio_usuarios)],
    talleres: Annotated[RepositorioTalleres, Depends(obtener_repositorio_talleres)],
    en_transaccion=Depends(obtener_transaccion),
) -> SolicitudTallerSalida:
    """Solicitud de alta de taller: queda pendiente hasta que la apruebe un administrador (HU-003)."""
    try:
        return await servicio_talleres.solicitar_alta(datos, usuarios, talleres, en_transaccion)
    except CorreoYaRegistrado:
        raise ErrorDeCampo(status.HTTP_409_CONFLICT, "correo", MENSAJE_CORREO_REGISTRADO)
    except CuitYaRegistrado:
        raise ErrorDeCampo(status.HTTP_409_CONFLICT, "cuit", "Ya hay un taller registrado con ese CUIT.")
