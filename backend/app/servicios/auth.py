from datetime import UTC, datetime, timedelta
from functools import lru_cache

from app.core.seguridad import crear_token, hashear_contrasena, verificar_contrasena
from app.esquemas.auth import LoginEntrada, RegistroEntrada, SesionSalida, UsuarioSalida
from app.modelos.taller import EstadoSolicitud
from app.modelos.usuario import Rol
from app.repositorios.talleres import RepositorioTalleres
from app.repositorios.usuarios import RepositorioUsuarios

MAX_INTENTOS_FALLIDOS = 5
DURACION_BLOQUEO = timedelta(minutes=15)

MENSAJE_CREDENCIALES = "Usuario o contraseña incorrectos."


class ErrorLogin(Exception):
    """Login rechazado. `codigo` indica el motivo; `mensaje` está listo para mostrar."""

    def __init__(self, codigo: str, mensaje: str):
        super().__init__(mensaje)
        self.codigo = codigo
        self.mensaje = mensaje


def nuevo_usuario(datos: RegistroEntrada, rol: Rol) -> dict:
    """Documento de `usuarios` listo para insertar, con la contraseña ya hasheada."""
    return {
        "nombre": datos.nombre,
        "apellido": datos.apellido,
        "correo": datos.correo,
        "contrasena_hash": hashear_contrasena(datos.contrasena),
        "rol": rol.value,
        "fecha_alta": datetime.now(UTC),
        "intentos_login_fallidos": 0,
        "bloqueado_hasta": None,
    }


async def registrar_propietario(datos: RegistroEntrada, repo: RepositorioUsuarios) -> UsuarioSalida:
    """Da de alta un propietario. Lanza CorreoYaRegistrado si el correo ya tiene cuenta."""
    usuario_id = await repo.insertar(nuevo_usuario(datos, Rol.PROPIETARIO))
    return UsuarioSalida(
        id=str(usuario_id),
        nombre=datos.nombre,
        apellido=datos.apellido,
        correo=datos.correo,
        rol=Rol.PROPIETARIO,
    )


async def iniciar_sesion(
    datos: LoginEntrada,
    usuarios: RepositorioUsuarios,
    talleres: RepositorioTalleres,
    ahora: datetime | None = None,
) -> SesionSalida:
    """Valida credenciales, aplica el bloqueo por intentos y el estado del taller (HU-002)."""
    ahora = ahora or datetime.now(UTC)
    usuario = await usuarios.buscar_por_correo(datos.correo)

    if usuario is None:
        # Igualamos el tiempo de respuesta con el de un usuario existente, para no revelar qué correos tienen cuenta.
        verificar_contrasena(datos.contrasena, _hash_de_relleno())
        raise ErrorLogin("credenciales", MENSAJE_CREDENCIALES)

    bloqueado_hasta = usuario.get("bloqueado_hasta")
    if bloqueado_hasta and bloqueado_hasta > ahora:
        raise ErrorLogin("bloqueada", _mensaje_bloqueo(bloqueado_hasta, ahora))

    if not verificar_contrasena(datos.contrasena, usuario["contrasena_hash"]):
        intentos = await usuarios.sumar_intento_fallido(usuario["_id"])
        if intentos >= MAX_INTENTOS_FALLIDOS:
            hasta = ahora + DURACION_BLOQUEO
            await usuarios.bloquear(usuario["_id"], hasta)
            raise ErrorLogin("bloqueada", _mensaje_bloqueo(hasta, ahora))
        raise ErrorLogin("credenciales", MENSAJE_CREDENCIALES)

    if usuario.get("intentos_login_fallidos") or bloqueado_hasta:
        await usuarios.reiniciar_intentos(usuario["_id"])

    rol = Rol(usuario["rol"])
    if rol is Rol.TALLER:
        await _verificar_taller_aprobado(usuario["_id"], talleres)

    return SesionSalida(
        token=crear_token(str(usuario["_id"]), rol),
        rol=rol,
        nombre=usuario["nombre"],
    )


async def _verificar_taller_aprobado(usuario_id, talleres: RepositorioTalleres) -> None:
    taller = await talleres.buscar_por_usuario(usuario_id)
    estado = EstadoSolicitud(taller["estado_solicitud"]) if taller else EstadoSolicitud.PENDIENTE
    if estado is EstadoSolicitud.PENDIENTE:
        raise ErrorLogin(
            "taller_pendiente",
            "Tu solicitud de alta como taller está pendiente de revisión. "
            "Vas a poder iniciar sesión cuando un administrador la apruebe.",
        )
    if estado is EstadoSolicitud.RECHAZADO:
        raise ErrorLogin(
            "taller_rechazado",
            f"Tu solicitud de alta como taller fue rechazada. Motivo: {taller.get('motivo_rechazo')}",
        )


def _mensaje_bloqueo(hasta: datetime, ahora: datetime) -> str:
    minutos = max(1, -(-int((hasta - ahora).total_seconds()) // 60))
    return (
        "Tu cuenta quedó bloqueada por demasiados intentos fallidos. "
        f"Probá de nuevo en {minutos} minuto{'s' if minutos != 1 else ''}."
    )


@lru_cache
def _hash_de_relleno() -> str:
    return hashear_contrasena("relleno-para-igualar-tiempos")
