from datetime import UTC, datetime

from app.esquemas.talleres import SolicitudTallerEntrada, SolicitudTallerSalida
from app.modelos.taller import EstadoSolicitud
from app.modelos.usuario import Rol
from app.repositorios.talleres import RepositorioTalleres
from app.repositorios.usuarios import RepositorioUsuarios
from app.servicios.auth import nuevo_usuario


async def solicitar_alta(
    datos: SolicitudTallerEntrada,
    usuarios: RepositorioUsuarios,
    talleres: RepositorioTalleres,
    en_transaccion,
) -> SolicitudTallerSalida:
    """Crea el usuario taller y su solicitud pendiente en una sola transacción (HU-003).

    Lanza CorreoYaRegistrado o CuitYaRegistrado; en ese caso no queda nada guardado.
    """
    usuario = nuevo_usuario(datos, Rol.TALLER)

    async def crear(sesion):
        usuario_id = await usuarios.insertar(dict(usuario), sesion=sesion)
        return await talleres.insertar(
            {
                "usuario_id": usuario_id,
                "razon_social": datos.razon_social,
                "cuit": datos.cuit,
                "domicilio": datos.domicilio,
                "telefono": datos.telefono,
                "estado_solicitud": EstadoSolicitud.PENDIENTE.value,
                "motivo_rechazo": None,
                "fecha_solicitud": datetime.now(UTC),
                "aprobado_por": None,
                "fecha_resolucion": None,
            },
            sesion=sesion,
        )

    taller_id = await en_transaccion(crear)
    return SolicitudTallerSalida(
        id=str(taller_id),
        razon_social=datos.razon_social,
        cuit=datos.cuit,
        estado_solicitud=EstadoSolicitud.PENDIENTE,
    )
