"""Recuperación de contraseña (HU-015).

- Siempre se responde lo mismo, exista o no la cuenta.
- Si existe, se envía un enlace con un token aleatorio de un solo uso que vence a los 30 minutos.
  Se guarda solo su hash.
- Al cambiar la contraseña el token queda utilizado, y se levanta el bloqueo por intentos fallidos.
"""

import hashlib
import html
import logging
import secrets
from datetime import UTC, datetime, timedelta

from app.core.config import obtener_settings
from app.core.seguridad import hashear_contrasena
from app.repositorios.tokens import RepositorioTokensRecuperacion
from app.repositorios.usuarios import RepositorioUsuarios
from app.servicios.correo import Correo

VIGENCIA_TOKEN = timedelta(minutes=30)

MENSAJE_SOLICITUD = (
    "Si el correo está registrado, vas a recibir un enlace para crear una nueva contraseña. "
    "El enlace es de un solo uso y vence en 30 minutos."
)
MENSAJE_RESTABLECIDA = "Tu contraseña se cambió. Ya podés iniciar sesión con la nueva."

logger = logging.getLogger("kmr.recuperacion")


class TokenInvalido(Exception):
    """El enlace no existe, ya se usó o venció."""


def hash_token(token: str) -> str:
    # El token ya es aleatorio y largo: alcanza con SHA-256 (no hace falta bcrypt).
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


async def solicitar(
    correo: str,
    usuarios: RepositorioUsuarios,
    tokens: RepositorioTokensRecuperacion,
    ahora: datetime | None = None,
) -> Correo | None:
    """Genera el token si la cuenta existe y devuelve el correo a enviar; si no existe, None."""
    usuario = await usuarios.buscar_por_correo(correo)
    if usuario is None:
        return None
    ahora = ahora or datetime.now(UTC)
    token = secrets.token_urlsafe(32)
    await tokens.invalidar_vigentes(usuario["_id"])
    await tokens.insertar({
        "usuario_id": usuario["_id"],
        "token_hash": hash_token(token),
        "fecha_vencimiento": ahora + VIGENCIA_TOKEN,
        "utilizado": False,
    })
    return correo_de_recuperacion(usuario, token)


def correo_de_recuperacion(usuario: dict, token: str) -> Correo:
    enlace = f"{obtener_settings().frontend_url}/recuperar?token={token}"
    nombre = usuario["nombre"]
    texto = (
        f"Hola, {nombre}:\n\n"
        "Recibimos un pedido para restablecer la contraseña de tu cuenta de KmR. "
        f"Para crear una nueva, entrá a este enlace:\n\n{enlace}\n\n"
        "El enlace es de un solo uso y vence en 30 minutos. "
        "Si no lo pediste vos, ignorá este correo: tu contraseña no cambia."
    )
    contenido = (
        f"<p>Hola, {html.escape(nombre)}:</p>"
        "<p>Recibimos un pedido para restablecer la contraseña de tu cuenta de KmR.</p>"
        f'<p><a href="{html.escape(enlace)}">Crear una nueva contraseña</a></p>'
        "<p>El enlace es de un solo uso y vence en 30 minutos. "
        "Si no lo pediste vos, ignorá este correo: tu contraseña no cambia.</p>"
    )
    return Correo(usuario["correo"], f"{nombre} {usuario['apellido']}", "Restablecé tu contraseña de KmR", contenido, texto)


async def enviar(enviador, correo: Correo) -> None:
    """Se ejecuta después de responder: un error de envío se registra, sin el token ni el enlace."""
    try:
        await enviador.enviar(correo)
    except Exception:
        logger.exception("No se pudo enviar el correo de recuperación a %s.", correo.destinatario)


async def restablecer(
    token: str,
    contrasena: str,
    usuarios: RepositorioUsuarios,
    tokens: RepositorioTokensRecuperacion,
    en_transaccion,
    ahora: datetime | None = None,
) -> None:
    """Cambia la contraseña y consume el token en una transacción. Lanza TokenInvalido si no sirve."""
    ahora = ahora or datetime.now(UTC)
    contrasena_hash = hashear_contrasena(contrasena)  # fuera de la transacción: bcrypt tarda

    async def cambiar(sesion):
        registro = await tokens.consumir(hash_token(token), ahora, sesion=sesion)
        if registro is None:
            raise TokenInvalido
        await usuarios.cambiar_contrasena(registro["usuario_id"], contrasena_hash, sesion=sesion)

    await en_transaccion(cambiar)
