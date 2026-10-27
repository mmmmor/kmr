"""Registro de intervenciones. Un registro solo se inserta: nunca se modifica ni se elimina."""

from bson import ObjectId
from bson.errors import InvalidId

from app.core.fechas import ahora_en_milisegundos, inicio_del_dia
from app.core.seguridad import UsuarioSesion
from app.esquemas.intervenciones import (
    AutorizacionEntrada,
    AutorizacionSalida,
    IntervencionEntrada,
    IntervencionSalida,
    IntervencionTallerEntrada,
    ItemSalida,
    ProximaRevisionSalida,
)
from app.esquemas.vehiculos import UltimaLectura
from app.modelos.intervencion import Origen
from app.modelos.usuario import Rol
from app.repositorios.codigos import RepositorioCodigos
from app.repositorios.comprobantes import AlmacenComprobantes
from app.repositorios.intervenciones import CadenaModificada, RepositorioIntervenciones
from app.repositorios.talleres import RepositorioTalleres
from app.repositorios.vehiculos import RepositorioVehiculos
from app.servicios import codigos as servicio_codigos
from app.servicios.codigos import CodigoInvalido
from app.servicios.hash import calcular_hash

# Cuántas veces se recalcula el encadenamiento si otra carga del mismo vehículo se adelantó.
MAX_REINTENTOS_CADENA = 5


class ComprobanteNoDisponible(Exception):
    """La intervención no existe, no tiene comprobante o quien lo pide no puede verlo."""


def nueva(
    datos: IntervencionEntrada,
    vehiculo_id: ObjectId,
    origen: Origen,
    registrado_por: ObjectId,
    taller_id: ObjectId | None = None,
    codigo_id: ObjectId | None = None,
) -> dict:
    """Documento de `intervenciones`. La fecha de registro y los hashes se completan al insertarlo."""
    proxima = datos.proxima_revision
    return {
        "vehiculo_id": vehiculo_id,
        "origen": origen.value,
        "taller_id": taller_id,
        "registrado_por": registrado_por,
        "codigo_id": codigo_id,
        "fecha_intervencion": inicio_del_dia(datos.fecha_intervencion),
        "kilometraje": datos.kilometraje,
        "tipo": datos.tipo,
        "descripcion": datos.descripcion,
        "items": [{"descripcion": item.descripcion, "cantidad": item.cantidad} for item in datos.items],
        "proxima_revision": None if proxima is None else {
            "kilometraje": proxima.kilometraje,
            "fecha": inicio_del_dia(proxima.fecha) if proxima.fecha else None,
            "detalle": proxima.detalle,
        },
        "comprobante_id": None,
        # La validación del kilometraje (HU-009) llega en el Sprint 3.
        "alerta_kilometraje": None,
        "corrige_a": None,
        "motivo_correccion": None,
    }


async def insertar_encadenada(
    intervencion: dict,
    intervenciones: RepositorioIntervenciones,
    en_transaccion,
    antes_de_insertar=None,
) -> dict:
    """Inserta la intervención al final de la cadena de hash de su vehículo, en una transacción.

    `antes_de_insertar(sesion)` corre dentro de la misma transacción (por ejemplo, consumir el
    código del taller): si la inserción falla, también se deshace. Si una carga simultánea del
    mismo vehículo tomó el mismo hash_anterior, se vuelve a leer el último hash y se reintenta.
    """

    async def encadenar(sesion):
        if antes_de_insertar is not None:
            await antes_de_insertar(sesion)
        ultima = await intervenciones.ultima_registrada(intervencion["vehiculo_id"], sesion=sesion)
        documento = {
            **intervencion,
            "fecha_registro": ahora_en_milisegundos(),
            "hash_anterior": ultima["hash"] if ultima else None,
        }
        documento["hash"] = calcular_hash(documento, documento["hash_anterior"])
        documento["_id"] = await intervenciones.insertar(documento, sesion=sesion)
        return documento

    for _ in range(MAX_REINTENTOS_CADENA - 1):
        try:
            return await en_transaccion(encadenar)
        except CadenaModificada:
            continue
    return await en_transaccion(encadenar)


async def registrar_con_comprobante(
    intervencion: dict,
    comprobante: tuple[bytes, str, str] | None,
    intervenciones: RepositorioIntervenciones,
    comprobantes: AlmacenComprobantes,
    en_transaccion,
    antes_de_insertar=None,
) -> dict:
    """Guarda el comprobante (si hay) y registra la intervención. Si el registro falla, borra el comprobante."""
    if comprobante is not None:
        contenido, tipo, nombre = comprobante
        intervencion["comprobante_id"] = await comprobantes.guardar(nombre, contenido, tipo)
    try:
        return await insertar_encadenada(intervencion, intervenciones, en_transaccion, antes_de_insertar)
    except Exception:
        if intervencion["comprobante_id"] is not None:
            await comprobantes.eliminar(intervencion["comprobante_id"])
        raise


# --- Propietario (HU-008) ---


async def registrar_por_propietario(
    datos: IntervencionEntrada,
    vehiculo: dict,
    propietario_id: str,
    comprobante: tuple[bytes, str, str] | None,
    intervenciones: RepositorioIntervenciones,
    comprobantes: AlmacenComprobantes,
    en_transaccion,
) -> IntervencionSalida:
    """Intervención autorreportada: sin taller ni código, se muestra como "Autorreportado por el propietario"."""
    intervencion = nueva(datos, vehiculo["_id"], Origen.PROPIETARIO, ObjectId(propietario_id))
    documento = await registrar_con_comprobante(intervencion, comprobante, intervenciones, comprobantes, en_transaccion)
    return a_salida(documento, vehiculo["dominio"])


# --- Taller (HU-007) ---


async def autorizar_taller(
    datos: AutorizacionEntrada, vehiculos: RepositorioVehiculos, codigos: RepositorioCodigos
) -> tuple[dict, dict]:
    """Vehículo y código si el dominio está vinculado y el código sirve. Si no, lanza CodigoInvalido.

    Un dominio sin vincular da el mismo error que un código incorrecto: no se revela qué vehículos
    tienen cuenta.
    """
    vehiculo = await vehiculos.buscar_por_dominio(datos.dominio)
    if vehiculo is None:
        raise CodigoInvalido
    return vehiculo, await servicio_codigos.validar(vehiculo["_id"], datos.codigo, codigos)


async def resumen_autorizado(vehiculo: dict, intervenciones: RepositorioIntervenciones) -> AutorizacionSalida:
    ultima = await intervenciones.ultima_lectura(vehiculo["_id"])
    return AutorizacionSalida(
        dominio=vehiculo["dominio"],
        marca=vehiculo["marca"],
        modelo=vehiculo["modelo"],
        anio=vehiculo["anio"],
        ultima_lectura=None if ultima is None else UltimaLectura(
            kilometraje=ultima["kilometraje"], fecha=ultima["fecha_intervencion"]
        ),
    )


async def registrar_por_taller(
    datos: IntervencionTallerEntrada,
    taller: dict,
    usuario_id: str,
    comprobante: tuple[bytes, str, str] | None,
    vehiculos: RepositorioVehiculos,
    codigos: RepositorioCodigos,
    intervenciones: RepositorioIntervenciones,
    comprobantes: AlmacenComprobantes,
    en_transaccion,
) -> IntervencionSalida:
    """Registra la intervención con la identificación del taller y consume el código (HU-007)."""
    vehiculo, codigo = await autorizar_taller(datos, vehiculos, codigos)
    intervencion = nueva(
        datos, vehiculo["_id"], Origen.TALLER, ObjectId(usuario_id), taller_id=taller["_id"], codigo_id=codigo["_id"]
    )

    async def consumir_codigo(sesion):
        await servicio_codigos.consumir(codigo, taller["_id"], codigos, sesion=sesion)

    documento = await registrar_con_comprobante(
        intervencion, comprobante, intervenciones, comprobantes, en_transaccion, consumir_codigo
    )
    return a_salida(documento, vehiculo["dominio"])


async def listar_del_taller(taller: dict, intervenciones: RepositorioIntervenciones) -> list[IntervencionSalida]:
    return [a_salida(i, i["dominio"]) for i in await intervenciones.listar_por_taller(taller["_id"])]


# --- Comprobantes ---


async def leer_comprobante(
    intervencion_id: str,
    usuario: UsuarioSesion,
    intervenciones: RepositorioIntervenciones,
    vehiculos: RepositorioVehiculos,
    talleres: RepositorioTalleres,
    comprobantes: AlmacenComprobantes,
) -> tuple[bytes, str, str]:
    """El comprobante puede tener datos personales: solo lo ven el propietario del vehículo y el taller que lo cargó."""
    try:
        intervencion = await intervenciones.buscar(ObjectId(intervencion_id))
    except (InvalidId, TypeError):
        raise ComprobanteNoDisponible
    if intervencion is None or intervencion.get("comprobante_id") is None:
        raise ComprobanteNoDisponible

    if usuario.rol is Rol.PROPIETARIO:
        vehiculo = await vehiculos.buscar(intervencion["vehiculo_id"])
        permitido = vehiculo is not None and vehiculo["propietario_id"] == ObjectId(usuario.id)
    else:
        taller = await talleres.buscar_por_usuario(ObjectId(usuario.id))
        permitido = taller is not None and intervencion["taller_id"] == taller["_id"]
    if not permitido:
        raise ComprobanteNoDisponible
    return await comprobantes.leer(intervencion["comprobante_id"])


def a_salida(intervencion: dict, dominio: str) -> IntervencionSalida:
    proxima = intervencion.get("proxima_revision")
    return IntervencionSalida(
        id=str(intervencion["_id"]),
        dominio=dominio,
        origen=intervencion["origen"],
        fecha_intervencion=intervencion["fecha_intervencion"],
        kilometraje=intervencion["kilometraje"],
        tipo=intervencion["tipo"],
        descripcion=intervencion.get("descripcion"),
        items=[ItemSalida(**item) for item in intervencion["items"]],
        proxima_revision=ProximaRevisionSalida(**proxima) if proxima else None,
        tiene_comprobante=intervencion.get("comprobante_id") is not None,
        alerta_kilometraje=intervencion.get("alerta_kilometraje"),
        fecha_registro=intervencion["fecha_registro"],
    )
