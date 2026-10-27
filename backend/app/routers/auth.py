from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.errores import ErrorDeCampo
from app.esquemas.auth import LoginEntrada, RegistroEntrada, SesionSalida, UsuarioSalida
from app.repositorios.talleres import RepositorioTalleres
from app.repositorios.usuarios import CorreoYaRegistrado, RepositorioUsuarios
from app.routers.dependencias import obtener_repositorio_talleres, obtener_repositorio_usuarios
from app.servicios import auth as servicio_auth

router = APIRouter(prefix="/auth", tags=["auth"])

MENSAJE_CORREO_REGISTRADO = "Ya existe una cuenta con ese correo electrónico."

ESTADOS_ERROR_LOGIN = {
    "credenciales": status.HTTP_401_UNAUTHORIZED,
    "bloqueada": status.HTTP_429_TOO_MANY_REQUESTS,
    "taller_pendiente": status.HTTP_403_FORBIDDEN,
    "taller_rechazado": status.HTTP_403_FORBIDDEN,
}


@router.post("/registro", status_code=status.HTTP_201_CREATED)
async def registro(
    datos: RegistroEntrada,
    repo: Annotated[RepositorioUsuarios, Depends(obtener_repositorio_usuarios)],
) -> UsuarioSalida:
    """Alta de propietario (HU-001)."""
    try:
        return await servicio_auth.registrar_propietario(datos, repo)
    except CorreoYaRegistrado:
        raise ErrorDeCampo(status.HTTP_409_CONFLICT, "correo", MENSAJE_CORREO_REGISTRADO)


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
