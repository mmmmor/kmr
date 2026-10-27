from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pymongo.asynchronous.database import AsyncDatabase

from app.core.db import obtener_db
from app.esquemas.auth import LoginEntrada, RegistroEntrada, SesionSalida, UsuarioSalida
from app.repositorios.talleres import RepositorioTalleres
from app.repositorios.usuarios import CorreoYaRegistrado, RepositorioUsuarios
from app.servicios import auth as servicio_auth

router = APIRouter(prefix="/auth", tags=["auth"])

ESTADOS_ERROR_LOGIN = {
    "credenciales": status.HTTP_401_UNAUTHORIZED,
    "bloqueada": status.HTTP_429_TOO_MANY_REQUESTS,
    "taller_pendiente": status.HTTP_403_FORBIDDEN,
    "taller_rechazado": status.HTTP_403_FORBIDDEN,
}


def obtener_repositorio_usuarios(
    db: Annotated[AsyncDatabase, Depends(obtener_db)],
) -> RepositorioUsuarios:
    return RepositorioUsuarios(db)


def obtener_repositorio_talleres(
    db: Annotated[AsyncDatabase, Depends(obtener_db)],
) -> RepositorioTalleres:
    return RepositorioTalleres(db)


@router.post("/registro", status_code=status.HTTP_201_CREATED)
async def registro(
    datos: RegistroEntrada,
    repo: Annotated[RepositorioUsuarios, Depends(obtener_repositorio_usuarios)],
) -> UsuarioSalida:
    """Alta de propietario (HU-001)."""
    try:
        return await servicio_auth.registrar_propietario(datos, repo)
    except CorreoYaRegistrado:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe una cuenta con ese correo electrónico.",
        )


@router.post("/login")
async def login(
    datos: LoginEntrada,
    usuarios: Annotated[RepositorioUsuarios, Depends(obtener_repositorio_usuarios)],
    talleres: Annotated[RepositorioTalleres, Depends(obtener_repositorio_talleres)],
) -> SesionSalida:
    """Inicio de sesión: devuelve el JWT y el rol (HU-002)."""
    try:
        return await servicio_auth.iniciar_sesion(datos, usuarios, talleres)
    except servicio_auth.ErrorLogin as error:
        raise HTTPException(status_code=ESTADOS_ERROR_LOGIN[error.codigo], detail=error.mensaje)
