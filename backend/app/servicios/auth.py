from datetime import UTC, datetime

from app.core.seguridad import hashear_contrasena
from app.esquemas.auth import RegistroEntrada, UsuarioSalida
from app.modelos.usuario import Rol
from app.repositorios.usuarios import RepositorioUsuarios


async def registrar_propietario(datos: RegistroEntrada, repo: RepositorioUsuarios) -> UsuarioSalida:
    """Da de alta un propietario. Lanza CorreoYaRegistrado si el correo ya tiene cuenta."""
    usuario = {
        "nombre": datos.nombre,
        "apellido": datos.apellido,
        "correo": datos.correo,
        "contrasena_hash": hashear_contrasena(datos.contrasena),
        "rol": Rol.PROPIETARIO.value,
        "fecha_alta": datetime.now(UTC),
        "intentos_login_fallidos": 0,
        "bloqueado_hasta": None,
    }
    usuario_id = await repo.insertar(usuario)
    return UsuarioSalida(
        id=usuario_id,
        nombre=datos.nombre,
        apellido=datos.apellido,
        correo=datos.correo,
        rol=Rol.PROPIETARIO,
    )
