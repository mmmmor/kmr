"""Contraseñas (bcrypt), sesiones (JWT HS256) y control de acceso por rol."""

import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Annotated

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import obtener_settings
from app.modelos.usuario import Rol

ALGORITMO_JWT = "HS256"
CONTRASENA_MIN = 8
CONTRASENA_MAX = 64
BCRYPT_MAX_BYTES = 72


# --- Contraseñas ---


def validar_politica_contrasena(contrasena: str) -> str | None:
    """Devuelve qué requisito no cumple la contraseña, o None si es válida."""
    if len(contrasena) > CONTRASENA_MAX:
        return f"La contraseña no puede superar los {CONTRASENA_MAX} caracteres."
    faltantes = []
    if len(contrasena) < CONTRASENA_MIN:
        faltantes.append(f"al menos {CONTRASENA_MIN} caracteres")
    if not re.search(r"[A-ZÁÉÍÓÚÑÜ]", contrasena):
        faltantes.append("al menos una mayúscula")
    if not re.search(r"\d", contrasena):
        faltantes.append("al menos un número")
    if faltantes:
        return "La contraseña debe tener " + _unir(faltantes) + "."
    # 64 caracteres con tildes o ñ pueden ocupar más de los 72 bytes que procesa bcrypt.
    if len(contrasena.encode("utf-8")) > BCRYPT_MAX_BYTES:
        return "La contraseña es demasiado larga: usá menos caracteres con tilde o especiales."
    return None


def hashear_contrasena(contrasena: str) -> str:
    """Hash bcrypt con un salt aleatorio propio de cada contraseña."""
    return bcrypt.hashpw(contrasena.encode("utf-8"), bcrypt.gensalt()).decode("ascii")


def verificar_contrasena(contrasena: str, contrasena_hash: str) -> bool:
    try:
        return bcrypt.checkpw(contrasena.encode("utf-8"), contrasena_hash.encode("ascii"))
    except ValueError:
        return False


def _unir(partes: list[str]) -> str:
    return partes[0] if len(partes) == 1 else ", ".join(partes[:-1]) + " y " + partes[-1]


# --- Sesiones (JWT) ---


@dataclass(frozen=True)
class UsuarioSesion:
    id: str
    rol: Rol


def crear_token(usuario_id: str, rol: Rol) -> str:
    settings = obtener_settings()
    ahora = datetime.now(UTC)
    payload = {
        "sub": usuario_id,
        "rol": rol.value,
        "iat": ahora,
        "exp": ahora + timedelta(minutes=settings.jwt_expira_minutos),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITMO_JWT)


def decodificar_token(token: str) -> UsuarioSesion:
    """Valida firma y vencimiento. Lanza 401 si el token no sirve."""
    try:
        payload = jwt.decode(
            token,
            obtener_settings().jwt_secret,
            algorithms=[ALGORITMO_JWT],
            options={"require": ["sub", "rol", "exp"]},
        )
        return UsuarioSesion(id=payload["sub"], rol=Rol(payload["rol"]))
    except (jwt.InvalidTokenError, ValueError):
        raise _no_autenticado("La sesión no es válida o venció. Iniciá sesión nuevamente.")


_bearer = HTTPBearer(auto_error=False)


def obtener_usuario_actual(
    credenciales: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> UsuarioSesion:
    if credenciales is None:
        raise _no_autenticado("Iniciá sesión para continuar.")
    return decodificar_token(credenciales.credentials)


def requiere_rol(*roles: Rol):
    """Dependencia que deja pasar solo a los usuarios con alguno de los roles indicados."""

    def verificar(
        usuario: Annotated[UsuarioSesion, Depends(obtener_usuario_actual)],
    ) -> UsuarioSesion:
        if usuario.rol not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tenés permiso para realizar esta acción.",
            )
        return usuario

    return verificar


def _no_autenticado(mensaje: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=mensaje,
        headers={"WWW-Authenticate": "Bearer"},
    )
