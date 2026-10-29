"""Correcciones (HU-011). Un registro nunca se modifica: la corrección es un registro nuevo vinculado.

La corrección conserva el origen y el taller del original, la registra quien corrige y no necesita
código. Su kilometraje se valida (HU-009) contra lo que había antes del registro que corrige.
"""

from bson import ObjectId
from bson.errors import InvalidId

from app.core.seguridad import UsuarioSesion
from app.esquemas.intervenciones import CorreccionEntrada, IntervencionSalida
from app.modelos.intervencion import Origen
from app.modelos.taller import EstadoSolicitud
from app.modelos.usuario import Rol
from app.repositorios.intervenciones import RepositorioIntervenciones
from app.repositorios.talleres import RepositorioTalleres
from app.repositorios.vehiculos import RepositorioVehiculos
from app.servicios import intervenciones as servicio_intervenciones
from app.servicios.historial import campos_corregidos


class RegistroNoEncontrado(Exception):
    """No existe, o es de un vehículo ajeno (no se revela cuál de las dos)."""


class CorreccionNoPermitida(Exception):
    def __init__(self, mensaje: str):
        super().__init__(mensaje)
        self.mensaje = mensaje


class RegistroYaCorregido(Exception):
    """Ya tiene una corrección: si hay otro error, se corrige la corrección (la versión vigente)."""


class SinCambios(Exception):
    pass


async def corregir(
    intervencion_id: str,
    datos: CorreccionEntrada,
    usuario: UsuarioSesion,
    intervenciones: RepositorioIntervenciones,
    vehiculos: RepositorioVehiculos,
    talleres: RepositorioTalleres,
    en_transaccion,
) -> IntervencionSalida:
    try:
        original = await intervenciones.buscar(ObjectId(intervencion_id))
    except (InvalidId, TypeError):
        raise RegistroNoEncontrado
    if original is None:
        raise RegistroNoEncontrado
    vehiculo = await vehiculos.buscar(original["vehiculo_id"])

    if usuario.rol is Rol.TALLER:
        taller = await talleres.buscar_por_usuario(ObjectId(usuario.id))
        if taller is None or taller["estado_solicitud"] != EstadoSolicitud.APROBADO:
            raise CorreccionNoPermitida("Tu taller no está habilitado para registrar intervenciones.")
        if original.get("taller_id") != taller["_id"]:
            raise CorreccionNoPermitida("Solo podés corregir los registros que cargó tu taller.")
    else:
        if vehiculo is None or vehiculo["propietario_id"] != ObjectId(usuario.id):
            raise RegistroNoEncontrado
        if original["origen"] != Origen.PROPIETARIO:
            raise CorreccionNoPermitida(
                "Solo podés corregir tus intervenciones autorreportadas. "
                "Un registro de un taller lo corrige ese taller."
            )

    correccion = servicio_intervenciones.nueva(
        datos, original["vehiculo_id"], Origen(original["origen"]), ObjectId(usuario.id),
        taller_id=original.get("taller_id"),
    )
    correccion.update(corrige_a=original["_id"], motivo_correccion=datos.motivo)
    if not campos_corregidos(correccion, original):
        raise SinCambios

    async def sin_correccion_previa(sesion):
        # Dentro de la transacción: dos correcciones simultáneas del mismo registro chocan en la
        # cadena de hash, y al reintentar esta ya ve la otra.
        if await intervenciones.buscar_correccion(original["_id"], sesion=sesion) is not None:
            raise RegistroYaCorregido

    documento = await servicio_intervenciones.insertar_encadenada(
        correccion, intervenciones, en_transaccion, sin_correccion_previa
    )
    return await servicio_intervenciones.salida_registrada(documento, vehiculo["dominio"], intervenciones)
