from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status

from app.core.errores import ErrorDeCampo
from app.esquemas.auth import (
    LoginEntrada,
    MensajeSalida,
    RecuperarEntrada,
    RegistroEntrada,
    RestablecerEntrada,
    SesionSalida,
    UsuarioSalida,
)
from app.repositorios.talleres import RepositorioTalleres
from app.repositorios.tokens import RepositorioTokensRecuperacion
from app.repositorios.usuarios import CorreoYaRegistrado, RepositorioUsuarios
from app.routers.dependencias import (
    obtener_repositorio_talleres,
    obtener_repositorio_tokens,
    obtener_repositorio_usuarios,
    obtener_transaccion,
)
from app.servicios import auth as servicio_auth
from app.servicios import recuperacion as servicio_recuperacion
from app.servicios.correo import obtener_enviador

router = APIRouter(prefix="/auth", tags=["auth"])

MENSAJE_CORREO_REGISTRADO = "Ya existe una cuenta con ese correo electrónico."
MENSAJE_TOKEN_INVALIDO = "El enlace para restablecer la contraseña no es válido o ya venció."

Usuarios = Annotated[RepositorioUsuarios, Depends(obtener_repositorio_usuarios)]
Tokens = Annotated[RepositorioTokensRecuperacion, Depends(obtener_repositorio_tokens)]

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


@router.post("/recuperar")
async def recuperar(
    datos: RecuperarEntrada,
    usuarios: Usuarios,
    tokens: Tokens,
    tareas: BackgroundTasks,
    enviador=Depends(obtener_enviador),
) -> MensajeSalida:
    """Envía el enlace de recuperación (HU-015). Responde lo mismo exista o no la cuenta.

    El correo se envía después de responder, así el tiempo de respuesta tampoco lo revela.
    """
    correo = await servicio_recuperacion.solicitar(datos.correo, usuarios, tokens)
    if correo is not None:
        tareas.add_task(servicio_recuperacion.enviar, enviador, correo)
    return MensajeSalida(mensaje=servicio_recuperacion.MENSAJE_SOLICITUD)


@router.post("/restablecer")
async def restablecer(
    datos: RestablecerEntrada,
    usuarios: Usuarios,
    tokens: Tokens,
    en_transaccion=Depends(obtener_transaccion),
) -> MensajeSalida:
    """Cambia la contraseña con el token del enlace, que queda utilizado (HU-015)."""
    try:
        await servicio_recuperacion.restablecer(datos.token, datos.contrasena, usuarios, tokens, en_transaccion)
    except servicio_recuperacion.TokenInvalido:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, MENSAJE_TOKEN_INVALIDO)
    return MensajeSalida(mensaje=servicio_recuperacion.MENSAJE_RESTABLECIDA)
